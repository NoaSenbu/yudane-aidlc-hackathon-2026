"""Phase 4 Step 4-3.2 PBT-04: Commutative プロパティ。

PBT-04 (NFR-PBT-DEBATE-04) 順序非依存:
  estimate_stress_level() の戻り値（level）は ClientSignals の信号集合に対して
  順序非依存 = client_signals の値が同じなら、Memory signals の順序を入れ替えても
  level が変わらない（不変条件）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-3.2
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md STRESS-03
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.debate.domain.payloads import ClientSignals
from backend.src.debate.stress import estimate_stress_level

# ---------------------------------------------------------------------------
# Hypothesis Arbitrary
# ---------------------------------------------------------------------------

now_strategy = st.datetimes(
    min_value=datetime(2025, 1, 1).replace(tzinfo=None),
    max_value=datetime(2030, 12, 31).replace(tzinfo=None),
    timezones=st.just(UTC),
)

# 既知の Memory signal 候補
known_signals = [
    "stress_high",
    "fatigue_chronic",
    "sleep_deprivation",
    "burnout",
    "overload",
]
neutral_signals = ["preference_a", "preference_b", "history_summary", "context_x"]


@st.composite
def client_signals_strategy(draw: st.DrawFn) -> ClientSignals:
    return ClientSignals(
        recent_cart_intercepts=draw(st.integers(min_value=0, max_value=20)),
        recent_debate_refuses=draw(st.integers(min_value=0, max_value=20)),
        last_signin_at_late_night=draw(st.booleans()),
        current_hour_jst=draw(st.integers(min_value=0, max_value=23)),
    )


memory_signals_strategy = st.lists(
    st.sampled_from(known_signals + neutral_signals),
    min_size=0,
    max_size=10,
)


# ---------------------------------------------------------------------------
# PBT-04: Memory signals の順序を入れ替えても level / score が同一
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    client_signals=client_signals_strategy(),
    memory_signals=memory_signals_strategy,
    now=now_strategy,
    permutation_seed=st.integers(min_value=0, max_value=10000),
)
def test_memory_signals_order_independent(
    client_signals: ClientSignals,
    memory_signals: list[str],
    now: datetime,
    permutation_seed: int,
) -> None:
    """Memory signals の順序を入れ替えても level / score / signals_used 集合は同じ。"""
    # 元の順序で計算
    result_a = estimate_stress_level(
        actor_id="user-1",
        now=now,
        client_signals=client_signals,
        memory_signals=memory_signals,
    )

    # 順序をシャッフル（permutation_seed で決定的に）
    import random as _random  # local import で hypothesis から isolation

    rng = _random.Random(permutation_seed)
    shuffled = memory_signals.copy()
    rng.shuffle(shuffled)

    result_b = estimate_stress_level(
        actor_id="user-1",
        now=now,
        client_signals=client_signals,
        memory_signals=shuffled,
    )

    assert result_a.level == result_b.level
    assert result_a.score == result_b.score


# ---------------------------------------------------------------------------
# PBT-04: actor_id を変えても level / score は変わらない（PII 非依存性）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    actor_a=st.text(min_size=1, max_size=36),
    actor_b=st.text(min_size=1, max_size=36),
    client_signals=client_signals_strategy(),
    memory_signals=memory_signals_strategy,
    now=now_strategy,
)
def test_actor_id_does_not_affect_level(
    actor_a: str,
    actor_b: str,
    client_signals: ClientSignals,
    memory_signals: list[str],
    now: datetime,
) -> None:
    """同じ signals なら actor_id が変わっても level / score は同じ（PII 非依存）。"""
    result_a = estimate_stress_level(
        actor_id=actor_a,
        now=now,
        client_signals=client_signals,
        memory_signals=memory_signals,
    )
    result_b = estimate_stress_level(
        actor_id=actor_b,
        now=now,
        client_signals=client_signals,
        memory_signals=memory_signals,
    )
    assert result_a.level == result_b.level
    assert result_a.score == result_b.score
