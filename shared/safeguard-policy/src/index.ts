export {
  CART_ATTACK_STEPS_SECONDS,
  DEBATE_COOLDOWN_SECONDS,
  DEBT_MONTHLY_LIMIT_RATIO,
  DEFAULT_MONTHLY_LIMIT_RATIO,
  WARN_THRESHOLD_RATIO,
} from './constants';
export { decideAllow } from './decide-allow';
export type { SafeguardDecision, SafeguardInput, SafeguardReasonCode } from './decide-allow';



# ===== Unit-5 Cart Intercept owner で追加（functional-design.md §2.4）=====


@dataclass(frozen=True)
class NotificationContext:
    """通知判定の追加コンテキスト（cooldown_until 自動冷却を SG-01 に追加）。"""

    user_id: str
    monthly_limit_yen: int
    current_budget_used_yen: int
    cooldown_on: bool
    quiet_week: bool
    has_debt: bool
    cooldown_until: Optional[str] = None  # ISO 8601、未来なら block


def evaluate_notification(
    user_id: str,
    monthly_limit_yen: int,
    current_budget_used_yen: int,
    cooldown_on: bool,
    quiet_week: bool,
    has_debt: bool,
    cooldown_until: Optional[str] = None,
    now: Optional[datetime] = None,
) -> SafeguardDecision:
    """通知配信可否判定（B-06 NotificationDispatcher が呼び出す）。

    decide_allow ラッパー。SG-01 評価順を継承しつつ、以下 2 点を追加:
    1. cooldown_until が現在時刻より未来 → block（自動冷却、SG-02 直前で評価）
    2. decide_allow の warn 判定は通知では block に格上げ
       （SG-07 例外、NG-6 罪悪感強要を避けるため near-limit 時も通知抑制）

    Args:
        user_id: ユーザー ID（ログ相関用、判定ロジックには未使用）。
        monthly_limit_yen: 月間上限（円）。
        current_budget_used_yen: 当月の遷移額合計（円）。
        cooldown_on: 冷却モード（手動 or 3 連続拒否で自動）。
        quiet_week: 静観ウィーク。
        has_debt: 負債保有フラグ。
        cooldown_until: 自動冷却の解除時刻（ISO 8601）。
        now: 現在時刻（テスト注入用、省略時は datetime.now(UTC)）。

    Returns:
        判定結果。warn は block に格上げ済み。reason_code / effective_limit_yen / remaining_yen
        を NotificationLogs に記録できる形式。
    """
    current_time = now if now is not None else datetime.now(timezone.utc)

    # 自動冷却（SG-02 cooldown_on の手動フラグに加えて時刻ベース）
    if cooldown_until and datetime.fromisoformat(cooldown_until) > current_time:
        return SafeguardDecision(
            decision="block",
            reason_code="safeguard.cooldown",
            effective_limit_yen=monthly_limit_yen,
            remaining_yen=max(0, monthly_limit_yen - current_budget_used_yen),
        )

    input_data = SafeguardInput(
        transition_count_month=0,  # 通知判定では未使用
        monthly_limit_yen=monthly_limit_yen,
        current_budget_used_yen=current_budget_used_yen,
        flags=SafeguardFlags(
            cooldown_on=cooldown_on,
            quiet_week=quiet_week,
            has_debt=has_debt,
        ),
    )
    decision = decide_allow(input_data)

    # warn は通知では block に格上げ（SG-07 例外）
    if decision.decision == "warn":
        return SafeguardDecision(
            decision="block",
            reason_code=decision.reason_code,
            effective_limit_yen=decision.effective_limit_yen,
            remaining_yen=decision.remaining_yen,
        )
    return decision
