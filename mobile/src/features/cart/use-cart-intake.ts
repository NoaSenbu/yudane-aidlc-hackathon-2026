/**
 * M-05 useCartIntake hook — Share 受信 → 監視登録 mutation。
 *
 * Q2=A 反映: Mobile 側で抽出済み ASIN を Backend に送信、Backend が再検証。
 * Q7=B（Unit-1）: POST は Idempotency-Key 必須（uuid v7）。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { v7 as uuidv7 } from 'uuid';

import { apiFetch } from '@yudane/api-client';

import type { CartWatchItemDto } from './use-cart-watch-item';

export interface CartIntakeRequest {
  url: string;
  asin: string;
}

export interface CartIntakeResponse {
  item: CartWatchItemDto;
  isNewlyCreated: boolean;
}

export function useCartIntake() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CartIntakeRequest) => {
      return apiFetch<CartIntakeResponse>('/v1/cart-watch-items', {
        method: 'POST',
        idempotencyKey: uuidv7(),
        body: JSON.stringify({ url: input.url, asin: input.asin }),
      });
    },
    onSuccess: () => {
      // 一覧キャッシュを invalidate（取込直後に M-05 一覧が最新化）
      queryClient.invalidateQueries({ queryKey: ['cart-watch-items'] });
    },
  });
}
