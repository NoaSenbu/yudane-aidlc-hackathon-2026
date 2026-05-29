/**
 * M-05 useCartWatchItems hook — 監視リスト一覧取得（NFR Q2=A' staleTime=60s 一覧）。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1
 */

import { useQuery } from '@tanstack/react-query';

import { apiFetch } from '@yudane/api-client';

import type { CartWatchItemDto } from './use-cart-watch-item';

export type CartStatusFilter =
  | 'active'
  | 'watching'
  | 'notified-30m'
  | 'notified-6h'
  | 'notified-24h'
  | 'watching_orphaned'
  | 'purchased'
  | 'dismissed';

export interface CartListResponse {
  items: CartWatchItemDto[];
  nextCursor?: string;
}

/** 監視リスト一覧 hook。staleTime=60s で短期間 cache 利用。 */
export function useCartWatchItems(params: {
  status?: CartStatusFilter;
  limit?: number;
  cursor?: string;
} = {}) {
  const { status = 'active', limit = 10, cursor } = params;
  const search = new URLSearchParams();
  search.set('status', status);
  search.set('limit', String(limit));
  if (cursor) {
    search.set('cursor', cursor);
  }
  return useQuery({
    queryKey: ['cart-watch-items', status, limit, cursor ?? ''],
    queryFn: () => apiFetch<CartListResponse>(`/v1/cart-watch-items?${search.toString()}`),
    staleTime: 60_000, // NFR Q2=A' 一覧は 60 秒間 cache 利用
  });
}
