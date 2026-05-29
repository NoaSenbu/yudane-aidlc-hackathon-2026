/**
 * S-03 SafeguardPolicy — 月間上限 / 冷却 / 負債の判定（純関数）。
 *
 * 設計: business-logic-model.md ALG-SG / business-rules.md SG-01〜10（Q2=A 段階評価）。
 * Mobile（M-07 等）と Backend（B-09）が同一実装を使い、UX とゲート判定を一致させる。
 */

import {
  DEBT_MONTHLY_LIMIT_RATIO,
  DEFAULT_MONTHLY_LIMIT_RATIO,
  WARN_THRESHOLD_RATIO,
} from './constants';

/** 判定への入力。 */
export interface SafeguardInput {
  /** 今月の Amazon 遷移回数。 */
  transitionCountMonth: number;
  /** 適用中の月間上限（円）。 */
  monthlyLimitYen: number;
  /** 今月の遷移額合計（円）。 */
  currentBudgetUsedYen: number;
  flags: {
    /** 冷却モード（手動 or 3 連続拒否で自動）。 */
    cooldownOn: boolean;
    /** 静観ウィーク。 */
    quietWeek: boolean;
    /** 負債保有フラグ。 */
    hasDebt: boolean;
  };
}

/** block/warn の根拠コード（DomainError.code と対応）。 */
export type SafeguardReasonCode =
  | 'safeguard.cooldown'
  | 'safeguard.quiet-week'
  | 'safeguard.monthly-limit-exceeded'
  | 'safeguard.debt-restricted'
  | 'safeguard.near-limit'
  | 'allowed';

/** 判定結果。 */
export interface SafeguardDecision {
  decision: 'allow' | 'block' | 'warn';
  reasonCode: SafeguardReasonCode;
  effectiveLimitYen: number;
  remainingYen: number;
}

/**
 * Amazon 遷移 / 論破開始の可否を段階評価で判定する。
 *
 * 評価順（SG-01）: cooldown → quietWeek → 実効上限決定（debt 切替）→ 上限超過 block →
 * 80% 超 warn → allow。warn は遷移を止めず通知のみ（SG-07、NG-6 回避）。
 *
 * @param input - 判定入力
 * @returns 判定結果（decision / reasonCode / 実効上限 / 残額）
 */
export function decideAllow(input: SafeguardInput): SafeguardDecision {
  const { monthlyLimitYen, currentBudgetUsedYen, flags } = input;

  // 実効上限（debt で再スケール、SG-04）。warn/block どちらの分岐でも返す
  const effectiveLimitYen = flags.hasDebt
    ? Math.round(monthlyLimitYen * (DEBT_MONTHLY_LIMIT_RATIO / DEFAULT_MONTHLY_LIMIT_RATIO))
    : monthlyLimitYen;
  const remainingYen = Math.max(0, effectiveLimitYen - currentBudgetUsedYen);

  const block = (reasonCode: SafeguardReasonCode): SafeguardDecision => ({
    decision: 'block',
    reasonCode,
    effectiveLimitYen,
    remainingYen,
  });

  // ステップ1: フラグ系の即時 block（最優先、SG-02/03）
  if (flags.cooldownOn) {
    return block('safeguard.cooldown');
  }
  if (flags.quietWeek) {
    return block('safeguard.quiet-week');
  }

  // ステップ3: 上限超過の block（SG-05）
  if (currentBudgetUsedYen >= effectiveLimitYen) {
    return block(flags.hasDebt ? 'safeguard.debt-restricted' : 'safeguard.monthly-limit-exceeded');
  }

  // ステップ4: 80% 超で warn（SG-06、遷移は止めない）
  if (currentBudgetUsedYen >= effectiveLimitYen * WARN_THRESHOLD_RATIO) {
    return {
      decision: 'warn',
      reasonCode: 'safeguard.near-limit',
      effectiveLimitYen,
      remainingYen,
    };
  }

  // ステップ5: 許可
  return { decision: 'allow', reasonCode: 'allowed', effectiveLimitYen, remainingYen };
}
