/**
 * M-05 CartInterceptScreen — 画面状態管理の純粋ロジック層（v3 強化、Issue R7 対応）。
 *
 * Mobile UI 結線時に Member D がそのまま import できるよう、UI 不要部分の
 * ロジックを完全純粋関数化する。本ファイルの関数群は React / RN に依存しない。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1
 */

import type { CartWatchItemDto } from './use-cart-watch-item';

/** Associates 開示文言（FR-PROFILE-04 / NG-8 / US-03-04 AC-3 整合、6 巡目追加）。 */
export const ASSOCIATES_DISCLOSURE_TEXT =
  'YUDANE は Amazon Associates として、紹介リンク経由の購入で Amazon から紹介料を受け取っています';

export type CartScreenMode = 'list' | 'detail' | 'intake';

/** 追撃タイムラインの進捗状態。 */
export interface TimelineProgress {
  step: '30m' | '6h' | '24h' | 'completed';
  remainingSec: number;
  isCurrentStep: boolean;
  isPast: boolean;
}

/** 警告アイコン表示判定（NFR Design 2 巡目 Issue LLLL: watching_orphaned 可視化）。 */
export function shouldShowOrphanedWarning(status: CartWatchItemDto['status']): boolean {
  return status === 'watching_orphaned';
}

/** Reduce Motion アニメ設定（WCAG 2.2 AA 整合、NFR Requirements §7.1）。 */
export function getAnimationConfig(reduceMotion: boolean): {
  duration: number;
  easing: 'linear' | 'ease-in-out';
  blink: boolean;
} {
  return reduceMotion
    ? { duration: 0, easing: 'linear', blink: false }
    : { duration: 300, easing: 'ease-in-out', blink: true };
}

/**
 * 追撃タイムラインの進捗を計算する。
 *
 * @param item - 監視アイテム
 * @param now - 現在時刻（テスト注入用）
 * @returns 30m / 6h / 24h ステップそれぞれの進捗
 */
export function computeTimelineProgress(
  item: CartWatchItemDto,
  now: Date = new Date(),
): TimelineProgress[] {
  const createdAt = new Date(item.createdAt);
  const stepDelaysSec: Record<'30m' | '6h' | '24h', number> = {
    '30m': 1_800,
    '6h': 21_600,
    '24h': 86_400,
  };

  const elapsedSec = Math.floor((now.getTime() - createdAt.getTime()) / 1000);

  return (Object.entries(stepDelaysSec) as Array<['30m' | '6h' | '24h', number]>).map(
    ([step, delay]) => {
      const remainingSec = Math.max(0, delay - elapsedSec);
      const isPast = elapsedSec >= delay;
      // notified-{step} に遷移済みなら past 判定
      const notifiedKey = `notified-${step}` as const;
      const isNotified = item.status === notifiedKey || _isStatusAfter(item.status, notifiedKey);
      return {
        step,
        remainingSec,
        isCurrentStep: !isPast && !isNotified && _findCurrentStep(item.status, step),
        isPast: isPast || isNotified,
      };
    },
  );
}

/** ステータスが指定 step を経過済みかを判定する（内部）。
 *
 * 2026-05-29 Issue Z6 修正: status enum 完全リスト化（watching_orphaned 追加）。
 * 通知系ステータスの順序判定のため、purchased / dismissed / watching_orphaned は
 * 末尾扱いで「経過済み（最終 notified を超えた状態）」とみなす。
 */
function _isStatusAfter(
  status: CartWatchItemDto['status'],
  step: 'notified-30m' | 'notified-6h' | 'notified-24h',
): boolean {
  // 通知系の経過判定のため、通知ステップのみ順序付けする
  const notifiedOrder: Record<'notified-30m' | 'notified-6h' | 'notified-24h', number> = {
    'notified-30m': 1,
    'notified-6h': 2,
    'notified-24h': 3,
  };
  const stepIdx = notifiedOrder[step];

  // 終端ステータス（purchased / dismissed）は最後の通知より「後」
  if (status === 'purchased' || status === 'dismissed') {
    return stepIdx <= 3;
  }
  // watching_orphaned は通知未到達（watching 同等扱い）
  if (status === 'watching' || status === 'watching_orphaned') {
    return false;
  }
  // notified-* は数値比較
  if (status === 'notified-30m' || status === 'notified-6h' || status === 'notified-24h') {
    return notifiedOrder[status] > stepIdx;
  }
  return false;
}

/** 現在進行中のステップを判定する。
 *
 * 2026-05-29 Issue Z6 修正: watching_orphaned も watching 同等の「30m 待ち」状態として扱う。
 */
function _findCurrentStep(
  status: CartWatchItemDto['status'],
  step: '30m' | '6h' | '24h',
): boolean {
  // status=watching / watching_orphaned → 30m が現在
  if ((status === 'watching' || status === 'watching_orphaned') && step === '30m') return true;
  if (status === 'notified-30m' && step === '6h') return true;
  if (status === 'notified-6h' && step === '24h') return true;
  return false;
}

/**
 * 楽観的更新の適用（dismiss 時）— 一覧から該当 asin を即座に除去。
 *
 * @param items - 現在の一覧
 * @param asin - 除去対象の ASIN
 * @returns 楽観更新後の一覧
 */
export function applyOptimisticDismiss(
  items: CartWatchItemDto[],
  asin: string,
): CartWatchItemDto[] {
  return items.filter((item) => item.asin !== asin);
}

/** 楽観的更新の rollback（API エラー時）— 元の一覧に戻す。 */
export function rollbackOptimisticDismiss(
  previous: CartWatchItemDto[],
): CartWatchItemDto[] {
  return previous;
}
