/**
 * M-05 useCartWatchItem hook — 単一監視アイテム取得（NFR Q2=A' staleTime=0 詳細）。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1
 */

import { useQuery } from '@tanstack/react-query';

import { apiFetch } from '@yudane/api-client';

/** CartWatchItemDto（OpenAPI shared/schema/paths/cart.yaml 整合の最小型）。 */
export interface CartWatchItemDto {
  itemId: string;
  asin: string;
  status:
    | 'watching'
    | 'notified-30m'
    | 'notified-6h'
    | 'notified-24h'
    | 'purchased'
    | 'dismissed'
    | 'watching_orphaned';
  productMeta: {
    title: string;
    priceYen: number;
    imageUrl?: string;
    reviewSummary?: string;
    brand?: string;
    category?: string;
  };
  attackSchedule?: {
    schedule_30m: string;
    schedule_6h: string;
    schedule_24h: string;
  } | null;
  triggerSource?: string;
  retry_count?: number;
  lastNotifiedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

/** 監視アイテムの単一取得 hook。staleTime=0 で常に最新（通知タップ時の即時反映）。 */
export function useCartWatchItem(asin: string) {
  return useQuery({
    queryKey: ['cart-watch-item', asin],
    queryFn: () => apiFetch<CartWatchItemDto>(`/v1/cart-watch-items/${asin}`),
    staleTime: 0, // NFR Q2=A' 詳細は常に refetch（status 遷移の即時反映が必要）
  });
}
