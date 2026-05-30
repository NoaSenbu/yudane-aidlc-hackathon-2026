/**
 * リールのジェスチャー判定ロジック（M-03 / ALG-GESTURE / Q5=A）。
 *
 * 純粋関数として実装し、UI（reanimated/gesture-handler）から呼ぶ。
 * 閾値・優先順位・遷移ガードは business-rules REEL-GES-01〜08 準拠。
 */

/** スワイプ確定閾値（px、REEL-GES-01/02）。 */
export const SWIPE_THRESHOLD_PX = 60;
/** ダブルタップ間隔上限（ms、REEL-GES-03）。 */
export const DOUBLE_TAP_MS = 350;
/** 同一カード左スワイプのクールダウン閾値（REEL-GES-06）。 */
export const LEFT_SWIPE_COOLDOWN_COUNT = 3;
/** Amazon タップ後のレポート自動遷移（ms、REEL-GES-08）。 */
export const POST_TAP_REDIRECT_MS = 1_200;

/** ジェスチャー入力。 */
export type ReelGesture = 'swipe-left' | 'swipe-right' | 'double-tap' | 'vertical-scroll';

/** ジェスチャー結果アクション。 */
export type GestureAction =
  | 'navigate-debate'
  | 'skip-toast'
  | 'register-cart-watch'
  | 'show-transition-overlay'
  | 'cooldown-blocked'
  | 'next-card';

/** ジェスチャー判定の入力。 */
export interface GestureInput {
  gesture: ReelGesture;
  /** 水平移動量（px、左右スワイプ用。左は負）。 */
  dx?: number;
  /** ダブルタップの 2 タップ間隔（ms）。 */
  tapIntervalMs?: number;
  /** 「論破不要」設定（US-02-03 AC-3）。 */
  debateDisabled?: boolean;
  /** 同一カードへの左スワイプ累積回数（REEL-GES-06）。 */
  leftSwipeCount?: number;
}

/**
 * ジェスチャーから実行アクションを決定する（純粋関数、決定論）。
 *
 * 優先順位は呼び出し側で解決済みの単一ジェスチャーを受け取る前提
 * （double-tap > 水平スワイプ > vertical-scroll、REEL-GES-04）。
 *
 * @param input - ジェスチャー入力。
 * @returns 実行アクション。
 */
export function resolveGesture(input: GestureInput): GestureAction {
  switch (input.gesture) {
    case 'double-tap':
      // ダブルタップは必ず確認オーバーレイ（FR-REEL-05、削除不可）
      if ((input.tapIntervalMs ?? Number.POSITIVE_INFINITY) <= DOUBLE_TAP_MS) {
        return 'show-transition-overlay';
      }
      return 'next-card';
    case 'swipe-left':
      if (Math.abs(input.dx ?? 0) < SWIPE_THRESHOLD_PX) {
        return 'next-card';
      }
      if ((input.leftSwipeCount ?? 0) > LEFT_SWIPE_COOLDOWN_COUNT) {
        return 'cooldown-blocked';
      }
      if (input.debateDisabled === true) {
        return 'skip-toast';
      }
      return 'navigate-debate';
    case 'swipe-right':
      if (Math.abs(input.dx ?? 0) < SWIPE_THRESHOLD_PX) {
        return 'next-card';
      }
      return 'register-cart-watch';
    case 'vertical-scroll':
    default:
      return 'next-card';
  }
}

/** 論破トリガー名（FR-DEBATE-01、左スワイプ＝reel-refuse）。 */
export const DEBATE_TRIGGER = 'reel-refuse' as const;
