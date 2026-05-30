"""evaluate_notification の単体 + PBT テスト（Unit-5 owner）。

Property 5（Safeguard 連携での通知抑制）を担保。TypeScript 実装と
同一入力に対し同一出力を返す（SG-10 クロス言語一致）。
Validates: NFR-PBT-02 / functional-design.md Property 5。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from safeguard_policy import evaluate_notification


def _ctx(
    *,
    monthly_limit_yen: int = 70_000,
    current_budget_used_yen: int = 0,
    cooldown_on: bool = False,
    quiet_week: bool = False,
    has_debt: bool = False,
    cooldown_until: Optional[str] = None,
    user_id: str = "user-123",
) -> dict:
    return {
        "user_id": user_id,
        "monthly_limit_yen": monthly_limit_yen,
        "current_budget_used_yen": current_budget_used_yen,
        "cooldown_on": cooldown_on,
        "quiet_week": quiet_week,
        "has_debt": has_debt,
        "cooldown_until": cooldown_until,
    }


class TestCooldownUntil:
    """cooldown_until 自動冷却の境界テスト。"""

    def test_future_cooldown_blocks(self) -> None:
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        future = (now + timedelta(hours=3)).isoformat()
        result = evaluate_notification(**_ctx(cooldown_until=future), now=now)
        assert result.decision == "block"
        assert result.reason_code == "safeguard.cooldown"

    def test_past_cooldown_proceeds_to_normal_eval(self) -> None:
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        past = (now - timedelta(hours=1)).isoformat()
        result = evaluate_notification(**_ctx(cooldown_until=past), now=now)
        assert result.decision == "allow"

    def test_no_cooldown_proceeds_to_normal_eval(self) -> None:
        result = evaluate_notification(**_ctx())
        assert result.decision == "allow"


class TestSG01EvaluationOrder:
    """SG-01 評価順 + warn → block 格上げ。"""

    def test_cooldown_on_blocks(self) -> None:
        result = evaluate_notification(**_ctx(cooldown_on=True))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.cooldown"

    def test_quiet_week_blocks(self) -> None:
        result = evaluate_notification(**_ctx(quiet_week=True))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.quiet-week"

    def test_monthly_limit_exceeded_blocks(self) -> None:
        result = evaluate_notification(**_ctx(current_budget_used_yen=75_000))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.monthly-limit-exceeded"

    def test_near_limit_warn_promoted_to_block_for_notification(self) -> None:
        # 70_000 * 0.8 = 56_000、warn 閾値到達
        result = evaluate_notification(**_ctx(current_budget_used_yen=60_000))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.near-limit"

    def test_below_warn_threshold_allows(self) -> None:
        result = evaluate_notification(**_ctx(current_budget_used_yen=30_000))
        assert result.decision == "allow"


class TestHasDebt:
    def test_debt_restricts_effective_limit(self) -> None:
        # 70_000 × 35/70 = 35_000
        result = evaluate_notification(**_ctx(has_debt=True, current_budget_used_yen=36_000))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.debt-restricted"


class TestPropertyBased:
    """PBT: warn が必ず block にマッピングされる不変条件。"""

    @given(used=st.integers(min_value=56_000, max_value=69_999))
    @settings(max_examples=50)
    def test_warn_always_block_for_notification(self, used: int) -> None:
        result = evaluate_notification(**_ctx(current_budget_used_yen=used))
        assert result.decision == "block"
        assert result.reason_code == "safeguard.near-limit"

    @given(offset_sec=st.integers(min_value=1, max_value=86_400 * 30))
    @settings(max_examples=50)
    def test_future_cooldown_always_blocks(self, offset_sec: int) -> None:
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        future = (now + timedelta(seconds=offset_sec)).isoformat()
        result = evaluate_notification(**_ctx(cooldown_until=future), now=now)
        assert result.decision == "block"
