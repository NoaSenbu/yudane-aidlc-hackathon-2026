/**
 * DebateViewModel のテスト（Phase 2 Step 6.1 Red）。
 *
 * Direction D D-2 DebateScreen の純ロジック層。token event を軸別ラベルに振り分け、
 * 90 秒タイマーの残時間を計算し、CTA ボタンの活性状態を導出する純関数 reducer。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3
 */

import { describe, expect, it } from 'vitest';

import type { StrandsStreamEvent } from '../types';
import {
  DEBATE_AGREE_CTA,
  DEBATE_AXIS_LABELS,
  DEBATE_DURATION_SECONDS,
  DEBATE_HEADER_TITLE,
  DEBATE_QUICK_REPLIES,
  debateAxisToLabel,
} from './direction-d-labels';
import {
  buildInitialDebateView,
  reduceDebateView,
  type DebateViewEvent,
  type DebateViewState,
} from './debate-view-model';

const _T0 = new Date('2026-06-01T12:00:00Z');

function _withSession(): DebateViewState {
  return reduceDebateView(buildInitialDebateView(), {
    type: 'session_started',
    asin: 'B01ABC1234',
    trigger: 'reel_skip',
    startedAt: _T0,
  });
}

describe('direction-d-labels', () => {
  it('FACT → 論破 I・データ', () => {
    expect(debateAxisToLabel('FACT')).toBe('論破 I・データ');
  });

  it('PSYCHOLOGY → 論破 II・感想', () => {
    expect(debateAxisToLabel('PSYCHOLOGY')).toBe('論破 II・感想');
  });

  it('REWARD → 論破 III・ご褒美', () => {
    expect(debateAxisToLabel('REWARD')).toBe('論破 III・ご褒美');
  });

  it('undefined → undefined（Direction D 既定スタイル）', () => {
    expect(debateAxisToLabel(undefined)).toBeUndefined();
  });

  it('DEBATE_AXIS_LABELS が Direction D HTML（D-2）と整合する固定文字列', () => {
    expect(DEBATE_AXIS_LABELS).toEqual({
      FACT: '論破 I・データ',
      PSYCHOLOGY: '論破 II・感想',
      REWARD: '論破 III・ご褒美',
    });
  });

  it('ヘッダタイトル + 担当バッジ + クイック返信 + CTA が固定文字列', () => {
    expect(DEBATE_HEADER_TITLE).toBe('迷い、論破します');
    expect(DEBATE_QUICK_REPLIES).toEqual(['いや高くない?', 'また今度で', '本当に要る?']);
    expect(DEBATE_AGREE_CTA).toBe('論破されたので買う');
    expect(DEBATE_DURATION_SECONDS).toBe(90);
  });
});

describe('reduceDebateView', () => {
  it('初期状態 = idle、token なし', () => {
    const init = buildInitialDebateView();
    expect(init.sessionStatus).toBe('idle');
    expect(init.factTokens).toEqual([]);
    expect(init.psychologyTokens).toEqual([]);
    expect(init.rewardTokens).toEqual([]);
  });

  it('session_started で sessionStatus="streaming" + asin/trigger/startedAt 反映', () => {
    const state = _withSession();
    expect(state.sessionStatus).toBe('streaming');
    expect(state.asin).toBe('B01ABC1234');
    expect(state.trigger).toBe('reel_skip');
    expect(state.startedAt).toEqual(_T0);
  });

  it('token + axis=FACT → factTokens にラベル付き append', () => {
    const evt: StrandsStreamEvent = {
      type: 'token',
      delta_text: '時給換算で',
      metadata: { axis: 'FACT' },
    };
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: evt,
    });
    expect(state.factTokens).toEqual(['時給換算で']);
    expect(state.factLabel).toBe('論破 I・データ');
  });

  it('token + axis=PSYCHOLOGY → psychologyTokens に append', () => {
    const evt: StrandsStreamEvent = {
      type: 'token',
      delta_text: '結局',
      metadata: { axis: 'PSYCHOLOGY' },
    };
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: evt,
    });
    expect(state.psychologyTokens).toEqual(['結局']);
    expect(state.psychologyLabel).toBe('論破 II・感想');
  });

  it('token + axis=REWARD → rewardTokens に append', () => {
    const evt: StrandsStreamEvent = {
      type: 'token',
      delta_text: 'ご褒美',
      metadata: { axis: 'REWARD' },
    };
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: evt,
    });
    expect(state.rewardTokens).toEqual(['ご褒美']);
    expect(state.rewardLabel).toBe('論破 III・ご褒美');
  });

  it('token + axis=undefined → uncategorizedTokens に append', () => {
    const evt: StrandsStreamEvent = {
      type: 'token',
      delta_text: '無印',
    };
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: evt,
    });
    expect(state.uncategorizedTokens).toEqual(['無印']);
  });

  it('session_complete で sessionStatus="complete" + reason', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: {
        type: 'session_complete',
        metadata: { reason: 'agreed' },
      },
    });
    expect(state.sessionStatus).toBe('complete');
    expect(state.completionReason).toBe('agreed');
  });

  it('error で sessionStatus="error" + reason', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: {
        type: 'error',
        metadata: { reason: 'auth.unauthenticated' },
      },
    });
    expect(state.sessionStatus).toBe('error');
    expect(state.errorReason).toBe('auth.unauthenticated');
  });

  it('debate.cooldown_triggered で sessionStatus="cooldown" + cooldownUntil', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: {
        type: 'debate.cooldown_triggered',
        metadata: { cooldown_until: '2026-06-01T15:00:00.000Z' },
      },
    });
    expect(state.sessionStatus).toBe('cooldown');
    expect(state.cooldownUntil).toBe('2026-06-01T15:00:00.000Z');
  });
});

describe('reduceDebateView - timer', () => {
  it('startedAt から 0 秒経過 → remainingSeconds=90', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'tick',
      now: _T0,
    });
    expect(state.remainingSeconds).toBe(90);
  });

  it('startedAt から 30 秒経過 → remainingSeconds=60', () => {
    const t30 = new Date(_T0.getTime() + 30 * 1000);
    const state = reduceDebateView(_withSession(), {
      type: 'tick',
      now: t30,
    });
    expect(state.remainingSeconds).toBe(60);
  });

  it('startedAt から 90 秒経過 → remainingSeconds=0', () => {
    const t90 = new Date(_T0.getTime() + 90 * 1000);
    const state = reduceDebateView(_withSession(), {
      type: 'tick',
      now: t90,
    });
    expect(state.remainingSeconds).toBe(0);
  });

  it('startedAt から 120 秒経過 → remainingSeconds=0（負にならない）', () => {
    const t120 = new Date(_T0.getTime() + 120 * 1000);
    const state = reduceDebateView(_withSession(), {
      type: 'tick',
      now: t120,
    });
    expect(state.remainingSeconds).toBe(0);
  });
});

describe('reduceDebateView - CTA 活性状態', () => {
  it('streaming 中で agree CTA 活性、refuse link 活性', () => {
    const state = _withSession();
    expect(state.canAgree).toBe(true);
    expect(state.canRefuse).toBe(true);
  });

  it('error 状態では agree / refuse とも非活性、retry 活性', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: { type: 'error', metadata: { reason: 'auth.unauthenticated' } },
    });
    expect(state.canAgree).toBe(false);
    expect(state.canRefuse).toBe(false);
    expect(state.canRetry).toBe(true);
  });

  it('cooldown 状態では agree / refuse とも非活性', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: {
        type: 'debate.cooldown_triggered',
        metadata: { cooldown_until: '2026-06-01T15:00:00.000Z' },
      },
    });
    expect(state.canAgree).toBe(false);
    expect(state.canRefuse).toBe(false);
  });

  it('complete 状態では agree CTA 非活性（既に翻意済 / 完了）', () => {
    const state = reduceDebateView(_withSession(), {
      type: 'stream_event',
      event: { type: 'session_complete', metadata: { reason: 'agreed' } },
    });
    expect(state.canAgree).toBe(false);
  });
});
