/**
 * IT-DEBATE-03: モデレーション block シナリオ（Phase 6 Step 6-1）。
 *
 * シナリオ: NG-3 / NG-6 を含む応答 chunk が来たら `moderation_blocked` event が yield され、
 * UI が `moderation_blocked` 状態に遷移、CTA が全て不活性化される流れを検証する。
 * matched_text は metadata に含めず PII 流出を防ぐ（SECURITY-08）。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §3 Step 6-1
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md MOD-01〜03
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
  user_input: 'やっぱりいらない',
  asin: 'B01ABC1234',
  trigger: 'product_dwell',
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

describe('IT-DEBATE-03: モデレーション block', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('NG-6 検出で moderation_blocked event が yield され、UI 状態が遷移', async () => {
    const events: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] 序盤', metadata: { axis: 'FACT' } },
      {
        type: 'moderation_blocked',
        metadata: { pattern_id: 'NG-6', pattern_name: 'guilt_coercion' },
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

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'product_dwell',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });

    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
    }

    // UI が moderation_blocked に遷移
    expect(viewState.sessionStatus).toBe('moderation_blocked');
    expect(viewState.moderationPatternId).toBe('NG-6');
    // 全 CTA が不活性
    expect(viewState.canAgree).toBe(false);
    expect(viewState.canRefuse).toBe(false);
    expect(viewState.canRetry).toBe(false);
    // FACT token は moderation 前に表示されたので残っている
    expect(viewState.factTokens).toHaveLength(1);
  });

  it('NG-3 insult 検出も同様に moderation_blocked 状態へ遷移', async () => {
    const events: StrandsStreamEvent[] = [
      {
        type: 'moderation_blocked',
        metadata: { pattern_id: 'NG-3', pattern_name: 'insult' },
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

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'product_dwell',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
    }

    expect(viewState.sessionStatus).toBe('moderation_blocked');
    expect(viewState.moderationPatternId).toBe('NG-3');
  });

  it('moderation_blocked metadata に matched_text が含まれない（PII / NG 文言の Telemetry 流出防止）', async () => {
    const events: StrandsStreamEvent[] = [
      {
        type: 'moderation_blocked',
        metadata: { pattern_id: 'NG-6', pattern_name: 'guilt_coercion' },
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

    const moderationEvent = collected.find((e) => e.type === 'moderation_blocked');
    expect(moderationEvent).toBeDefined();
    // metadata に matched_text が含まれていない（PII 流出防止）
    const m = moderationEvent?.metadata as Record<string, unknown> | undefined;
    expect(m?.matched_text).toBeUndefined();
  });
});
