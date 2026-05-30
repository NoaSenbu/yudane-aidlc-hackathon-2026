"""Unit-3 Debate Stress Estimator のテスト（Phase 2 Step 1.1 Red）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §4 STRESS-01〜06
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-logic-model.md ALG-STRESS
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.src.debate.domain.payloads import ClientSignals
from backend.src.debate.stress import estimate_stress_level


def _make_signals(
    *,
    cart_intercepts: int = 0,
    debate_refuses: int = 0,
    late_night: bool = False,
    hour_jst: int = 12,
) -> ClientSignals:
    """テスト用の ClientSignals を構築する。"""
    return ClientSignals(
        recent_cart_intercepts=cart_intercepts,
        recent_debate_refuses=debate_refuses,
        last_signin_at_late_night=late_night,
        current_hour_jst=hour_jst,
    )


@pytest.fixture
def now_jst_noon() -> datetime:
    """JST 正午（UTC 03:00、stress スコアに加算なし）。"""
    return datetime(2026, 6, 1, 3, 0, 0, tzinfo=UTC)


@pytest.fixture
def now_jst_late_night() -> datetime:
    """JST 23 時（UTC 14:00、深夜帯 +2）。"""
    return datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)


@pytest.fixture
def now_jst_overtime() -> datetime:
    """JST 20 時（UTC 11:00、残業帯 +1）。"""
    return datetime(2026, 6, 1, 11, 0, 0, tzinfo=UTC)


class TestEstimateStressLevel:
    """`estimate_stress_level` の挙動を検証する（business-rules STRESS-01〜06）。"""

    def test_empty_signals_returns_low(self, now_jst_noon: datetime) -> None:
        """client_signals=空 + memory=空 → low（STRESS-04 の fail-safe 含む）。"""
        signals = _make_signals(hour_jst=12)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
            memory_signals=None,
        )
        assert result.level == "low"
        assert result.score == 0

    def test_late_night_adds_2_to_score(self, now_jst_late_night: datetime) -> None:
        """current_hour_jst=23（深夜帯）→ +2 加算 → mid（score=2）。"""
        signals = _make_signals(hour_jst=23)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_late_night,
            client_signals=signals,
        )
        assert result.score == 2
        assert result.level == "mid"

    def test_overtime_adds_1_to_score(self, now_jst_overtime: datetime) -> None:
        """current_hour_jst=20（残業帯）→ +1 加算 → low（score=1）。"""
        signals = _make_signals(hour_jst=20)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_overtime,
            client_signals=signals,
        )
        assert result.score == 1
        assert result.level == "low"

    def test_high_with_late_night_and_signals(
        self, now_jst_late_night: datetime
    ) -> None:
        """深夜帯 + late_night_signin=True + cart_intercepts=3 + debate_refuses=1 → score=5 → high。

        スコア配点: 深夜帯(+2) + cart>=3(+1) + refuses>=1(+1) + late_night_signin(+1) = 5
        """
        signals = _make_signals(
            hour_jst=23,
            cart_intercepts=3,
            debate_refuses=1,
            late_night=True,
        )
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_late_night,
            client_signals=signals,
        )
        assert result.score == 5
        assert result.level == "high"

    def test_memory_high_signal_adds_to_score(self, now_jst_noon: datetime) -> None:
        """Memory に 'stress_high' signal を含む → +1 加算（STRESS-03）。"""
        signals = _make_signals(hour_jst=12)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
            memory_signals=["stress_high"],
        )
        assert result.score == 1
        assert result.level == "low"

    def test_memory_two_high_signals_adds_2(self, now_jst_noon: datetime) -> None:
        """Memory に 'stress_high' + 'fatigue_chronic' → +2 加算（最大 +2、STRESS-03）。"""
        signals = _make_signals(hour_jst=12)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
            memory_signals=["stress_high", "fatigue_chronic"],
        )
        assert result.score == 2
        assert result.level == "mid"

    def test_memory_signals_none_does_not_raise(self, now_jst_noon: datetime) -> None:
        """memory_signals=None でも例外を上げず動作する（STRESS-04 fail-safe）。"""
        signals = _make_signals(hour_jst=12)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
            memory_signals=None,
        )
        assert result.level == "low"

    def test_memory_signals_empty_list_does_not_raise(
        self, now_jst_noon: datetime
    ) -> None:
        """memory_signals=[] でも例外を上げず動作する。"""
        signals = _make_signals(hour_jst=12)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
            memory_signals=[],
        )
        assert result.level == "low"

    def test_signals_used_does_not_contain_pii(
        self, now_jst_late_night: datetime
    ) -> None:
        """signals_used フィールドに PII を含まない（NFR-SEC-DEBATE-04 整合）。"""
        signals = _make_signals(hour_jst=23, cart_intercepts=3, late_night=True)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_late_night,
            client_signals=signals,
        )
        # actor_id 等の PII が signals_used に混入しない
        for sig in result.signals_used:
            assert "user-1" not in sig
            assert isinstance(sig, str)

    def test_score_boundary_exactly_2_returns_mid(self, now_jst_noon: datetime) -> None:
        """score == 2（境界）→ mid（STRESS-05: score >= 2 → mid）。"""
        signals = _make_signals(hour_jst=12, cart_intercepts=3, debate_refuses=1)
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_noon,
            client_signals=signals,
        )
        assert result.score == 2
        assert result.level == "mid"

    def test_score_boundary_exactly_4_returns_high(
        self, now_jst_late_night: datetime
    ) -> None:
        """score == 4（境界）→ high（STRESS-05: score >= 4 → high）。"""
        signals = _make_signals(
            hour_jst=23,
            cart_intercepts=3,
            debate_refuses=1,
        )
        result = estimate_stress_level(
            actor_id="user-1",
            now=now_jst_late_night,
            client_signals=signals,
        )
        assert result.score == 4
        assert result.level == "high"
