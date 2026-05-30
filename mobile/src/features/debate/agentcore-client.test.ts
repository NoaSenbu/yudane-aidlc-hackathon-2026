/**
 * DebateAgentCoreClient のテスト（Phase 1 Step 6.1 Red、Outside-In TDD）。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 6
 * 参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md §5
 *
 * 設計方針:
 *   - SSM 直接読みは行わず、EAS Build 時に注入された `EXPO_PUBLIC_*` 環境変数から
 *     RuntimeEndpoint ARN / Region を取得する（4IDC-1 修正）。
 *   - Cognito JWT は Amplify Auth.fetchAuthSession() で取得（モックで差し替え可能）。
 *   - HTTP fetch は依存注入で差し替え可能、本番では BedrockAgentCoreRuntime API を直接呼ぶ。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  DebateAgentCoreClient,
  type DebateAgentCoreClientDeps,
} from './agentcore-client';
import type { DebateInvocationPayload } from './types';

/** テスト用のヘルパー: 環境変数 + Auth + fetch モックを含む依存セット。 */
function buildMockDeps(
  overrides: Partial<DebateAgentCoreClientDeps> = {},
): DebateAgentCoreClientDeps {
  return {
    runtimeEndpointArn:
      'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
    region: 'ap-northeast-1',
    fetchJwt: vi.fn(async () => 'fake-jwt-token'),
    fetch: vi.fn() as unknown as typeof fetch,
    ...overrides,
  };
}

const samplePayload: DebateInvocationPayload = {
  action: 'start_session',
  user_input: 'でも欲しい',
  asin: 'B01ABC1234',
  trigger: 'reel_skip',
};

describe('DebateAgentCoreClient', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('configuration', () => {
    it('runtimeEndpointArn が空文字なら invoke で error を投げる', async () => {
      const deps = buildMockDeps({ runtimeEndpointArn: '' });
      const client = new DebateAgentCoreClient(deps);

      await expect(async () => {
        for await (const _ of client.invoke(samplePayload)) {
          /* drain */
        }
      }).rejects.toThrow(/EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN/);
    });
  });

  describe('JWT auth', () => {
    it('fetchJwt() で JWT を取得し Authorization ヘッダに設定する', async () => {
      const fetchJwt = vi.fn(async () => 'real-jwt-token');
      const fetchFn = vi.fn(async () => mockStreamingResponse(['{"type":"token","delta_text":"hi"}']));
      const deps = buildMockDeps({ fetchJwt, fetch: fetchFn as unknown as typeof fetch });
      const client = new DebateAgentCoreClient(deps);

      for await (const _ of client.invoke(samplePayload)) {
        /* drain */
      }

      expect(fetchJwt).toHaveBeenCalled();
      expect(fetchFn).toHaveBeenCalled();
      const callArgs = fetchFn.mock.calls[0];
      expect(callArgs).toBeDefined();
      const init = callArgs?.[1] as RequestInit;
      expect(init.headers).toMatchObject({
        Authorization: 'Bearer real-jwt-token',
      });
    });

    it('JWT 取得失敗で auth.unauthenticated エラーを yield する', async () => {
      const fetchJwt = vi.fn(async () => null);
      const deps = buildMockDeps({ fetchJwt });
      const client = new DebateAgentCoreClient(deps);

      const events: unknown[] = [];
      for await (const evt of client.invoke(samplePayload)) {
        events.push(evt);
      }

      expect(events).toEqual([
        expect.objectContaining({
          type: 'error',
          metadata: expect.objectContaining({ reason: 'auth.unauthenticated' }),
        }),
      ]);
    });
  });

  describe('payload', () => {
    it('actor_id は payload から除外する（SECURITY-08）', async () => {
      const fetchFn = vi.fn(async () => mockStreamingResponse(['{"type":"session_complete"}']));
      const deps = buildMockDeps({ fetch: fetchFn as unknown as typeof fetch });
      const client = new DebateAgentCoreClient(deps);

      const payloadWithActorId = {
        ...samplePayload,
        actor_id: 'attacker-spoofed',
      } as DebateInvocationPayload;

      for await (const _ of client.invoke(payloadWithActorId)) {
        /* drain */
      }

      const callArgs = fetchFn.mock.calls[0];
      expect(callArgs).toBeDefined();
      const init = callArgs?.[1] as RequestInit;
      const body = JSON.parse((init.body as string) ?? '{}');
      // actor_id は除外されている（SECURITY-08）
      expect(body.actor_id).toBeUndefined();
      expect(body.user_input).toBe('でも欲しい');
    });
  });

  describe('streaming', () => {
    it('chunk を順に Uint8Array で yield する', async () => {
      const chunks = [
        '{"type":"token","delta_text":"こ"}\n',
        '{"type":"token","delta_text":"んにちは"}\n',
        '{"type":"session_complete"}\n',
      ];
      const fetchFn = vi.fn(async () => mockStreamingResponse(chunks));
      const deps = buildMockDeps({ fetch: fetchFn as unknown as typeof fetch });
      const client = new DebateAgentCoreClient(deps);

      const collected: Uint8Array[] = [];
      for await (const chunk of client.invoke(samplePayload)) {
        if (chunk instanceof Uint8Array) {
          collected.push(chunk);
        }
      }

      expect(collected).toHaveLength(3);
    });
  });

  describe('retry', () => {
    it('ThrottlingException で 1 回のみリトライする（PAT-D-COST-02）', async () => {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce(mockErrorResponse(429, 'ThrottlingException'))
        .mockResolvedValueOnce(mockStreamingResponse(['{"type":"session_complete"}']));
      const deps = buildMockDeps({ fetch: fetchFn as unknown as typeof fetch });
      const client = new DebateAgentCoreClient(deps);

      const events: unknown[] = [];
      for await (const evt of client.invoke(samplePayload)) {
        events.push(evt);
      }

      expect(fetchFn).toHaveBeenCalledTimes(2);
      // 2 回目で session_complete chunk が送られる
      expect(events.length).toBeGreaterThan(0);
    });

    it('2 回目失敗で error event を yield する', async () => {
      const fetchFn = vi
        .fn()
        .mockResolvedValueOnce(mockErrorResponse(429, 'ThrottlingException'))
        .mockResolvedValueOnce(mockErrorResponse(429, 'ThrottlingException'));
      const deps = buildMockDeps({ fetch: fetchFn as unknown as typeof fetch });
      const client = new DebateAgentCoreClient(deps);

      const events: unknown[] = [];
      for await (const evt of client.invoke(samplePayload)) {
        events.push(evt);
      }

      expect(fetchFn).toHaveBeenCalledTimes(2);
      expect(events).toEqual([
        expect.objectContaining({
          type: 'error',
          metadata: expect.objectContaining({ reason: 'runtime.throttled' }),
        }),
      ]);
    });
  });
});

// =====================================================================
// helpers
// =====================================================================

/** ReadableStream<Uint8Array> を含む擬似 Response を返す。 */
function mockStreamingResponse(chunks: readonly string[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const encoder = new TextEncoder();
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'application/x-ndjson' },
  });
}

/** エラー Response を返す。 */
function mockErrorResponse(status: number, errorCode: string): Response {
  return new Response(JSON.stringify({ __type: errorCode }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
