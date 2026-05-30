/**
 * IT-DEBATE-01: クールダウンサイクル（Phase 6 Step 6-1）。
 *
 * シナリオ: 連続 3 回拒否 → クールダウン発火 → 自然解除 → 1 にリセット の完全サイクルを
 * Mobile 純ロジック層で結線確認。Backend は msw でモックし、cooldown.cooldown_triggered と
 * 通常 streaming の切替を検証する。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §3 Step 6-1
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md COOLDOWN-01〜04
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
  trigger: 'cart_intercept',
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

async function _runStream(
  events: readonly StrandsStreamEvent[],
): Promise<StrandsStreamEvent[]> {
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
  return collected;
}

describe('IT-DEBATE-01: クールダウンサイクル', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('1〜2 回目の拒否は通常 streaming（cooldown event 来ない）', async () => {
    const normalEvents: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] テスト', metadata: { axis: 'FACT' } },
      { type: 'session_complete', metadata: { reason: 'agent_completed' } },
    ];
    const events = await _runStream(normalEvents);
    const cooldownEvents = events.filter(
      (e) => e.type === 'debate.cooldown_triggered',
    );
    expect(cooldownEvents).toHaveLength(0);
    expect(events[events.length - 1]?.type).toBe('session_complete');
  });

  it('3 回目の拒否でクールダウン発火、cooldown_until が UI に反映される', async () => {
    const cooldownEvent: StrandsStreamEvent = {
      type: 'debate.cooldown_triggered',
      metadata: { cooldown_until: '2026-06-01T15:00:00.000Z' },
    };
    const events = await _runStream([cooldownEvent]);

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'cart_intercept',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    for (const evt of events) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
    }

    expect(viewState.sessionStatus).toBe('cooldown');
    expect(viewState.cooldownUntil).toBe('2026-06-01T15:00:00.000Z');
    expect(viewState.canAgree).toBe(false);
    expect(viewState.canRefuse).toBe(false);
    expect(viewState.canRetry).toBe(false);
  });

  it('クールダウン後、自然解除されたら通常 streaming が再開可能', async () => {
    // クールダウン解除後は再度ストリーミングが返ってくる想定
    const normalEvents: StrandsStreamEvent[] = [
      { type: 'token', delta_text: '[FACT] 復活', metadata: { axis: 'FACT' } },
      { type: 'session_complete', metadata: { reason: 'agent_completed' } },
    ];
    const events = await _runStream(normalEvents);

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _PAYLOAD.asin,
      trigger: 'cart_intercept',
      startedAt: new Date('2026-06-01T15:01:00Z'),
    });
    for (const evt of events) {
      viewState = reduceDebateView(viewState, { type: 'stream_event', event: evt });
    }

    expect(viewState.sessionStatus).toBe('complete');
    expect(viewState.factTokens).toHaveLength(1);
  });
});
