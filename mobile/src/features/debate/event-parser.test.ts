/**
 * event-parser.ts のテスト（Phase 1 Step 7.1 Red、Outside-In TDD）。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 7
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §3.1
 */

import { describe, expect, it } from 'vitest';

import { extractAxis, parseEventStream } from './event-parser';
import type { StrandsStreamEvent } from './types';

/** 文字列配列を AsyncIterable<Uint8Array> に変換するヘルパー。 */
function toStream(chunks: readonly string[]): AsyncIterable<Uint8Array> {
  const encoder = new TextEncoder();
  return (async function* () {
    for (const c of chunks) {
      yield encoder.encode(c);
    }
  })();
}

describe('parseEventStream', () => {
  it('token chunk を EventType=token / delta_text 付きで返す', async () => {
    const stream = toStream(['{"type":"token","delta_text":"hello"}\n']);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events).toEqual([
      expect.objectContaining({ type: 'token', delta_text: 'hello' }),
    ]);
  });

  it('turn_complete を返す', async () => {
    const stream = toStream(['{"type":"turn_complete"}\n']);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events).toEqual([expect.objectContaining({ type: 'turn_complete' })]);
  });

  it('session_complete に reason を含む', async () => {
    const stream = toStream([
      '{"type":"session_complete","metadata":{"reason":"agreed"}}\n',
    ]);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events[0]).toMatchObject({
      type: 'session_complete',
      metadata: { reason: 'agreed' },
    });
  });

  it('error event を返す', async () => {
    const stream = toStream([
      '{"type":"error","metadata":{"reason":"auth.unauthenticated"}}\n',
    ]);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events[0]).toMatchObject({
      type: 'error',
      metadata: { reason: 'auth.unauthenticated' },
    });
  });

  it('不正な JSON で error event を yield する（fail-safe）', async () => {
    const stream = toStream(['not a json\n']);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events).toEqual([
      expect.objectContaining({
        type: 'error',
        metadata: expect.objectContaining({ reason: 'parser.invalid_json' }),
      }),
    ]);
  });

  it('複数 chunk を順に yield する', async () => {
    const stream = toStream([
      '{"type":"token","delta_text":"こ"}\n',
      '{"type":"token","delta_text":"ん"}\n',
      '{"type":"turn_complete"}\n',
      '{"type":"session_complete"}\n',
    ]);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events).toHaveLength(4);
    expect(events[0]?.delta_text).toBe('こ');
    expect(events[1]?.delta_text).toBe('ん');
    expect(events[2]?.type).toBe('turn_complete');
    expect(events[3]?.type).toBe('session_complete');
  });

  it('chunk が改行で区切られていない場合（バッファリング）', async () => {
    // 1 つ目の chunk が途中で切れる
    const stream = toStream([
      '{"type":"toke',
      'n","delta_text":"hi"}\n',
      '{"type":"session_complete"}\n',
    ]);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ type: 'token', delta_text: 'hi' });
  });
});

describe('extractAxis', () => {
  it('[FACT] マーカーを FACT 軸として抽出する', () => {
    expect(extractAxis('[FACT] これはデータです')).toBe('FACT');
  });

  it('[PSYCHOLOGY] マーカーを PSYCHOLOGY 軸として抽出する', () => {
    expect(extractAxis('[PSYCHOLOGY] あなたの心理は')).toBe('PSYCHOLOGY');
  });

  it('[REWARD] マーカーを REWARD 軸として抽出する', () => {
    expect(extractAxis('[REWARD] 今日のご褒美に')).toBe('REWARD');
  });

  it('マーカーなしで undefined を返す', () => {
    expect(extractAxis('普通のテキスト')).toBeUndefined();
  });

  it('複数マーカーがあっても最初の軸だけを返す', () => {
    expect(extractAxis('[FACT] データ [REWARD] ご褒美')).toBe('FACT');
  });

  it('マーカーの大文字小文字を区別する（ガードレール仕様）', () => {
    // 仕様: 大文字 [FACT] のみ受理、[fact] は無視
    expect(extractAxis('[fact] テスト')).toBeUndefined();
  });
});

describe('parseEventStream + extractAxis 統合', () => {
  it('token の delta_text に [FACT] マーカーがあれば metadata.axis に付与する', async () => {
    const stream = toStream([
      '{"type":"token","delta_text":"[FACT] 時給換算で"}\n',
    ]);
    const events: StrandsStreamEvent[] = [];
    for await (const evt of parseEventStream(stream)) {
      events.push(evt);
    }
    expect(events[0]).toMatchObject({
      type: 'token',
      metadata: { axis: 'FACT' },
    });
  });
});
