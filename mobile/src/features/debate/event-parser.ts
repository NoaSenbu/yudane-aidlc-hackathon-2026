/**
 * LC-D-10 Mobile Event Parser（Phase 1 Step 7.2 Green、Outside-In TDD）。
 *
 * Strands Agent の streaming chunk（NDJSON: 1 行 1 JSON）を最小 4 種 EventType に変換する。
 * `delta_text` 内の `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` セクションマーカーを
 * `metadata.axis` に抽出（Direction D の論破画面ラベルへの 1:1 マッピング）。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §3.1 / §3.2
 * 参照: aidlc-docs/construction/design-system/direction-d-design-system.md
 */

import type { DebateAxis, EventType, StrandsStreamEvent } from './types';

const VALID_EVENT_TYPES: ReadonlySet<EventType> = new Set([
  'token',
  'turn_complete',
  'session_complete',
  'error',
  'debate.cooldown_triggered',
  'moderation_blocked',
  'graceful_shutdown_initiated',
]);

/** 軸タグマーカー（大文字のみ受理、ガードレール仕様）。 */
const AXIS_MARKER_REGEX = /\[(FACT|PSYCHOLOGY|REWARD)\]/;

/**
 * 文字列から最初の軸タグマーカーを抽出する。
 *
 * @param text - delta_text 等のチャンクテキスト。
 * @returns 軸種別（'FACT' | 'PSYCHOLOGY' | 'REWARD'）、見つからなければ undefined。
 */
export function extractAxis(text: string): DebateAxis | undefined {
  const match = AXIS_MARKER_REGEX.exec(text);
  if (match === null || match[1] === undefined) {
    return undefined;
  }
  return match[1] as DebateAxis;
}

/**
 * Strands streaming chunk（AsyncIterable<Uint8Array>）を StrandsStreamEvent の AsyncIterable に変換する。
 *
 * NDJSON 形式（改行区切り JSON）を前提とし、chunk の境界が JSON 構造途中に来てもバッファリングで
 * 復元する。不正な JSON は `error event with reason='parser.invalid_json'` で yield して継続不可
 * （fail-safe）。
 *
 * @param stream - HTTP レスポンスの ReadableStream を AsyncIterable に変換したもの。
 * @yields {StrandsStreamEvent} parsed events。
 */
export async function* parseEventStream(
  stream: AsyncIterable<Uint8Array>,
): AsyncIterableIterator<StrandsStreamEvent> {
  const decoder = new TextDecoder();
  let buffer = '';

  for await (const chunk of stream) {
    buffer += decoder.decode(chunk, { stream: true });

    let newlineIdx = buffer.indexOf('\n');
    while (newlineIdx >= 0) {
      const line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);
      newlineIdx = buffer.indexOf('\n');
      if (line === '') {
        continue;
      }
      const event = parseLine(line);
      if (event !== undefined) {
        yield event;
      }
    }
  }

  // 残りのバッファを処理（最終 chunk が改行で終わっていない場合）
  buffer += decoder.decode();
  const trailing = buffer.trim();
  if (trailing !== '') {
    const event = parseLine(trailing);
    if (event !== undefined) {
      yield event;
    }
  }
}

/** 1 行の JSON を StrandsStreamEvent に parse する。失敗時は error event を返す。 */
function parseLine(line: string): StrandsStreamEvent | undefined {
  let raw: unknown;
  try {
    raw = JSON.parse(line);
  } catch {
    return {
      type: 'error',
      metadata: { reason: 'parser.invalid_json' },
    };
  }

  if (typeof raw !== 'object' || raw === null) {
    return {
      type: 'error',
      metadata: { reason: 'parser.not_object' },
    };
  }

  const obj = raw as Record<string, unknown>;
  const type = obj.type;
  if (typeof type !== 'string' || !VALID_EVENT_TYPES.has(type as EventType)) {
    return {
      type: 'error',
      metadata: { reason: 'parser.unknown_type' },
    };
  }

  const event: {
    type: EventType;
    delta_text?: string;
    metadata?: {
      reason?: string;
      axis?: DebateAxis;
      cooldown_until?: string;
      pattern_id?: string;
      pattern_name?: string;
      elapsed_seconds?: number;
    };
  } = { type: type as EventType };

  if (typeof obj.delta_text === 'string') {
    event.delta_text = obj.delta_text;
  }

  // metadata
  const metadata = obj.metadata;
  if (typeof metadata === 'object' && metadata !== null) {
    const m = metadata as Record<string, unknown>;
    const eventMetadata: {
      reason?: string;
      axis?: DebateAxis;
      cooldown_until?: string;
      pattern_id?: string;
      pattern_name?: string;
      elapsed_seconds?: number;
    } = {};
    if (typeof m.reason === 'string') {
      eventMetadata.reason = m.reason;
    }
    if (typeof m.cooldown_until === 'string') {
      eventMetadata.cooldown_until = m.cooldown_until;
    }
    if (typeof m.pattern_id === 'string') {
      eventMetadata.pattern_id = m.pattern_id;
    }
    if (typeof m.pattern_name === 'string') {
      eventMetadata.pattern_name = m.pattern_name;
    }
    if (typeof m.elapsed_seconds === 'number') {
      eventMetadata.elapsed_seconds = m.elapsed_seconds;
    }
    if (Object.keys(eventMetadata).length > 0) {
      event.metadata = eventMetadata;
    }
  }

  // 軸タグ抽出（delta_text に [FACT] / [PSYCHOLOGY] / [REWARD] が含まれていれば metadata.axis）
  if (event.delta_text !== undefined) {
    const axis = extractAxis(event.delta_text);
    if (axis !== undefined) {
      event.metadata = { ...(event.metadata ?? {}), axis };
    }
  }

  return event satisfies StrandsStreamEvent;
}
