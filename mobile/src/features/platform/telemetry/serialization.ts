/**
 * TelemetryEnvelope の serialize / deserialize（PBT-02 round-trip 対象、TEL-09）。
 */

import type { TelemetryEnvelope } from './types';

/** Envelope を JSON 文字列にする。 */
export function serializeEnvelope(envelope: TelemetryEnvelope): string {
  return JSON.stringify(envelope);
}

/** JSON 文字列から Envelope を復元する。 */
export function deserializeEnvelope(raw: string): TelemetryEnvelope {
  return JSON.parse(raw) as TelemetryEnvelope;
}
