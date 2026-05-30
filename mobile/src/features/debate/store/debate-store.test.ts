/**
 * DebateSession Store のテスト（Phase 2 Step 5.1 Red）。
 *
 * Zustand slice ベース、純ロジックテスト（既存 onboarding-store / toast-slice と同パターン）。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 5
 */

import { describe, expect, it, vi } from 'vitest';
import { create } from 'zustand';

import { createDebateSlice, type DebateSlice } from './debate-store';

function buildStore() {
  return create<DebateSlice>()((...a) => createDebateSlice(...a));
}

describe('debate-store', () => {
  it('startSession で論破セッションが開始され、tokensByAxis が空になる', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    const state = store.getState();
    expect(state.asin).toBe('B01ABC1234');
    expect(state.trigger).toBe('reel_skip');
    expect(state.sessionStatus).toBe('streaming');
    expect(state.tokensByAxis.fact).toEqual([]);
    expect(state.tokensByAxis.psychology).toEqual([]);
    expect(state.tokensByAxis.reward).toEqual([]);
    expect(state.tokensByAxis.uncategorized).toEqual([]);
  });

  it('appendToken で metadata.axis=FACT の token が tokensByAxis.fact に append', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().appendToken({
      type: 'token',
      delta_text: '時給換算で',
      metadata: { axis: 'FACT' },
    });
    expect(store.getState().tokensByAxis.fact).toEqual(['時給換算で']);
  });

  it('appendToken で metadata.axis=PSYCHOLOGY → psychology に append', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().appendToken({
      type: 'token',
      delta_text: '結局',
      metadata: { axis: 'PSYCHOLOGY' },
    });
    expect(store.getState().tokensByAxis.psychology).toEqual(['結局']);
  });

  it('appendToken で metadata.axis=REWARD → reward に append', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().appendToken({
      type: 'token',
      delta_text: 'ご褒美',
      metadata: { axis: 'REWARD' },
    });
    expect(store.getState().tokensByAxis.reward).toEqual(['ご褒美']);
  });

  it('appendToken で metadata.axis=undefined → uncategorized に append', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().appendToken({
      type: 'token',
      delta_text: '無印テキスト',
    });
    expect(store.getState().tokensByAxis.uncategorized).toEqual(['無印テキスト']);
  });

  it('handleSessionComplete で sessionStatus="complete"', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().handleSessionComplete('agent_completed');
    expect(store.getState().sessionStatus).toBe('complete');
    expect(store.getState().completionReason).toBe('agent_completed');
  });

  it('handleError で sessionStatus="error" と reason がセット', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().handleError('auth.unauthenticated');
    expect(store.getState().sessionStatus).toBe('error');
    expect(store.getState().errorReason).toBe('auth.unauthenticated');
  });

  it('handleCooldown で sessionStatus="cooldown" と cooldownUntil がセット', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    const cooldownUntil = '2026-06-01T15:00:00.000Z';
    store.getState().handleCooldown(cooldownUntil);
    expect(store.getState().sessionStatus).toBe('cooldown');
    expect(store.getState().cooldownUntil).toBe(cooldownUntil);
  });

  it('cancel で AbortController が abort される', () => {
    const store = buildStore();
    const ctrl = new AbortController();
    const abortSpy = vi.spyOn(ctrl, 'abort');
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
      abortController: ctrl,
    });
    store.getState().cancel();
    expect(abortSpy).toHaveBeenCalled();
    expect(store.getState().sessionStatus).toBe('cancelled');
  });

  it('reset で初期状態に戻る', () => {
    const store = buildStore();
    store.getState().startSession({
      asin: 'B01ABC1234',
      trigger: 'reel_skip',
      startedAt: new Date('2026-06-01T12:00:00Z'),
    });
    store.getState().appendToken({
      type: 'token',
      delta_text: 'X',
      metadata: { axis: 'FACT' },
    });
    store.getState().reset();
    expect(store.getState().sessionStatus).toBe('idle');
    expect(store.getState().asin).toBeUndefined();
    expect(store.getState().tokensByAxis.fact).toEqual([]);
  });
});
