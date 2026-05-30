/**
 * event-parser.ts の PBT-02 Round-trip プロパティ（Phase 1 Step 7.4 PBT 補強）。
 *
 * PBT-02: 任意の有効な StrandsStreamEvent を JSON encode → parseEventStream で
 *         decode したラウンドトリップで同一値が得られる。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/nfr-requirements/nfr-requirements.md NFR-PBT-DEBATE-02
 */

import * as fc from 'fast-check';
import { describe, expect, it } from 'vitest';

import { parseEventStream } from './event-parser';
import type { DebateAxis, EventType, StrandsStreamEvent } from './types';

const eventTypeArb: fc.Arbitrary<EventType> = fc.constantFrom(
  'token',
  'turn_complete',
  'session_complete',
  'error',
);

const axisArb: fc.Arbitrary<DebateAxis> = fc.constantFrom('FACT', 'PSYCHOLOGY', 'REWARD');

// 制御文字 / 改行を除外し、ASCII + 一部 Unicode を許可
const safeStringArb = fc
  .string({ minLength: 0, maxLength: 50 })
  .filter((s) => !/[\x00-\x1f\x7f-\x9f]/.test(s) && !s.includes('\n'));

const reasonArb = fc.constantFrom(
  'agreed',
  'refused',
  'graceful_timeout',
  'hard_timeout',
  'error',
  'auth.unauthenticated',
);

/** 有効な StrandsStreamEvent を生成する Arbitrary。 */
const eventArb: fc.Arbitrary<StrandsStreamEvent> = eventTypeArb.chain((type) => {
  if (type === 'token') {
    return fc.record({
      type: fc.constant<EventType>('token'),
      delta_text: safeStringArb,
    }) as fc.Arbitrary<StrandsStreamEvent>;
  }
  if (type === 'session_complete' || type === 'error') {
    return fc.record({
      type: fc.constant<EventType>(type),
      metadata: fc.record({ reason: reasonArb }),
    }) as fc.Arbitrary<StrandsStreamEvent>;
  }
  return fc.constant<StrandsStreamEvent>({ type });
});

/** AsyncIterable<Uint8Array> ヘルパー。 */
function toStream(jsonLines: readonly string[]): AsyncIterable<Uint8Array> {
  const encoder = new TextEncoder();
  return (async function* () {
    for (const line of jsonLines) {
      yield encoder.encode(line);
    }
  })();
}

describe('parseEventStream PBT-02 Round-trip', () => {
  it('任意の StrandsStreamEvent を JSON 化 → parse で同一値が得られる', async () => {
    await fc.assert(
      fc.asyncProperty(fc.array(eventArb, { minLength: 1, maxLength: 5 }), async (events) => {
        const lines = events.map((e) => `${JSON.stringify(e)}\n`);
        const stream = toStream(lines);
        const parsed: StrandsStreamEvent[] = [];
        for await (const evt of parseEventStream(stream)) {
          parsed.push(evt);
        }

        expect(parsed).toHaveLength(events.length);
        // delta_text に軸タグマーカーが偶然含まれている場合は metadata.axis が付与されるが、
        // 元の event には axis を入れていないため、その差分を許容する
        for (let i = 0; i < events.length; i++) {
          const original = events[i]!;
          const restored = parsed[i]!;
          expect(restored.type).toBe(original.type);
          expect(restored.delta_text).toBe(original.delta_text);
          if (original.metadata?.reason !== undefined) {
            expect(restored.metadata?.reason).toBe(original.metadata.reason);
          }
        }
      }),
      { numRuns: 50 },
    );
  });

  it('軸タグマーカーを含む token は metadata.axis が確実に抽出される', async () => {
    await fc.assert(
      fc.asyncProperty(axisArb, safeStringArb, async (axis, content) => {
        const event = {
          type: 'token' as const,
          delta_text: `[${axis}] ${content}`,
        };
        const stream = toStream([`${JSON.stringify(event)}\n`]);
        const parsed: StrandsStreamEvent[] = [];
        for await (const evt of parseEventStream(stream)) {
          parsed.push(evt);
        }

        expect(parsed).toHaveLength(1);
        expect(parsed[0]?.metadata?.axis).toBe(axis);
      }),
      { numRuns: 30 },
    );
  });
});
