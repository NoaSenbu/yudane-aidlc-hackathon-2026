import { beforeEach, describe, expect, it, vi } from 'vitest';
import fc from 'fast-check';

import { deserializeEnvelope, serializeEnvelope } from './serialization';
import { Telemetry } from './telemetry';
import {
  OVERFLOW_STORE_KEY,
  type PersistentStore,
  type TelemetryEnvelope,
  type TelemetryTransport,
} from './types';

/** インメモリ PersistentStore。 */
function makeStore(): PersistentStore & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: vi.fn(async (k: string) => data.get(k) ?? null),
    setItem: vi.fn(async (k: string, v: string) => void data.set(k, v)),
    removeItem: vi.fn(async (k: string) => void data.delete(k)),
  };
}

const fixedNow = (): Date => new Date('2026-05-30T00:00:00Z');

describe('Telemetry.track / flush', () => {
  let store: ReturnType<typeof makeStore>;

  beforeEach(() => {
    store = makeStore();
  });

  it('未知イベントは no-op（TEL-01）', async () => {
    const transport: TelemetryTransport = { send: vi.fn().mockResolvedValue(undefined) };
    const t = new Telemetry({
      transport,
      store,
      isKnownEvent: (n) => n === 'screen_view',
      now: fixedNow,
    });
    t.track('evil_event');
    await t.flush();
    expect(transport.send).not.toHaveBeenCalled();
  });

  it('許可外 props はドロップする（TEL-02）', async () => {
    let captured: TelemetryEnvelope | undefined;
    const transport: TelemetryTransport = {
      send: vi.fn(async (e: TelemetryEnvelope) => void (captured = e)),
    };
    const t = new Telemetry({
      transport,
      store,
      isAllowedProp: (k) => k === 'screen',
      now: fixedNow,
    });
    t.track('screen_view', { screen: 'home', email: 'a@b.com' });
    await t.flush();
    expect(captured?.events[0]?.props).toEqual({ screen: 'home' });
  });

  it('batchMax 到達で自動 flush する（TEL-04）', async () => {
    const transport: TelemetryTransport = { send: vi.fn().mockResolvedValue(undefined) };
    const t = new Telemetry({ transport, store, batchMaxEvents: 2, now: fixedNow });
    t.track('screen_view');
    t.track('screen_view');
    // 自動 flush は非同期。マイクロタスクを待つ
    await Promise.resolve();
    await Promise.resolve();
    expect(transport.send).toHaveBeenCalled();
  });

  it('送信失敗時は退避キューへ保存する（TEL-05）', async () => {
    const transport: TelemetryTransport = {
      send: vi.fn().mockRejectedValue(new Error('network')),
    };
    const t = new Telemetry({ transport, store, now: fixedNow });
    t.track('screen_view');
    await t.flush();
    expect(store.data.get(OVERFLOW_STORE_KEY)).toBeTruthy();
  });

  it('退避分を次回 flush で再送し、成功後に退避をクリアする', async () => {
    store.data.set(
      OVERFLOW_STORE_KEY,
      JSON.stringify([{ name: 'screen_view', occurredAt: '2026-05-29T00:00:00Z' }]),
    );
    const transport: TelemetryTransport = { send: vi.fn().mockResolvedValue(undefined) };
    const t = new Telemetry({ transport, store, now: fixedNow });
    t.track('screen_view');
    await t.flush();
    expect((transport.send as ReturnType<typeof vi.fn>).mock.calls[0][0].events).toHaveLength(2);
    expect(store.data.has(OVERFLOW_STORE_KEY)).toBe(false);
  });

  it('退避上限を超えたら古い順に破棄する（TEL-05）', async () => {
    const transport: TelemetryTransport = {
      send: vi.fn().mockRejectedValue(new Error('network')),
    };
    const t = new Telemetry({ transport, store, overflowMaxEvents: 3, now: fixedNow });
    for (let i = 0; i < 5; i += 1) {
      t.track('screen_view', { idx: i });
    }
    await t.flush();
    const saved = JSON.parse(store.data.get(OVERFLOW_STORE_KEY) ?? '[]');
    expect(saved).toHaveLength(3);
    expect(saved[saved.length - 1].props.idx).toBe(4); // 最新が残る
  });
});

describe('serialize/deserialize（PBT-02 round-trip）', () => {
  const eventArb = fc.record({
    name: fc.constantFrom('screen_view', 'app_foreground', 'deeplink_open'),
    occurredAt: fc.date().map((d) => d.toISOString()),
    props: fc.option(
      fc.dictionary(
        fc.string(),
        fc.oneof(fc.string(), fc.integer(), fc.boolean()),
      ),
      { nil: undefined },
    ),
  });

  const envelopeArb: fc.Arbitrary<TelemetryEnvelope> = fc.record({
    events: fc.array(eventArb, { maxLength: 20 }),
    clientSentAt: fc.date().map((d) => d.toISOString()),
    schemaVersion: fc.constant('1.0.0'),
  });

  it('serialize → deserialize で元の Envelope に一致する', () => {
    fc.assert(
      fc.property(envelopeArb, (env) => {
        const round = deserializeEnvelope(serializeEnvelope(env));
        return JSON.stringify(round) === JSON.stringify(env);
      }),
      { seed: 20260529 },
    );
  });
});
