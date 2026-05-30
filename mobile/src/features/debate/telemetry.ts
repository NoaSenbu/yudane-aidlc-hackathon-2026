/**
 * Unit-3 Debate Telemetry イベントカタログ（Phase 2 Step 8.2 Green）。
 *
 * M-13 Telemetry に Unit-3 専用 10 イベントを追加。Phase 2 では 8 イベントを発火配線、
 * 2 イベント（moderation_blocked / graceful_shutdown_initiated）は送信スキーマのみ整備、
 * 発火元は Phase 3（Bedrock Guardrails / Strands graceful shutdown 80s）で結線する。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 8
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6.2 EMF メトリクス
 */

import type {
  TelemetryEvent,
  TelemetryValue,
} from '../platform/telemetry/types';

/** Unit-3 Debate のイベント名カタログ（10 種、SSOT）。 */
export const DEBATE_TELEMETRY_EVENT_NAMES = [
  'debate.session_started',
  'debate.token_streamed',
  'debate.refused',
  'debate.agreed',
  'debate.session_complete',
  'debate.cooldown_triggered',
  'debate.affirmation_shown',
  'debate.moderation_blocked',
  'debate.graceful_shutdown_initiated',
  'debate.stress_estimated',
] as const;

export type DebateTelemetryEventName =
  (typeof DEBATE_TELEMETRY_EVENT_NAMES)[number];

/** イベント名集合（Telemetry.isKnownEvent 連携用）。 */
const _KNOWN_EVENT_NAMES_SET = new Set<string>(DEBATE_TELEMETRY_EVENT_NAMES);

/**
 * 既知の Debate イベント名か判定する純関数。
 *
 * @param name - イベント名。
 * @returns Unit-3 Debate のカタログに登録済みなら true。
 */
export function isKnownDebateTelemetryEvent(name: string): boolean {
  return _KNOWN_EVENT_NAMES_SET.has(name);
}

/** イベント別に許可される props キー（PII 混入防止、TEL-02）。 */
const _ALLOWED_PROPS_BY_EVENT: Readonly<
  Record<DebateTelemetryEventName, ReadonlySet<string>>
> = Object.freeze({
  'debate.session_started': new Set([
    'session_id',
    'asin',
    'trigger',
  ]),
  'debate.token_streamed': new Set(['session_id', 'axis']),
  'debate.refused': new Set([
    'session_id',
    'consecutive_refuses',
    'cooldown_triggered',
  ]),
  'debate.agreed': new Set(['session_id', 'asin', 'axis']),
  'debate.session_complete': new Set(['session_id', 'reason']),
  'debate.cooldown_triggered': new Set([
    'session_id',
    'cooldown_until',
  ]),
  'debate.affirmation_shown': new Set([
    'session_id',
    'asin',
    'service_record_id',
  ]),
  'debate.moderation_blocked': new Set([
    'session_id',
    'layer',
    'pattern_detected',
  ]),
  'debate.graceful_shutdown_initiated': new Set([
    'session_id',
    'elapsed_seconds',
  ]),
  'debate.stress_estimated': new Set(['session_id', 'level']),
});

/**
 * Debate イベントの props キー許可判定（純関数、PII 混入防止）。
 *
 * @param eventName - 対象イベント名。
 * @param propKey - props のキー名。
 * @returns 許可済みなら true。
 */
export function isAllowedDebateProp(
  eventName: string,
  propKey: string,
): boolean {
  if (!isKnownDebateTelemetryEvent(eventName)) {
    return false;
  }
  const allowed = _ALLOWED_PROPS_BY_EVENT[eventName as DebateTelemetryEventName];
  return allowed.has(propKey);
}

/** Telemetry track の便利ラッパー。**Phase 2 ではスキーマ整備のみ**、発火配線は store / view-model から呼ぶ。 */
export interface DebateTelemetryClient {
  trackSessionStarted(props: {
    session_id: string;
    asin: string;
    trigger: string;
  }): void;
  trackTokenStreamed(props: { session_id: string; axis?: string }): void;
  trackRefused(props: {
    session_id: string;
    consecutive_refuses: number;
    cooldown_triggered: boolean;
  }): void;
  trackAgreed(props: { session_id: string; asin: string; axis?: string }): void;
  trackSessionComplete(props: { session_id: string; reason: string }): void;
  trackCooldownTriggered(props: {
    session_id: string;
    cooldown_until: string;
  }): void;
  trackAffirmationShown(props: {
    session_id: string;
    asin: string;
    service_record_id: string;
  }): void;
  trackModerationBlocked(props: {
    session_id: string;
    layer: string;
    pattern_detected?: string;
  }): void;
  trackGracefulShutdownInitiated(props: {
    session_id: string;
    elapsed_seconds: number;
  }): void;
  trackStressEstimated(props: { session_id: string; level: string }): void;
}

/** バッキング track 関数を受け取って DebateTelemetryClient を作成するファクトリ。 */
export function createDebateTelemetryClient(
  track: (name: string, props?: Record<string, TelemetryValue>) => void,
): DebateTelemetryClient {
  return {
    trackSessionStarted: (p) => track('debate.session_started', p),
    trackTokenStreamed: (p) => track('debate.token_streamed', p),
    trackRefused: (p) => track('debate.refused', p),
    trackAgreed: (p) => track('debate.agreed', p),
    trackSessionComplete: (p) => track('debate.session_complete', p),
    trackCooldownTriggered: (p) => track('debate.cooldown_triggered', p),
    trackAffirmationShown: (p) => track('debate.affirmation_shown', p),
    trackModerationBlocked: (p) => track('debate.moderation_blocked', p),
    trackGracefulShutdownInitiated: (p) =>
      track('debate.graceful_shutdown_initiated', p),
    trackStressEstimated: (p) => track('debate.stress_estimated', p),
  };
}

/** TelemetryEvent シェイプの参照型（外部のテストで利用可能）。 */
export type DebateTelemetryEvent = TelemetryEvent & {
  name: DebateTelemetryEventName;
};
