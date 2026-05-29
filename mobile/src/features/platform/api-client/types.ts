/** ApiClient の型定義（LC-01 / PAT-PERF-01）。 */

/** リクエストの種別。タイムアウトポリシーを切り替える（NFR-PERF-01/02）。 */
export type RequestKind = 'rest' | 'stream';

/** タイムアウト設定（ミリ秒）。 */
export interface TimeoutPolicy {
  /** 接続タイムアウト。 */
  connectMs: number;
  /** 全体タイムアウト。null は無制限（SSE 用）。 */
  totalMs: number | null;
  /** アイドルタイムアウト（SSE のみ）。 */
  idleMs?: number;
}

/** リクエストポリシー。 */
export interface RequestPolicy {
  kind: RequestKind;
  timeout?: Partial<TimeoutPolicy>;
  /** GET 以外でも明示的にリトライを許可する場合（既定 false）。 */
  retry?: boolean;
}

/** 認証トークン供給（M-11 AuthModule のインターフェース。実体は Unit-2）。 */
export interface AuthTokenProvider {
  getAccessToken(): Promise<string | null>;
  refresh(): Promise<boolean>;
  onAuthExpired(): void;
}

/** ApiClient 設定。 */
export interface ApiClientConfig {
  baseUrl: string;
  auth: AuthTokenProvider;
  /** 相関 ID 生成器（既定は UUID v4）。テスト注入用。 */
  generateCorrelationId?: () => string;
  /** fetch 実装（テスト注入用）。 */
  fetchImpl?: typeof fetch;
}

/** 既定タイムアウト（NFR-PERF-01/02）。 */
export const DEFAULT_REST_TIMEOUT: TimeoutPolicy = { connectMs: 3_000, totalMs: 10_000 };
export const DEFAULT_STREAM_TIMEOUT: TimeoutPolicy = {
  connectMs: 3_000,
  totalMs: null,
  idleMs: 30_000,
};

/** リトライ設定（RETRY-01〜03）。 */
export const RETRY_BASE_MS = 300;
export const RETRY_MAX_ATTEMPTS = 2;
export const RETRYABLE_STATUS = new Set([429, 503]);
