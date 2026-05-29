"""負債セーフガード調整ロジック（ALG-DEBT / PAT2-DEBT-01、US-AUTH-03）。

判定本体は Unit-1 SafeguardPolicy（shared/safeguard-policy）を再利用し、Unit-2 は
has_debt 状態管理と 72h クーリングオフの遅延評価のみを担う（NG-4 倫理配慮）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.src.auth.models import SafeguardStateEntity

# 負債解除のクーリングオフ期間（DEBT-05）
DEBT_RELEASE_COOLDOWN_HOURS = 72


def declare_debt(state: SafeguardStateEntity) -> SafeguardStateEntity:
    """負債ありを申告し、初回から冷却 ON にする（DEBT-01、US-AUTH-03 AC-1）。

    上限の半減は Unit-1 SafeguardPolicy.decideAllow が has_debt=true で自動適用するため、
    ここではフラグ設定のみ（再実装しない）。

    Args:
        state: 現在の SafeguardState。

    Returns:
        負債フラグ・冷却を ON にした SafeguardState。
    """
    updated = state.model_copy(deep=True)
    updated.flags.has_debt = True
    updated.flags.cooldown_on = True
    return updated


def request_debt_release(
    state: SafeguardStateEntity,
    now: datetime,
) -> SafeguardStateEntity:
    """負債解除をリクエストする（時刻を記録、DEBT-04）。

    実際の解除は 72h クーリングオフ後に evaluate_debt_release で行う。

    Args:
        state: 現在の SafeguardState。
        now: 現在時刻。

    Returns:
        debt_release_requested_at を設定した SafeguardState。
    """
    updated = state.model_copy(deep=True)
    updated.debt_release_requested_at = now.isoformat()
    return updated


def evaluate_debt_release(
    state: SafeguardStateEntity,
    now: datetime,
) -> SafeguardStateEntity:
    """72h クーリングオフ経過を評価し、満了していれば負債フラグを解除する（DEBT-05）。

    遅延評価（PAT2-DEBT-01）。日次バッチ or アクセス時に呼ばれる。72h 未満は no-op。

    Args:
        state: 現在の SafeguardState。
        now: 現在時刻。

    Returns:
        解除条件を満たせば負債・冷却を OFF にした SafeguardState、未満なら変更なし。
    """
    if state.debt_release_requested_at is None:
        return state
    requested_at = datetime.fromisoformat(state.debt_release_requested_at)
    if now - requested_at < timedelta(hours=DEBT_RELEASE_COOLDOWN_HOURS):
        return state  # 72h 未満は no-op
    updated = state.model_copy(deep=True)
    updated.flags.has_debt = False
    updated.flags.cooldown_on = False
    updated.debt_release_requested_at = None
    return updated
