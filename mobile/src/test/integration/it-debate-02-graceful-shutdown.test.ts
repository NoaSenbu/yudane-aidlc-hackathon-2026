/**
 * IT-DEBATE-02: graceful shutdown シナリオ（Phase 6 Step 6-1）。
 *
 * シナリオ: 80 秒経過時点で `graceful_shutdown_initiated` event が送信され、
 * サマリ生成 → session_complete reason='graceful_timeout' で正常終了する流れを
 * Mobile 純ロジック層で結線確認する。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §3 Step 6-1
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md DEBATE-08
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DebateAgentCoreClient } from '../../features/debate/agentcore-client';
import { parseEventStream } from '../../features/debate/event-parser';
import {
  buildInitialDebateView,
  reduceDebateView,
} from '../../features/debate/screens/debate-view-model';
import type {
  DebateInvocationPayload,
  StrandsStreamEvent,
} from '../../features/debate/types';

const _PAYLOAD: DebateInvocationPayload = {
  action: 'start_session',
  user_input: 'やっぱり迷う',
  asin: 'B01ABC1234',
  trigger: 'reel_skip',
};

function _strandsResponse(events: readonly StrandsStreamEvent[]): Response {
  const ndjson = events.map((e) => `${JSON.stringify(e)}\n`).join('');
  return new Response(
    new ReadableStream({
      async start(controller) {
        controller.enqueue(new TextEncoder().encode(ndjson));
        controller.close();
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/x-ndjson' } },
  );
}

describe('IT-DEBATE-02: graceful shutdown 80s', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('80 秒経過で graceful_shutdown_initiated event が yield される', async () => {
    const events: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] 序盤', metadata: { axis: 'FACT' } },
      {
        type: 'graceful_shutdown_initiated',
        metadata: { elapsed_seconds: 80 },
      },
    ];

    const fetchMock = vi.fn(async () => _strandsResponse(events));
    const client = new DebateAgentCoreClient({
      runtimeEndpointArn:
        'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
      region: 'ap-northeast-1',
      fetchJwt: async () => 'dummy-jwt',
      fetch: fetchMock as unknown as typeof fetch,
    });

    async function* uint8ArrayOnly(): AsyncIterable<Uint8Array> {
      for await (const chunk of client.invoke(_PAYLOAD)) {
        if (chunk instanceof Uint8Array) {
          yield chunk;
        }
      }
    }

    const collected: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      collected.push(evt);
    }

    const gracefulEvents = collected.filter(
      (e) => e.type === 'graceful_shutdown_initiated',
    );
    expect(gracefulEvents).toHaveLength(1);
    expect(gracefulEvents[0]?.metadata?.elapsed_seconds).toBe(80);
  });

  it('graceful_shutdown_initiated → session_complete reason=graceful_timeout が UI で graceful_shutting_down → complete に遷移', async () => {
    const events: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] テスト', metadata: { axis: 'FACT' } },
      {
        type: 'graceful_shutdown_initiated',
        metadata: { elapsed_seconds: 80 },
      },
      { type: 'session_complete', metadata: { reason: 'graceful_timeout' } },
    ];

    const fetchMock = vi.fn(async () => _strandsResponse(events));
    const client = new DebateAgentCoreClient({
      runtimeEndpointArn:
        'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
      region: 'ap-northeast-1',
      fetchJwt: async () => 'dummy-jwt',
      fetch: fetchMock as unknown as typeof fetch,
    });

    async function* uint8ArrayOnly(): AsyncIterable<Uint8Array> {
      for await (const chunk of client.invoke(_PAYLOAD)) {
        if (chunk instanceof Uint8Array) {
          yield chunk;
        }
      }
    }

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });

    const seenStatuses: string[] = [viewState.sessionStatus];
    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
      seenStatuses.push(viewState.sessionStatus);
    }

    // streaming → graceful_shutting_down → complete の遷移を辿った
    expect(seenStatuses).toContain('graceful_shutting_down');
    expect(viewState.sessionStatus).toBe('complete');
    expect(viewState.completionReason).toBe('graceful_timeout');
    expect(viewState.gracefulShutdownElapsedSeconds).toBe(80);
  });

  it('hard_timeout で session_complete reason=hard_timeout が UI に反映される', async () => {
    const events: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] 90 秒到達', metadata: { axis: 'FACT' } },
      { type: 'session_complete', metadata: { reason: 'hard_timeout' } },
    ];

    const fetchMock = vi.fn(async () => _strandsResponse(events));
    const client = new DebateAgentCoreClient({
      runtimeEndpointArn:
        'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
      region: 'ap-northeast-1',
      fetchJwt: async () => 'dummy-jwt',
      fetch: fetchMock as unknown as typeof fetch,
    });

    async function* uint8ArrayOnly(): AsyncIterable<Uint8Array> {
      for await (const chunk of client.invoke(_PAYLOAD)) {
        if (chunk instanceof Uint8Array) {
          yield chunk;
        }
      }
    }

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
    }

    expect(viewState.sessionStatus).toBe('complete');
    expect(viewState.completionReason).toBe('hard_timeout');
  });
});
