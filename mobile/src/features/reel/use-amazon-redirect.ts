/**
 * useAmazonRedirect — Special Link 構築 → 遷移記録 → Linking.openURL（R6, R7, R10）。
 *
 * 処理順: buildSpecialLink → POST /v1/amazon-transitions(5s timeout) → Linking.openURL
 * 記録失敗でも遷移は継続（R6.5）。タグ未設定 / ASIN 不正なら遷移しない（R6.7, R6.3）。
 */

import { useState } from 'react';
import { Alert, Linking } from 'react-native';
import { useMutation } from '@tanstack/react-query';

import { makeClientTransitionId } from './client-transition-id';
import { recordAmazonTransition, type ReelApiClient } from './reel-api';
import { buildSpecialLink, SpecialLinkValidationError } from './special-link';
import type { ExpAward } from './types';

// デモ用フォールバックタグ（環境変数未設定時）
const TRACKING_TAG =
  (typeof process !== 'undefined' && process.env['EXPO_PUBLIC_ASSOCIATES_TRACKING_TAG']) ||
  'yudane-demo-22';

const TRANSITION_TIMEOUT_MS = 5_000;

export type AmazonRedirectContext = 'reel' | 'debate-agree' | 'cart-attack';

export interface AmazonRedirectInput {
  cardId: string;
  asin: string;
  context: AmazonRedirectContext;
}

/** Amazon 遷移サービス（R6, R7）。 */
export function useAmazonRedirect(client: ReelApiClient): {
  redirect: (input: AmazonRedirectInput) => Promise<void>;
  displayedYudaneLevel: number | null;
  isPending: boolean;
  error: Error | null;
} {
  const [displayedYudaneLevel, setDisplayedYudaneLevel] = useState<number | null>(null);

  const mutation = useMutation<void, Error, AmazonRedirectInput>({
    mutationFn: async ({ cardId, asin, context }) => {
      // 1. Special Link URL 構築（R6.1, R6.3）
      let url: string;
      try {
        url = buildSpecialLink(asin, TRACKING_TAG);
      } catch (err) {
        const msg =
          err instanceof SpecialLinkValidationError
            ? err.message
            : 'URLを構築できませんでした';
        Alert.alert('遷移エラー', msg);
        return;
      }

      // 2. 遷移記録（5s timeout、R6.4）— 失敗しても遷移継続（R6.5）
      try {
        const award = await Promise.race<ExpAward>([
          recordAmazonTransition(client, {
            cardId,
            asin,
            context,
            clientTransitionId: makeClientTransitionId(cardId),
          }),
          new Promise<never>((_, reject) =>
            setTimeout(
              () => reject(new Error('遷移記録がタイムアウトしました')),
              TRANSITION_TIMEOUT_MS,
            ),
          ),
        ]);
        // EXP 加算成功 → displayedYudaneLevel に反映（R7.2）
        setDisplayedYudaneLevel(award.totalExp);
      } catch {
        // EXP 未記録エラー表示（遷移は継続、R6.5）
        Alert.alert('', 'EXPが記録できませんでしたが、Amazonへ遷移します');
      }

      // 3. Amazon に遷移（R6.4）
      await Linking.openURL(url);
    },
  });

  return {
    redirect: (input) => mutation.mutateAsync(input),
    displayedYudaneLevel,
    isPending: mutation.isPending,
    error: mutation.error,
  };
}
