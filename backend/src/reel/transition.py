"""ALG-TRANSITION: Amazon 遷移記録 + EXP + Safeguard ゲート（B-13、Q6=A）。

先行 Safeguard ゲート（S-03 正本 decide_allow、fail-closed）→ 冪等な原子書き込み
（遷移記録 + 月間カウント）→ EXP +1 同期付与。永続層は TransitionRepository で抽象化
（テストはフェイク、DynamoDB は repository 実装で結線）。
設計: business-logic ALG-TRANSITION / business-rules REEL-TR-01〜08 / R-PAT-TXN-01/SAFE-01。
"""

from __future__ import annotations

from typing import Protocol

from backend.src.common.exceptions import DomainError, ErrorCategory
from backend.src.reel.models import AmazonTransitionRequest, ExpAward

# S-03 正本（shared/safeguard-policy/python）。クロス言語一致の判定（SG-10）。
from safeguard_policy import SafeguardDecision


class SafeguardGate(Protocol):
    """遷移前ゲート。S-03 decide_allow をラップし入力を組み立てて判定する。"""

    def evaluate(self, user_id: str) -> SafeguardDecision:
        """ユーザーの現在状態から遷移可否を判定する。取得失敗時は例外（fail-closed）。"""
        ...


class TransitionRepository(Protocol):
    """遷移記録・月間カウント・EXP の永続層（DynamoDB を抽象化）。"""

    def record_if_absent(self, req: AmazonTransitionRequest, month_bucket: str) -> bool:
        """冪等記録: clientTransitionId 未登録なら記録+月間カウント+1 して True。

        既登録なら False（二重計上しない、REEL-TR-01）。
        遷移記録と月間カウント更新は原子的に行う（TransactWriteItems）。
        """
        ...

    def increment_exp(self, user_id: str, amount: int) -> int:
        """EXP を加算し累計を返す（Achievements、Unit-2 スキーマ、REEL-TR-07）。"""
        ...

    def current_exp(self, user_id: str) -> int:
        """現在の累計 EXP を返す（重複時の応答用）。"""
        ...


def record_transition(
    req: AmazonTransitionRequest,
    *,
    gate: SafeguardGate,
    repo: TransitionRepository,
    month_bucket: str,
) -> ExpAward:
    """Amazon 遷移を冪等に記録し EXP +1 を同期付与する（ALG-TRANSITION）。

    Args:
        req: 遷移リクエスト（冪等キー client_transition_id を含む）。
        gate: 先行 Safeguard ゲート。
        repo: 永続層。
        month_bucket: 集計用の月バケット（"YYYY-MM"）。

    Returns:
        ExpAward（初回は awarded=1、冪等重複は awarded=0/duplicate=true）。

    Raises:
        DomainError: Safeguard block（409）/ ゲート取得失敗（fail-closed, 409）。
    """
    # 1. 先行 Safeguard ゲート（fail-closed、REEL-TR-03 / R-PAT-SAFE-01）
    try:
        decision = gate.evaluate(req.user_id)
    except Exception as exc:  # noqa: BLE001 - 取得失敗は安全側で遷移ブロック
        raise DomainError(
            ErrorCategory.SAFEGUARD,
            "safeguard.unavailable",
            f"Safeguard 状態の取得に失敗（fail-closed）: {exc}",
            user_message="いまは安全のため遷移できません",
            status=409,
        ) from exc

    if decision.decision == "block":
        raise DomainError(
            ErrorCategory.SAFEGUARD,
            decision.reason_code,
            f"Safeguard block: {decision.reason_code}",
            user_message="今月の上限などにより遷移できません",
            status=409,
        )
    # warn は遷移を止めない（REEL-TR-04）

    # 2. 冪等な原子記録（遷移 + 月間カウント、REEL-TR-01/05）
    recorded = repo.record_if_absent(req, month_bucket)
    if not recorded:
        return ExpAward(awarded=0, total_exp=repo.current_exp(req.user_id), duplicate=True)

    # 3. EXP +1 同期付与（REEL-TR-02/07）
    total = repo.increment_exp(req.user_id, 1)
    return ExpAward(awarded=1, total_exp=total, duplicate=False)
