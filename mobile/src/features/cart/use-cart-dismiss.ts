/**
 * M-05 useCartDismiss hook — 監視解除 mutation + 楽観的更新。
 *
 * DELETE は Unit-1 Q7=B により冪等のため Idempotency-Key 不要。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiFetch } from '@yudane/api-client';

import type { CartListResponse } from './use-cart-watch-items';

export function useCartDismiss() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (asin: string) =>
      apiFetch<void>(`/v1/cart-watch-items/${asin}`, {
        method: 'DELETE',
      }),
    onMutate: async (asin: string) => {
      // 楽観的更新: 一覧から即座に除去
      await queryClient.cancelQueries({ queryKey: ['cart-watch-items'] });
      const previous = queryClient.getQueriesData<CartListResponse>({ queryKey: ['cart-watch-items'] });
      queryClient.setQueriesData<CartListResponse>(
        { queryKey: ['cart-watch-items'] },
        (old) => {
          if (!old) return old;
          return { ...old, items: old.items.filter((item) => item.asin !== asin) };
        },
      );
      return { previous };
    },
    onError: (_err, _asin, context) => {
      // エラー時は楽観的更新をロールバック
      if (context?.previous) {
        for (const [key, data] of context.previous) {
          queryClient.setQueryData(key, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['cart-watch-items'] });
    },
  });
}
