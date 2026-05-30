/**
 * apiFetch — `ApiClient.request` の薄いラッパー。Unit-5 / Unit-3 / Unit-4 / Unit-6 / Unit-7 / Unit-8
 * の features/* で React Hook の queryFn / mutationFn から呼び出すために提供する。
 *
 * 設計: api-contracts.md §4 / Unit-1 LC-01 ApiClient と整合。本ヘルパーは状態を持たず、
 * ApiClient のシングルトンを `setApiClient()` で受け取り、`apiFetch<T>()` で呼び出す。
 *
 * 2026-05-29 追加（Issue B3 / Unit-5 設計から、各 Unit の features で利用）。
 */

import type { ApiClient, RequestOptions } from './api-client';

/** ヘッダ用の Idempotency-Key を `RequestOptions` から扱いやすくするための拡張オプション。 */
export interface ApiFetchOptions extends Omit<RequestOptions, 'headers'> {
  /** Idempotency-Key ヘッダ（POST / PATCH の冪等性、Unit-1 Q7=B）。 */
  idempotencyKey?: string;
  /** 任意の追加ヘッダ。 */
  headers?: HeadersInit;
}

let apiClientInstance: ApiClient | null = null;

/** AppShell のセットアップで一度だけ呼ぶ（M-01 AppShell.setupProviders 内）。 */
export function setApiClient(client: ApiClient): void {
  apiClientInstance = client;
}

/**
 * 単発の REST 呼び出し（hooks 内の queryFn / mutationFn 用）。
 *
 * @example
 * useQuery({
 *   queryKey: ['cart-watch-item', asin],
 *   queryFn: () => apiFetch<CartWatchItemDto>(`/v1/cart-watch-items/${asin}`),
 * });
 *
 * @param path - パス（baseUrl からの相対）
 * @param options - HTTP オプション + idempotencyKey
 * @returns レスポンス body
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  if (!apiClientInstance) {
    throw new Error('apiFetch: setApiClient() を AppShell 起動時に呼んでください');
  }

  const { idempotencyKey, headers, ...rest } = options;
  const mergedHeaders = new Headers(headers);
  if (idempotencyKey) {
    mergedHeaders.set('Idempotency-Key', idempotencyKey);
  }
  return apiClientInstance.request<T>(path, { ...rest, headers: mergedHeaders });
}
