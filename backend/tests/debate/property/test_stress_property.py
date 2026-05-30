"""Stress Estimator の PBT-07 集合性プロパティ（Phase 2 Step 1.4 PBT 補強）。

PBT-07: 任意の入力で必ず 'low' | 'mid' | 'high' のいずれかを返す（business-rules STRESS-01）。
PBT-07': score >= 0 を保証。

参照: aidlc-docs/construction/unit-3-debate/nfr-requirements/nfr-requirements.md NFR-PBT-DEBATE-07
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §4 STRESS
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from backend.src.debate.domain.payloads import ClientSignals
from backend.src.debate.stress import estimate_stress_level

_VALID_LEVELS = frozenset({"low", "mid", "high"})

# 業務帯域に絞った datetime（2025-2030 UTC）
datetime_strategy = st.datetimes(
    min_value=datetime(2025, 1, 1).replace(tzinfo=None),
    max_value=datetime(2030, 12, 31).replace(tzinfo=None),
    timezones=st.just(UTC),
)


@st.composite
def client_signals_strategy(draw: st.DrawFn) -> ClientSignals:
    """有効な ClientSignals を生成する Arbitrary。"""
    return ClientSignals(
        recent_cart_intercepts=draw(st.integers(min_value=0, max_value=100)),
        recent_debate_refuses=draw(st.integers(min_value=0, max_value=100)),
        last_signin_at_late_night=draw(st.booleans()),
        current_hour_jst=draw(st.integers(min_value=0, max_value=23)),
    )


memory_signals_strategy = st.one_of(
    st.none(),
    st.lists(
        st.text(min_size=0, max_size=30).filter(lambda s: not s.startswith("__")),
        min_size=0,
        max_size=10,
    ),
)


@given(
    actor_id=st.text(min_size=1, max_size=30),
    now=datetime_strategy,
    signals=client_signals_strategy(),
    memory_signals=memory_signals_strategy,
)
def test_stress_level_always_in_three_set(
    actor_id: str,
    now: datetime,
    signals: ClientSignals,
    memory_signals: list[str] | None,
) -> None:
    """PBT-07: 任意の入力で result.level が 'low' / 'mid' / 'high' のいずれか。"""
    result = estimate_stress_level(
        actor_id=actor_id,
        now=now,
        client_signals=signals,
        memory_signals=memory_signals,
    )
    assert result.level in _VALID_LEVELS, (
        f"Invalid level '{result.level}' for input "
        f"actor_id={actor_id}, hour={signals.current_hour_jst}, "
        f"score={result.score}"
    )


@given(
    actor_id=st.text(min_size=1, max_size=30),
    now=datetime_strategy,
    signals=client_signals_strategy(),
    memory_signals=memory_signals_strategy,
)
def test_stress_score_always_non_negative(
    actor_id: str,
    now: datetime,
    signals: ClientSignals,
    memory_signals: list[str] | None,
) -> None:
    """PBT-07': score は常に 0 以上。"""
    result = estimate_stress_level(
        actor_id=actor_id,
        now=now,
        client_signals=signals,
        memory_signals=memory_signals,
    )
    assert result.score >= 0


@given(
    actor_id=st.text(min_size=1, max_size=30),
    signals=client_signals_strategy(),
)
def test_signals_used_contains_no_actor_id(
    actor_id: str,
    signals: ClientSignals,
) -> None:
    """signals_used フィールドに actor_id は含まれない（NFR-SEC-DEBATE-04 整合）。"""
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    result = estimate_stress_level(
        actor_id=actor_id,
        now=now,
        client_signals=signals,
    )
    for sig in result.signals_used:
        # actor_id の文字列は signals_used に登場しない
        # ただし actor_id が偶然 'late_night' 等の英単語と一致するケースを除外
        if actor_id and len(actor_id) >= 8:
            assert (
                actor_id not in sig
            ), f"actor_id leaked: '{actor_id}' found in signal '{sig}'"


@given(
    actor_id=st.text(min_size=1, max_size=30),
    signals=client_signals_strategy(),
)
def test_high_threshold_score_returns_high(
    actor_id: str,
    signals: ClientSignals,
) -> None:
    """PBT-07: score >= 4 のとき必ず 'high'（STRESS-05 不変条件）。"""
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    result = estimate_stress_level(
        actor_id=actor_id,
        now=now,
        client_signals=signals,
        memory_signals=None,
    )
    if result.score >= 4:
        assert result.level == "high"
    elif result.score >= 2:
        assert result.level == "mid"
    else:
        assert result.level == "low"
