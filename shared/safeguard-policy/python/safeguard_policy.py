"""S-03 SafeguardPolicy（Python 実装）。

月間上限 / 冷却 / 負債の判定（純関数）。TypeScript 実装（decide-allow.ts）と
同一入力に対し同一出力を返す（SG-10、クロス言語一致）。
設計: business-logic-model.md ALG-SG / business-rules.md SG-01〜10。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# 定数（business-rules.md §2.1）
DEFAULT_MONTHLY_LIMIT_RATIO = 0.7
DEBT_MONTHLY_LIMIT_RATIO = 0.35
DEBATE_COOLDOWN_SECONDS = 86_400
CART_ATTACK_STEPS_SECONDS: tuple[int, ...] = (1_800, 21_600, 86_400)
WARN_THRESHOLD_RATIO = 0.8

Decision = Literal["allow", "block", "warn"]
ReasonCode = Literal[
    "safeguard.cooldown",
    "safeguard.quiet-week",
    "safeguard.monthly-limit-exceeded",
    "safeguard.debt-restricted",
    "safeguard.near-limit",
    "allowed",
]


@dataclass(frozen=True)
class SafeguardFlags:
    """セーフガードのフラグ群。"""

    cooldown_on: bool
    quiet_week: bool
    has_debt: bool


@dataclass(frozen=True)
class SafeguardInput:
    """判定への入力。"""

    transition_count_month: int
    monthly_limit_yen: int
    current_budget_used_yen: int
    flags: SafeguardFlags


@dataclass(frozen=True)
class SafeguardDecision:
    """判定結果。"""

    decision: Decision
    reason_code: ReasonCode
    effective_limit_yen: int
    remaining_yen: int


def decide_allow(data: SafeguardInput) -> SafeguardDecision:
    """Amazon 遷移 / 論破開始の可否を段階評価で判定する。

    評価順（SG-01）: cooldown → quiet_week → 実効上限決定（debt 切替）→ 上限超過 block →
    80% 超 warn → allow。warn は遷移を止めず通知のみ（SG-07、NG-6 回避）。

    Args:
        data: 判定入力。

    Returns:
        判定結果（decision / reason_code / 実効上限 / 残額）。
    """
    flags = data.flags

    # 実効上限（debt で再スケール、SG-04）
    if flags.has_debt:
        effective_limit_yen = round(
            data.monthly_limit_yen * (DEBT_MONTHLY_LIMIT_RATIO / DEFAULT_MONTHLY_LIMIT_RATIO)
        )
    else:
        effective_limit_yen = data.monthly_limit_yen
    remaining_yen = max(0, effective_limit_yen - data.current_budget_used_yen)

    def _decision(decision: Decision, reason: ReasonCode) -> SafeguardDecision:
        return SafeguardDecision(
            decision=decision,
            reason_code=reason,
            effective_limit_yen=effective_limit_yen,
            remaining_yen=remaining_yen,
        )

    # ステップ1: フラグ系の即時 block（最優先、SG-02/03）
    if flags.cooldown_on:
        return _decision("block", "safeguard.cooldown")
    if flags.quiet_week:
        return _decision("block", "safeguard.quiet-week")

    # ステップ3: 上限超過の block（SG-05）
    if data.current_budget_used_yen >= effective_limit_yen:
        reason: ReasonCode = (
            "safeguard.debt-restricted" if flags.has_debt else "safeguard.monthly-limit-exceeded"
        )
        return _decision("block", reason)

    # ステップ4: 80% 超で warn（SG-06、遷移は止めない）
    if data.current_budget_used_yen >= effective_limit_yen * WARN_THRESHOLD_RATIO:
        return _decision("warn", "safeguard.near-limit")

    # ステップ5: 許可
    return _decision("allow", "allowed")
