/**
 * リール API 呼び出し（M-03 → M-12 ApiClient）。
 *
 * フック（useReelFeed / useAmazonRedirect）から使うサーバー I/O 関数。
 * ApiClient はインターフェースで受け取り、テストはフェイク注入する（Outside-In）。
 */

import type { AmazonTransitionRequest, ExpAward, ReelPage } from './types';

/** ApiClient の最小インターフェース（実体は Unit-1 M-12）。 */
export interface ReelApiClient {
  apiFetch<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T>;
}

/**
 * リールフィードを取得する（GET /v1/reel、カーソルページング）。
 *
 * @param client - ApiClient。
 * @param cursor - 不透明カーソル（初回は undefined）。
 * @param limit - 1 ページ件数。
 * @returns リールページ。
 */
export async function fetchReel(
  client: ReelApiClient,
  cursor?: string,
  limit?: number,
): Promise<ReelPage> {
  const params = new URLSearchParams();
  if (cursor !== undefined) params.set('cursor', cursor);
  if (limit !== undefined) params.set('limit', String(limit));
  const query = params.toString();
  const path = query ? `/v1/reel?${query}` : '/v1/reel';
  return client.apiFetch<ReelPage>(path, { method: 'GET' });
}

/**
 * Amazon 遷移を記録する（POST /v1/amazon-transitions）。
 *
 * @param client - ApiClient。
 * @param request - 遷移リクエスト（冪等キー含む）。
 * @returns EXP 加算結果。
 */
export async function recordAmazonTransition(
  client: ReelApiClient,
  request: AmazonTransitionRequest,
): Promise<ExpAward> {
  return client.apiFetch<ExpAward>('/v1/amazon-transitions', {
    method: 'POST',
    body: request,
  });
}
