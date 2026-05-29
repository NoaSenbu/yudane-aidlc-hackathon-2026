/**
 * M-12 ApiClient — interceptor チェーンを内包する REST/SSE クライアント（LC-01）。
 *
 * 順序: auth(JWT) → correlation(ID) → timeout(policy 別) → retry(GET のみ) →
 *       refresh(401 single-shot) → errorMap(Problem→DomainError)。
 * 設計: business-logic-model.md ALG-API/REFRESH/MAP / business-rules.md REQ・RETRY。
 */

import type { ProblemDetails } from '@yudane/schema';

import { DomainError, mapProblemToDomainError } from './domain-error';
import { backoffDelayMs, shouldRetry } from './retry-policy';
import {
  type ApiClientConfig,
  DEFAULT_REST_TIMEOUT,
  DEFAULT_STREAM_TIMEOUT,
  type RequestPolicy,
  RETRY_BASE_MS,
} from './types';

/** UUID v4 を生成する（相関 ID 用）。 */
function defaultCorrelationId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `cid-${Date.now()}-${Math.random()}`;
}

/** デフォルトの待機（テストで上書き可能なよう関数化）。 */
const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

export interface RequestOptions extends Omit<RequestInit, 'signal'> {
  policy?: RequestPolicy;
}

/** M-12 ApiClient。 */
export class ApiClient {
  private readonly config: Required<Pick<ApiClientConfig, 'baseUrl' | 'auth'>> &
    ApiClientConfig;
  private readonly fetchImpl: typeof fetch;
  private readonly genId: () => string;

  constructor(config: ApiClientConfig) {
    this.config = config;
    this.fetchImpl = config.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.genId = config.generateCorrelationId ?? defaultCorrelationId;
  }

  /**
   * REST リクエストを送る。2xx の JSON を返し、エラーは DomainError を throw する。
   *
   * @param path - パス（baseUrl からの相対）
   * @param options - fetch オプション + RequestPolicy
   * @returns レスポンス body（型 T）
   */
  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const method = (options.method ?? 'GET').toUpperCase();
    const correlationId = this.genId();
    const explicitRetry = options.policy?.retry ?? false;

    let didRefresh = false;
    let attempt = 0;

    for (;;) {
      let status: number | undefined;
      try {
        const res = await this.sendOnce(path, options, correlationId, method);
        status = res.status;

        if (res.ok) {
          return (await this.parseBody(res)) as T;
        }

        // 401: single-shot refresh（PAT-RESIL-02 / ALG-REFRESH）
        if (res.status === 401 && !didRefresh) {
          didRefresh = true;
          const ok = await this.config.auth.refresh();
          if (ok) {
            continue; // 同一 correlationId で再送
          }
          this.config.auth.onAuthExpired();
        }

        // リトライ判定（GET のみ、429/503）
        if (shouldRetry({ method, status: res.status, attempt, explicitRetry })) {
          await sleep(backoffDelayMs(attempt, RETRY_BASE_MS, 100));
          attempt += 1;
          continue;
        }

        throw await this.toDomainError(res, method);
      } catch (err) {
        if (err instanceof DomainError) {
          throw err;
        }
        // ネットワーク断
        if (shouldRetry({ method, status: undefined, attempt, explicitRetry })) {
          await sleep(backoffDelayMs(attempt, RETRY_BASE_MS, 100));
          attempt += 1;
          continue;
        }
        throw new DomainError({
          category: 'external-api',
          code: 'external-api.network',
          message: err instanceof Error ? err.message : 'network error',
          status: 0,
          retryable: false,
          userMessage: 'ちょっと混み合ってるみたい。あとでもう一度試してね',
        });
      }
    }
  }

  /** 1 回のリクエスト送信（auth + correlation + timeout interceptor を適用）。 */
  private async sendOnce(
    path: string,
    options: RequestOptions,
    correlationId: string,
    method: string,
  ): Promise<Response> {
    const token = await this.config.auth.getAccessToken();
    const headers = new Headers(options.headers);
    headers.set('X-Correlation-Id', correlationId);
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    if (!headers.has('Content-Type') && options.body) {
      headers.set('Content-Type', 'application/json');
    }

    const policy = options.policy ?? { kind: 'rest' };
    const timeout =
      policy.kind === 'stream'
        ? { ...DEFAULT_STREAM_TIMEOUT, ...policy.timeout }
        : { ...DEFAULT_REST_TIMEOUT, ...policy.timeout };

    const controller = new AbortController();
    const timer =
      timeout.totalMs !== null ? setTimeout(() => controller.abort(), timeout.totalMs) : null;

    try {
      return await this.fetchImpl(`${this.config.baseUrl}${path}`, {
        ...options,
        method,
        headers,
        signal: controller.signal,
      });
    } finally {
      if (timer) {
        clearTimeout(timer);
      }
    }
  }

  /** レスポンスを DomainError に変換する。 */
  private async toDomainError(res: Response, method: string): Promise<DomainError> {
    let problem: ProblemDetails | null = null;
    try {
      problem = (await res.clone().json()) as ProblemDetails;
    } catch {
      problem = null;
    }
    return mapProblemToDomainError(problem, res.status, method.toUpperCase() === 'GET');
  }

  /** 2xx body をパースする（204 は undefined）。 */
  private async parseBody(res: Response): Promise<unknown> {
    if (res.status === 204) {
      return undefined;
    }
    const text = await res.text();
    return text ? JSON.parse(text) : undefined;
  }
}
