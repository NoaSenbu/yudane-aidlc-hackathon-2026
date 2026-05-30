/**
 * E2E-01 シナリオ: Cart Intercept → 論破セッション開始 → 翻意 → Amazon 遷移（Phase 2 Step 9.1 / 9.2）。
 *
 * Mobile 側純ロジックの End-to-End 統合テスト。`agentcore-client.ts` + `event-parser.ts` +
 * `debate-store` + `debate-view-model` + `telemetry` をすべて結線して動作確認。
 * Backend は msw でモック（Strands Agent native event 形式を返すスクリプト）。
 *
 * 参照: aidlc-docs/inception/user-stories/stories.md US-01-01
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DebateAgentCoreClient } from '../../features/debate/agentcore-client';
import { parseEventStream } from '../../features/debate/event-parser';
import {
  buildInitialDebateView,
  reduceDebateView,
} from '../../features/debate/screens/debate-view-model';
import { buildAffirmViewModel } from '../../features/debate/screens/affirm-view-model';
import { createDebateTelemetryClient } from '../../features/debate/telemetry';
import type {
  DebateInvocationPayload,
  StrandsStreamEvent,
} from '../../features/debate/types';

const _SAMPLE_PAYLOAD: DebateInvocationPayload = {
  action: 'start_session',
  user_input: 'でも欲しい',
  asin: 'B01ABC1234',
  trigger: 'cart_intercept',
};

/** Strands Agent 風の NDJSON チャンク列を生成。 */
function _strandsResponse(events: readonly StrandsStreamEvent[]): Response {
  const ndjson = events.map((e) => `${JSON.stringify(e)}\n`).join('');
  return new Response(
    new ReadableStream({
      async start(controller) {
        controller.enqueue(new TextEncoder().encode(ndjson));
        controller.close();
      },
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/x-ndjson' },
    },
  );
}

describe('E2E-01: Cart Intercept → 論破 → 翻意 → Amazon 遷移', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('全段が結線されて翻意 → AffirmViewModel まで到達する', async () => {
    // === Mock Backend: Strands Agent native event の連続を返す ===
    const mockBackendEvents: StrandsStreamEvent[] = [
      {
        type: 'token',
        delta_text: '[FACT] 時給換算で 11 時間分じゃないですか?',
        metadata: { axis: 'FACT' },
      },
      {
        type: 'token',
        delta_text: '[PSYCHOLOGY] 結局買って使ってるじゃないですか',
        metadata: { axis: 'PSYCHOLOGY' },
      },
      {
        type: 'session_complete',
        metadata: { reason: 'agent_completed' },
      },
    ];

    const fetchMock = vi.fn(async () => _strandsResponse(mockBackendEvents));

    const client = new DebateAgentCoreClient({
      runtimeEndpointArn:
        'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
      region: 'ap-northeast-1',
      fetchJwt: async () => 'dummy-jwt',
      fetch: fetchMock as unknown as typeof fetch,
    });

    // === ViewModel 駆動 ===
    let viewState = buildInitialDebateView();
    const startedAt = new Date('2026-06-01T12:00:00Z');
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _SAMPLE_PAYLOAD.asin,
      trigger: 'cart_intercept',
      startedAt,
    });

    // === Telemetry mock ===
    const telemetryTrack = vi.fn();
    const telemetry = createDebateTelemetryClient(telemetryTrack);
    telemetry.trackSessionStarted({
      session_id: 'sess-e2e-01',
      asin: _SAMPLE_PAYLOAD.asin,
      trigger: 'cart_intercept',
    });

    // === client.invoke() → event-parser → reduceDebateView の結線 ===
    const collectedEvents: StrandsStreamEvent[] = [];

    // 1. agentcore-client から Uint8Array stream を取得
    const rawStream = client.invoke(_SAMPLE_PAYLOAD);

    // 2. Uint8Array のみ抽出（StrandsStreamEvent 型の error は除外）
    async function* uint8ArrayOnly(): AsyncIterable<Uint8Array> {
      for await (const chunk of rawStream) {
        if (chunk instanceof Uint8Array) {
          yield chunk;
        }
      }
    }

    // 3. event-parser で StrandsStreamEvent に変換
    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      collectedEvents.push(evt);
      viewState = reduceDebateView(viewState, {
        type: 'stream_event',
        event: evt,
      });
      if (evt.type === 'token') {
        telemetry.trackTokenStreamed({
          session_id: 'sess-e2e-01',
          axis: evt.metadata?.axis,
        });
      }
    }

    // === 期待結果: 軸別に振り分けされ、sessionStatus=complete に到達 ===
    expect(collectedEvents).toHaveLength(3);
    expect(viewState.factTokens).toHaveLength(1);
    expect(viewState.factTokens[0]).toContain('[FACT]');
    expect(viewState.psychologyTokens).toHaveLength(1);
    expect(viewState.psychologyTokens[0]).toContain('[PSYCHOLOGY]');
    expect(viewState.sessionStatus).toBe('complete');
    expect(viewState.completionReason).toBe('agent_completed');
    // session_complete 時点では agree CTA は不活性
    expect(viewState.canAgree).toBe(false);

    // === 翻意 → Telemetry agreed + AffirmViewModel 構築 ===
    telemetry.trackAgreed({
      session_id: 'sess-e2e-01',
      asin: _SAMPLE_PAYLOAD.asin,
      axis: 'PSYCHOLOGY',
    });
    telemetry.trackSessionComplete({
      session_id: 'sess-e2e-01',
      reason: 'agreed',
    });

    const affirmVm = buildAffirmViewModel({
      asin: _SAMPLE_PAYLOAD.asin,
      sessionId: 'sess-e2e-01',
      now: () => new Date('2026-06-01T12:01:30Z'),
      serviceRecordIdGenerator: () => '#503-2890471',
    });
    telemetry.trackAffirmationShown({
      session_id: 'sess-e2e-01',
      asin: _SAMPLE_PAYLOAD.asin,
      service_record_id: affirmVm.serviceRecordId,
    });

    // === 期待結果: AffirmViewModel が Direction D D-3 固定文字列で返る ===
    expect(affirmVm.headlineText).toBe('はい、論破完了。');
    expect(affirmVm.acceptedPillText).toBe('ACCEPTED · #503-2890471');

    // Telemetry が 4 回呼ばれた（session_started / token_streamed × 2 / agreed / session_complete / affirmation_shown）
    expect(telemetryTrack).toHaveBeenCalledWith(
      'debate.session_started',
      expect.any(Object),
    );
    expect(telemetryTrack).toHaveBeenCalledWith(
      'debate.agreed',
      expect.any(Object),
    );
    expect(telemetryTrack).toHaveBeenCalledWith(
      'debate.affirmation_shown',
      expect.any(Object),
    );
  });

  it('クールダウン中はカート介入 → cooldown_triggered → AffirmViewModel に到達しない', async () => {
    const cooldownEvent: StrandsStreamEvent = {
      type: 'debate.cooldown_triggered',
      metadata: { cooldown_until: '2026-06-01T15:00:00.000Z' },
    };
    const fetchMock = vi.fn(async () => _strandsResponse([cooldownEvent]));

    const client = new DebateAgentCoreClient({
      runtimeEndpointArn:
        'arn:aws:bedrock-agentcore:ap-northeast-1:000000000000:runtime/yudane_debate_dev/runtime-endpoint/live',
      region: 'ap-northeast-1',
      fetchJwt: async () => 'dummy-jwt',
      fetch: fetchMock as unknown as typeof fetch,
    });

    let viewState = buildInitialDebateView();
    viewState = reduceDebateView(viewState, {
      type: 'session_started',
      asin: _SAMPLE_PAYLOAD.asin,
      trigger: 'cart_intercept',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });

    async function* uint8ArrayOnly(): AsyncIterable<Uint8Array> {
      for await (const chunk of client.invoke(_SAMPLE_PAYLOAD)) {
        if (chunk instanceof Uint8Array) {
          yield chunk;
        }
      }
    }

    for await (const evt of parseEventStream(uint8ArrayOnly())) {
      viewState = reduceDebateView(viewState, {
        type: 'stream_event',
        event: evt,
      });
    }

    expect(viewState.sessionStatus).toBe('cooldown');
    expect(viewState.cooldownUntil).toBe('2026-06-01T15:00:00.000Z');
    expect(viewState.canAgree).toBe(false);
    expect(viewState.canRefuse).toBe(false);
  });
});
