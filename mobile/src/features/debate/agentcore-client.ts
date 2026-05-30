/**
 * LC-D-09 Mobile AgentCore Client（Phase 1 Step 6.2 Green、Outside-In TDD）。
 *
 * Mobile から AgentCore Runtime を呼び出すラッパー。Phase 1 では HTTP fetch を直接使い、
 * Cognito JWT を `Authorization: Bearer` ヘッダで送る AgentCore Cognito Authorizer 方式
 * （infrastructure-design §1.1）。
 *
 * SSM 直接読みは行わず、EAS Build 時に注入された `EXPO_PUBLIC_*` 環境変数から
 * RuntimeEndpoint ARN を取得（4IDC-1 修正）。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md §5
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 6
 */

import type { DebateInvocationPayload, StrandsStreamEvent } from './types';

/**
 * DebateAgentCoreClient の依存。テストで差し替え可能。
 */
export interface DebateAgentCoreClientDeps {
  /** Runtime Endpoint ARN（EAS Build 時に EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN として注入）。 */
  readonly runtimeEndpointArn: string;
  /** AWS リージョン。 */
  readonly region: string;
  /** Cognito JWT 取得関数（Amplify Auth.fetchAuthSession() ラッパー、null で auth.unauthenticated）。 */
  readonly fetchJwt: () => Promise<string | null>;
  /** HTTP fetch 関数（テスト時はモック差し替え）。 */
  readonly fetch?: typeof fetch;
  /** AbortController（呼び出し側でキャンセル制御するときに使用）。 */
  readonly abortController?: AbortController;
}

/**
 * AgentCore Runtime InvokeAgentRuntime を呼び出すクライアント。
 *
 * 使用例:
 * ```typescript
 * const client = new DebateAgentCoreClient({
 *   runtimeEndpointArn: process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN ?? '',
 *   region: 'ap-northeast-1',
 *   fetchJwt: async () => (await Amplify.Auth.fetchAuthSession()).tokens?.idToken?.toString() ?? null,
 * });
 * for await (const chunk of client.invoke(payload)) {
 *   // chunk は Uint8Array（streaming raw bytes）または StrandsStreamEvent（error 時）
 * }
 * ```
 */
export class DebateAgentCoreClient {
  private readonly deps: DebateAgentCoreClientDeps;
  private readonly fetchFn: typeof fetch;

  constructor(deps: DebateAgentCoreClientDeps) {
    this.deps = deps;
    this.fetchFn = deps.fetch ?? globalThis.fetch;
  }

  /**
   * 論破セッションを起動して streaming chunk を非同期 iterate する。
   *
   * Phase 1 では SDK 不使用、HTTP fetch + JSON Lines streaming で簡易実装。
   * Phase 2 で `@aws-sdk/client-bedrock-agentcore` の `InvokeAgentRuntimeCommand` に置換予定。
   *
   * @param payload - Mobile 側 DTO（actor_id は **絶対に含めない**、SECURITY-08）。
   * @yields {Uint8Array | StrandsStreamEvent} streaming chunk（success）/ error event（failure）。
   */
  async *invoke(
    payload: DebateInvocationPayload,
  ): AsyncIterableIterator<Uint8Array | StrandsStreamEvent> {
    if (!this.deps.runtimeEndpointArn) {
      throw new Error(
        'EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN が未設定です。EAS Build 時に SSM から注入してください',
      );
    }

    const jwt = await this.deps.fetchJwt();
    if (jwt === null || jwt === '') {
      yield {
        type: 'error',
        metadata: { reason: 'auth.unauthenticated' },
      } satisfies StrandsStreamEvent;
      return;
    }

    // SECURITY-08: actor_id は payload から除外（JWT.sub から AgentCore Runtime が解決）
    const sanitizedPayload = sanitizePayload(payload);

    const url = this.buildInvokeUrl();
    const requestInit: RequestInit = {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${jwt}`,
        'Content-Type': 'application/json',
        Accept: 'application/x-ndjson',
      },
      body: JSON.stringify(sanitizedPayload),
      signal: this.deps.abortController?.signal,
    };

    // 1 回のみリトライ（ThrottlingException、PAT-D-COST-02）
    let response: Response;
    try {
      response = await this.fetchFn(url, requestInit);
      if (response.status === 429) {
        // ThrottlingException → 1 回のみリトライ
        response = await this.fetchFn(url, requestInit);
        if (response.status === 429) {
          yield {
            type: 'error',
            metadata: { reason: 'runtime.throttled' },
          } satisfies StrandsStreamEvent;
          return;
        }
      }
    } catch (err) {
      yield {
        type: 'error',
        metadata: { reason: errorReason(err) },
      } satisfies StrandsStreamEvent;
      return;
    }

    if (!response.ok) {
      yield {
        type: 'error',
        metadata: { reason: `runtime.http_${response.status}` },
      } satisfies StrandsStreamEvent;
      return;
    }

    if (response.body === null) {
      yield {
        type: 'error',
        metadata: { reason: 'runtime.empty_body' },
      } satisfies StrandsStreamEvent;
      return;
    }

    // streaming chunk を Uint8Array で yield（event-parser.ts が JSON 解釈）
    const reader = response.body.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  }

  /** AgentCore Runtime InvokeAgentRuntime のエンドポイント URL を組み立てる。 */
  private buildInvokeUrl(): string {
    // AgentCore Runtime endpoint: https://bedrock-agentcore.<region>.amazonaws.com/agent-runtimes/<runtime-id>/invoke
    // Phase 1 では runtime-endpoint-live-arn を URL に変換せず、ARN を `x-agentcore-target-arn`
    // 風のヘッダ経由で送る簡易実装。Phase 2 で SDK の InvokeAgentRuntimeCommand に置換時に正規化。
    return `https://bedrock-agentcore.${this.deps.region}.amazonaws.com/runtimes/${encodeURIComponent(this.deps.runtimeEndpointArn)}/invocations`;
  }
}

/** payload から actor_id を除外する純関数（SECURITY-08）。 */
function sanitizePayload(payload: DebateInvocationPayload): DebateInvocationPayload {
  const sanitized: Record<string, unknown> = { ...payload };
  // 攻撃者が型を欺いて actor_id 等を入れた場合に備えて、明示的に削除
  delete sanitized.actor_id;
  delete sanitized.actorId;
  delete sanitized.user_id;
  delete sanitized.userId;
  return sanitized as DebateInvocationPayload;
}

/** エラーオブジェクトから reason 文字列を抽出する。 */
function errorReason(err: unknown): string {
  if (err instanceof Error) {
    if (err.name === 'AbortError') {
      return 'runtime.aborted';
    }
    return `runtime.fetch_failed:${err.name}`;
  }
  return 'runtime.fetch_failed';
}
