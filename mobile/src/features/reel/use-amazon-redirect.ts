/**
 * useAmazonRedirect: 確認オーバーレイ確定 → 遷移記録 → Amazon Deep Link（M-03）。
 *
 * ダブルタップ → 確認オーバーレイ（FR-REEL-05）を経た後に呼ぶ。冪等キーを生成し
 * POST /v1/amazon-transitions を叩き、ExpAward を返す。遷移後トーストと自動遷移は
 * 呼び出し側 UI（reel-screen）が POST_TAP_REDIRECT_MS で制御する。
 */

import { useMutation } from '@tanstack/react-query';

import { makeClientTransitionId } from './client-transition-id';
import { recordAmazonTransition, type ReelApiClient } from './reel-api';
import type { ExpAward, ReelCard } from './types';

/** Amazon 遷移を起動するコールバックを提供するフック。 */
export function useAmazonRedirect(client: ReelApiClient) {
  return useMutation<ExpAward, Error, ReelCard>({
    mutationFn: (card: ReelCard): Promise<ExpAward> =>
      recordAmazonTransition(client, {
        cardId: card.cardId,
        asin: card.product.asin,
        context: 'reel',
        clientTransitionId: makeClientTransitionId(card.cardId),
      }),
  });
}
