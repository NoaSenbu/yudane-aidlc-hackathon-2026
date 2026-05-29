/**
 * Unit-1 AuthTokenProvider の実装（MFA-06）。
 *
 * ApiClient（Unit-1）に注入され、401 single-shot refresh から refresh が呼ばれる。
 * Amplify ラッパー（AmplifyAuthGateway）に委譲する。
 */

import type { AuthTokenProvider } from '../../platform/api-client';
import type { AmplifyAuthGateway } from './amplify-auth';

/**
 * AmplifyAuthGateway から AuthTokenProvider を生成する。
 *
 * @param gateway - Amplify Auth ラッパー
 * @param onExpired - セッション失効時のコールバック（AppShell.onAuthExpired）
 * @returns ApiClient に注入する AuthTokenProvider
 */
export function createAuthTokenProvider(
  gateway: AmplifyAuthGateway,
  onExpired: () => void,
): AuthTokenProvider {
  return {
    getAccessToken: () => gateway.getAccessToken(),
    refresh: async () => {
      const tokens = await gateway.refresh();
      return tokens !== null;
    },
    onAuthExpired: onExpired,
  };
}
