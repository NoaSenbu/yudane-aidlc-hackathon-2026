/**
 * S-03 拡張 — 通知配信可否判定（evaluateNotification）。
 *
 * 既存 decideAllow を内包する薄いラッパー。SG-01 評価順を継承しつつ、以下 2 点を追加:
 * 1. cooldownUntil が現在時刻より未来 → block（自動冷却、SG-02 直前で評価）
 * 2. decideAllow の warn 判定は通知では block に格上げ（プッシュ通知は介入性が高く、
 *    NG-6 罪悪感強要を避けるため near-limit 時も通知抑制、SG-07 の例外）
 *
 * 設計: Unit-5 functional-design.md §2.4 / Property 5（Safeguard 連携での通知抑制）
 *      Unit-5 owner として追加、Unit-7 owner（Member C）レビュー必須。
 */

import { decideAllow, type SafeguardDecision, type SafeguardInput } from './decide-allow';

/** 通知判定の追加コンテキスト（cooldownUntil 自動冷却を SG-01 に追加）。 */
export interface NotificationContext {
  /** ユーザー ID（ログ相関用、判定ロジックには未使用）。 */
  userId: string;
  /** 適用中の月間上限（円、business-rules.md SG-04 整合）。 */
  monthlyLimitYen: number;
  /** 今月の遷移額合計（円、business-rules.md SG-05 整合）。 */
  currentBudgetUsedYen: number;
  /** 冷却モード（手動 ON or 3 連続拒否で自動）。 */
  cooldownOn: boolean;
  /** 自動冷却の解除時刻（ISO 8601、未来なら block）。 */
  cooldownUntil?: string;
  /** 「静観ウィーク」モード。 */
  quietWeek: boolean;
  /** 負債保有フラグ（SG-04、実効上限の re-scale 判定）。 */
  hasDebt: boolean;
}

/**
 * 通知配信可否判定（B-06 NotificationDispatcher が呼び出す）。
 *
 * 戻り値は既存 SafeguardDecision を維持（reasonCode / effectiveLimitYen / remainingYen を
 * NotificationLogs に記録するため）。
 *
 * @param ctx - 通知判定コンテキスト
 * @param now - 現在時刻（テスト注入用、省略時は new Date()）
 * @returns 判定結果（warn は block に格上げ済み）
 */
export function evaluateNotification(ctx: NotificationContext, now: Date = new Date()): SafeguardDecision {
  // 自動冷却（SG-02 cooldownOn の手動フラグに加えて時刻ベース）
  if (ctx.cooldownUntil && new Date(ctx.cooldownUntil) > now) {
    return {
      decision: 'block',
      reasonCode: 'safeguard.cooldown',
      effectiveLimitYen: ctx.monthlyLimitYen,
      remainingYen: Math.max(0, ctx.monthlyLimitYen - ctx.currentBudgetUsedYen),
    };
  }

  const input: SafeguardInput = {
    transitionCountMonth: 0, // 通知判定では未使用
    monthlyLimitYen: ctx.monthlyLimitYen,
    currentBudgetUsedYen: ctx.currentBudgetUsedYen,
    flags: {
      cooldownOn: ctx.cooldownOn,
      quietWeek: ctx.quietWeek,
      hasDebt: ctx.hasDebt,
    },
  };
  const decision = decideAllow(input);

  // warn は通知では block に格上げ（SG-07 例外、NG-6 配慮）
  if (decision.decision === 'warn') {
    return { ...decision, decision: 'block' };
  }
  return decision;
}
