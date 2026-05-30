/**
 * Unit-3 Debate Telemetry のテスト（Phase 2 Step 8.1 Red）。
 *
 * イベント名カタログ + props 許可判定 + DebateTelemetryClient ファクトリの検証。
 * 発火元の結線（DebateScreen / Backend からの呼び出し）は Phase 2 範囲では不要。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 8
 */

import { describe, expect, it, vi } from 'vitest';

import {
  DEBATE_TELEMETRY_EVENT_NAMES,
  createDebateTelemetryClient,
  isAllowedDebateProp,
  isKnownDebateTelemetryEvent,
} from './telemetry';

describe('DEBATE_TELEMETRY_EVENT_NAMES', () => {
  it('Phase 2 で 10 イベント名を提供', () => {
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toHaveLength(10);
  });

  it('プレフィックスは全て debate.', () => {
    for (const name of DEBATE_TELEMETRY_EVENT_NAMES) {
      expect(name.startsWith('debate.')).toBe(true);
    }
  });

  it('必須 8 イベントを含む（Phase 2 で発火配線）', () => {
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.session_started');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.token_streamed');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.refused');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.agreed');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.session_complete');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.cooldown_triggered');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.affirmation_shown');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.stress_estimated');
  });

  it('Phase 3 結線予定の 2 イベントもスキーマだけ含む', () => {
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain('debate.moderation_blocked');
    expect(DEBATE_TELEMETRY_EVENT_NAMES).toContain(
      'debate.graceful_shutdown_initiated',
    );
  });
});

describe('isKnownDebateTelemetryEvent', () => {
  it('カタログ登録済みイベント → true', () => {
    expect(isKnownDebateTelemetryEvent('debate.session_started')).toBe(true);
  });

  it('未登録イベント → false（TEL-01: 未知イベントは作らない）', () => {
    expect(isKnownDebateTelemetryEvent('debate.unknown')).toBe(false);
    expect(isKnownDebateTelemetryEvent('reel.session_started')).toBe(false);
    expect(isKnownDebateTelemetryEvent('')).toBe(false);
  });
});

describe('isAllowedDebateProp', () => {
  it('debate.session_started + session_id → true', () => {
    expect(isAllowedDebateProp('debate.session_started', 'session_id')).toBe(true);
  });

  it('debate.session_started + asin → true', () => {
    expect(isAllowedDebateProp('debate.session_started', 'asin')).toBe(true);
  });

  it('debate.session_started + actor_id → false（PII 混入防止、TEL-02）', () => {
    expect(isAllowedDebateProp('debate.session_started', 'actor_id')).toBe(false);
  });

  it('debate.stress_estimated + level → true', () => {
    expect(isAllowedDebateProp('debate.stress_estimated', 'level')).toBe(true);
  });

  it('debate.stress_estimated + signals_used → false（PII 防止）', () => {
    // signals_used フィールドは Backend では debug 用、Telemetry には送らない
    expect(isAllowedDebateProp('debate.stress_estimated', 'signals_used')).toBe(false);
  });

  it('未登録イベント名 → false', () => {
    expect(isAllowedDebateProp('debate.unknown', 'session_id')).toBe(false);
  });
});

describe('createDebateTelemetryClient', () => {
  it('trackSessionStarted で正しいイベント名と props で track を呼ぶ', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackSessionStarted({
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
    });
    expect(track).toHaveBeenCalledWith('debate.session_started', {
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
    });
  });

  it('trackTokenStreamed で axis を伝達', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackTokenStreamed({ session_id: 'sess-1', axis: 'FACT' });
    expect(track).toHaveBeenCalledWith('debate.token_streamed', {
      session_id: 'sess-1',
      axis: 'FACT',
    });
  });

  it('trackRefused で cooldown_triggered フラグを伝達', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackRefused({
      session_id: 'sess-1',
      consecutive_refuses: 3,
      cooldown_triggered: true,
    });
    expect(track).toHaveBeenCalledWith('debate.refused', {
      session_id: 'sess-1',
      consecutive_refuses: 3,
      cooldown_triggered: true,
    });
  });

  it('trackAgreed で軸別翻意を計測（M-1/M-2 軸別 KPI）', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackAgreed({
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      axis: 'REWARD',
    });
    expect(track).toHaveBeenCalledWith('debate.agreed', {
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      axis: 'REWARD',
    });
  });

  it('trackSessionComplete で reason を伝達', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackSessionComplete({ session_id: 'sess-1', reason: 'agreed' });
    expect(track).toHaveBeenCalledWith('debate.session_complete', {
      session_id: 'sess-1',
      reason: 'agreed',
    });
  });

  it('trackCooldownTriggered で cooldown_until を伝達', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackCooldownTriggered({
      session_id: 'sess-1',
      cooldown_until: '2026-06-01T15:00:00.000Z',
    });
    expect(track).toHaveBeenCalledWith('debate.cooldown_triggered', {
      session_id: 'sess-1',
      cooldown_until: '2026-06-01T15:00:00.000Z',
    });
  });

  it('trackAffirmationShown で service_record_id を伝達', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackAffirmationShown({
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      service_record_id: '#503-2890471',
    });
    expect(track).toHaveBeenCalledWith('debate.affirmation_shown', {
      session_id: 'sess-1',
      asin: 'B01ABC1234',
      service_record_id: '#503-2890471',
    });
  });

  it('trackStressEstimated で Backend からの level を計測', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackStressEstimated({ session_id: 'sess-1', level: 'high' });
    expect(track).toHaveBeenCalledWith('debate.stress_estimated', {
      session_id: 'sess-1',
      level: 'high',
    });
  });

  it('trackModerationBlocked / trackGracefulShutdownInitiated は Phase 2 でスキーマのみ提供', () => {
    const track = vi.fn();
    const client = createDebateTelemetryClient(track);
    client.trackModerationBlocked({
      session_id: 'sess-1',
      layer: 'guardrails',
      pattern_detected: 'NG-6',
    });
    client.trackGracefulShutdownInitiated({
      session_id: 'sess-1',
      elapsed_seconds: 80,
    });
    expect(track).toHaveBeenCalledTimes(2);
    expect(track.mock.calls[0]?.[0]).toBe('debate.moderation_blocked');
    expect(track.mock.calls[1]?.[0]).toBe('debate.graceful_shutdown_initiated');
  });
});
