/**
 * お取り置きフィルタ・集計（R3.3, R4）— タブ値 → status 判定・フィルタ・集計の純関数群。
 */

import type { CartWatchItemDto } from './use-cart-watch-item';

export type FilterTab = 'すべて' | 'おすすめ' | 'まもなく' | '休眠';
type CartStatus = CartWatchItemDto['status'];

/**
 * タブ値ごとの status 判定条件（R4.1 一意対応付け）。
 * - すべて: 全件
 * - おすすめ: watching（新規監視中の推奨）
 * - まもなく: notified-30m | notified-6h | notified-24h（追撃通知進行中）
 * - 休眠: watching_orphaned | purchased | dismissed（停滞・終端）
 */
export function matchesFilter(tab: FilterTab, status: CartStatus): boolean {
  switch (tab) {
    case 'すべて':
      return true;
    case 'おすすめ':
      return status === 'watching';
    case 'まもなく':
      return (
        status === 'notified-30m' || status === 'notified-6h' || status === 'notified-24h'
      );
    case '休眠':
      return status === 'watching_orphaned' || status === 'purchased' || status === 'dismissed';
  }
}

/** 選択タブで一覧を絞り込む（R4.2, R4.3, R4.5）。 */
export function filterWatchItems(
  items: CartWatchItemDto[],
  tab: FilterTab,
): CartWatchItemDto[] {
  if (tab === 'すべて') return items;
  return items.filter((item) => matchesFilter(tab, item.status));
}

/** 表示対象の件数と価格合計を集計する（R3.3, R4.4）。 */
export function aggregateWatchItems(items: CartWatchItemDto[]): {
  count: number;
  totalYen: number;
} {
  return {
    count: items.length,
    totalYen: items.reduce((sum, item) => sum + item.productMeta.priceYen, 0),
  };
}

/** ステータスの日本語表示ラベル。 */
export const STATUS_LABEL: Record<CartStatus, string> = {
  watching:           'おすすめ',
  'notified-30m':     'まもなく(30分)',
  'notified-6h':      'まもなく(6時間)',
  'notified-24h':     'まもなく(24時間)',
  purchased:          '購入済み',
  dismissed:          '解除済み',
  watching_orphaned:  '休眠',
};
