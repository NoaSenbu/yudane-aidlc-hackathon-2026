/**
 * S-03 SafeguardPolicy 定数（business-rules.md §2.1）。
 * 変更は破壊的影響があるため、PR で必ず影響範囲を説明する。
 */

/** 予算感に対する標準月間上限比率。 */
export const DEFAULT_MONTHLY_LIMIT_RATIO = 0.7;

/** 負債保有者の月間上限比率。 */
export const DEBT_MONTHLY_LIMIT_RATIO = 0.35;

/** 3 連続拒否後のクールダウン（秒、24h）。 */
export const DEBATE_COOLDOWN_SECONDS = 86_400;

/** カート追撃のステップ（秒、30m / 6h / 24h）。 */
export const CART_ATTACK_STEPS_SECONDS: readonly number[] = [1_800, 21_600, 86_400];

/** 実効上限の何割で warn を出すか。 */
export const WARN_THRESHOLD_RATIO = 0.8;
