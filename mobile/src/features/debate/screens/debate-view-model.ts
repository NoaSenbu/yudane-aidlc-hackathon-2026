/**
 * DebateViewModel（Phase 2 Step 6.2 Green）。
 *
 * Direction D D-2 DebateScreen の純ロジック層。token event を軸別 token 配列に振り分け、
 * 90 秒タイマーの残時間を計算し、CTA ボタンの活性状態を導出する純関数 reducer。
 * React Native コンポーネント本体は実機ビルド時に追加（Phase 2 範囲外）。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3
 * 参照: 既存パターン mobile/src/features/auth/auth-module/auth-machine.ts（純関数 reducer）
 */

import type { DebateInvocationPayload, StrandsStreamEvent } from '../types';
import {
  DEBATE_DURATION_SECONDS,
  debateAxisToLabel,
} from './direction-d-labels';

/** セッションのライフサイクル状態。 */
export type DebateViewSessionStatus =
  | 'idle'
  | 'streaming'
  | 'complete'
  | 'error'
  | 'cooldown'
  | 'moderation_blocked'
  | 'graceful_shutting_down';

/** ViewModel の state（純データ、Direction D UI 表示で使う全フィールド）。 */
export interface DebateViewState {
  readonly sessionStatus: DebateViewSessionStatus;
  readonly asin: string | undefined;
  readonly trigger: DebateInvocationPayload['trigger'] | undefined;
  readonly startedAt: Date | undefined;
  readonly remainingSeconds: number;
  /** axis=FACT の token（時系列順、Direction D 「論破 I・データ」セクション用）。 */
  readonly factTokens: readonly string[];
  /** Direction D ラベル「論破 I・データ」（factTokens が空でも常に同じ）。 */
  readonly factLabel: string;
  readonly psychologyTokens: readonly string[];
  readonly psychologyLabel: string;
  readonly rewardTokens: readonly string[];
  readonly rewardLabel: string;
  /** axis 未付与の token（Direction D では既定スタイルで表示）。 */
  readonly uncategorizedTokens: readonly string[];
  readonly completionReason: string | undefined;
  readonly errorReason: string | undefined;
  readonly cooldownUntil: string | undefined;
  /** moderation_blocked 時の検出 NG パターン ID（NG-3 / NG-6、Phase 3 Step 3-2）。 */
  readonly moderationPatternId: string | undefined;
  /** graceful_shutdown_initiated 時の経過秒数（Phase 3 Step 3-1）。 */
  readonly gracefulShutdownElapsedSeconds: number | undefined;
  readonly canAgree: boolean;
  readonly canRefuse: boolean;
  readonly canRetry: boolean;
}

/** ViewModel に対する event。 */
export type DebateViewEvent =
  | {
      readonly type: 'session_started';
      readonly asin: string;
      readonly trigger: DebateInvocationPayload['trigger'];
      readonly startedAt: Date;
    }
  | {
      readonly type: 'stream_event';
      readonly event: StrandsStreamEvent;
    }
  | {
      readonly type: 'tick';
      readonly now: Date;
    }
  | {
      readonly type: 'reset';
    };

/**
 * 初期状態を構築する純関数。
 *
 * @returns idle 状態の DebateViewState（factLabel 等は固定文字列で初期化）。
 */
export function buildInitialDebateView(): DebateViewState {
  return {
    sessionStatus: 'idle',
    asin: undefined,
    trigger: undefined,
    startedAt: undefined,
    remainingSeconds: DEBATE_DURATION_SECONDS,
    factTokens: [],
    factLabel: '論破 I・データ',
    psychologyTokens: [],
    psychologyLabel: '論破 II・感想',
    rewardTokens: [],
    rewardLabel: '論破 III・ご褒美',
    uncategorizedTokens: [],
    completionReason: undefined,
    errorReason: undefined,
    cooldownUntil: undefined,
    moderationPatternId: undefined,
    gracefulShutdownElapsedSeconds: undefined,
    canAgree: false,
    canRefuse: false,
    canRetry: false,
  };
}

/**
 * DebateViewState を更新する純関数 reducer（Redux/useReducer 互換）。
 *
 * @param state - 現在状態。
 * @param event - 適用するイベント。
 * @returns 新しい状態（state は不変、新オブジェクトを返す）。
 */
export function reduceDebateView(
  state: DebateViewState,
  event: DebateViewEvent,
): DebateViewState {
  switch (event.type) {
    case 'session_started':
      return {
        ...buildInitialDebateView(),
        sessionStatus: 'streaming',
        asin: event.asin,
        trigger: event.trigger,
        startedAt: event.startedAt,
        canAgree: true,
        canRefuse: true,
      };
    case 'stream_event':
      return _applyStreamEvent(state, event.event);
    case 'tick':
      return _applyTick(state, event.now);
    case 'reset':
      return buildInitialDebateView();
    default:
      return state;
  }
}

function _applyStreamEvent(
  state: DebateViewState,
  evt: StrandsStreamEvent,
): DebateViewState {
  switch (evt.type) {
    case 'token':
      return _appendToken(state, evt);
    case 'session_complete':
      return {
        ...state,
        sessionStatus: 'complete',
        completionReason: evt.metadata?.reason,
        canAgree: false,
        canRefuse: false,
        canRetry: false,
      };
    case 'error':
      return {
        ...state,
        sessionStatus: 'error',
        errorReason: evt.metadata?.reason,
        canAgree: false,
        canRefuse: false,
        canRetry: true,
      };
    case 'debate.cooldown_triggered':
      return {
        ...state,
        sessionStatus: 'cooldown',
        cooldownUntil: evt.metadata?.cooldown_until,
        canAgree: false,
        canRefuse: false,
        canRetry: false,
      };
    case 'moderation_blocked':
      // 第 3 層モデレーション NG-3 / NG-6 検出。即座に CTA を不活性化、UI 上で
      // 「言葉を選び直しています」表示用の status に遷移（Direction D 仕様、business-rules MOD-01）。
      // 検出された pattern_id は Telemetry で送信（matched_text は含めない、SECURITY-08）。
      return {
        ...state,
        sessionStatus: 'moderation_blocked',
        moderationPatternId: evt.metadata?.pattern_id,
        canAgree: false,
        canRefuse: false,
        canRetry: false,
      };
    case 'graceful_shutdown_initiated':
      // 80 秒経過で graceful shutdown 開始。サマリ生成中は streaming 継続だが
      // タイマー UI を「まとめ中」に切替。CTA は維持（agree は引き続き可能）。
      return {
        ...state,
        sessionStatus: 'graceful_shutting_down',
        gracefulShutdownElapsedSeconds: evt.metadata?.elapsed_seconds,
      };
    case 'turn_complete':
      // turn_complete は Phase 2 では UI に反映しない（streaming 継続）
      return state;
    default:
      return state;
  }
}

function _appendToken(
  state: DebateViewState,
  evt: StrandsStreamEvent,
): DebateViewState {
  if (evt.delta_text === undefined || evt.delta_text === '') {
    return state;
  }
  const axis = evt.metadata?.axis;
  const label = debateAxisToLabel(axis);
  void label; // Direction D ラベルは固定で state に含まれているので使用不要

  if (axis === 'FACT') {
    return { ...state, factTokens: [...state.factTokens, evt.delta_text] };
  }
  if (axis === 'PSYCHOLOGY') {
    return {
      ...state,
      psychologyTokens: [...state.psychologyTokens, evt.delta_text],
    };
  }
  if (axis === 'REWARD') {
    return { ...state, rewardTokens: [...state.rewardTokens, evt.delta_text] };
  }
  return {
    ...state,
    uncategorizedTokens: [...state.uncategorizedTokens, evt.delta_text],
  };
}

function _applyTick(state: DebateViewState, now: Date): DebateViewState {
  if (state.startedAt === undefined) {
    return state;
  }
  const elapsedMs = now.getTime() - state.startedAt.getTime();
  const elapsedSec = Math.floor(elapsedMs / 1000);
  const remaining = Math.max(0, DEBATE_DURATION_SECONDS - elapsedSec);
  return { ...state, remainingSeconds: remaining };
}
