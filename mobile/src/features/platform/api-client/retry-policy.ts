/**
 * リトライ判定の純関数（RETRY-01〜06）。ApiClient 本体から分離し PBT 対象とする。
 */

import { RETRY_MAX_ATTEMPTS, RETRYABLE_STATUS } from './types';

/**
 * リトライすべきかを判定する。
 *
 * @param params.method - HTTP メソッド
 * @param params.status - HTTP ステータス（ネットワーク断は undefined）
 * @param params.attempt - 既に試行した回数（0 始まり）
 * @param params.explicitRetry - GET 以外で明示許可されたか
 * @returns リトライするなら true
 */
export function shouldRetry(params: {
  method: string;
  status: number | undefined;
  attempt: number;
  explicitRetry: boolean;
}): boolean {
  const { method, status, attempt, explicitRetry } = params;

  // 上限到達（RETRY-03: 最大 RETRY_MAX_ATTEMPTS 回）
  if (attempt >= RETRY_MAX_ATTEMPTS) {
    return false;
  }

  // 冪等性: GET のみ（明示許可で例外）。RETRY-01
  const isIdempotent = method.toUpperCase() === 'GET' || explicitRetry;
  if (!isIdempotent) {
    return false;
  }

  // ネットワーク断（status なし）はリトライ対象
  if (status === undefined) {
    return true;
  }

  // 429 / 503 のみ（RETRY-02）
  return RETRYABLE_STATUS.has(status);
}

/**
 * 指数バックオフ + jitter の待機時間を計算する（RETRY-03）。
 *
 * @param attempt - 試行回数（0 始まり）
 * @param baseMs - 基数
 * @param jitterMs - 追加ジッタの最大値
 * @returns 待機ミリ秒
 */
export function backoffDelayMs(attempt: number, baseMs: number, jitterMs: number): number {
  const exponential = baseMs * 2 ** attempt;
  const jitter = Math.floor(Math.random() * (jitterMs + 1));
  return exponential + jitter;
}
