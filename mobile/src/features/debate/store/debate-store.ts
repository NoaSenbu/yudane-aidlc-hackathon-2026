/**
 * DebateSession Store（Phase 2 Step 5.2 Green、Zustand slice）。
 *
 * agentcore-client の AsyncIterableIterator + event-parser の StrandsStreamEvent を
 * UI 層に橋渡しする状態管理。既存 onboarding-store / toast-slice と同じ
 * `StateCreator<Slice>` パターンで純ロジックを実装。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 5
 * 参照: aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md §3
 */

import type { StateCreator } from 'zustand';

import type {
  DebateAxis,
  DebateInvocationPayload,
  StrandsStreamEvent,
} from '../types';

/** セッションのライフサイクル状態。 */
export type DebateSessionStatus =
  | 'idle'
  | 'streaming'
  | 'complete'
  | 'error'
  | 'cancelled'
  | 'cooldown';

/** 軸ごとのトークン蓄積。 */
export interface TokensByAxis {
  fact: string[];
  psychology: string[];
  reward: string[];
  uncategorized: string[];
}

/** startSession の引数。 */
export interface StartSessionInput {
  readonly asin: string;
  readonly trigger: DebateInvocationPayload['trigger'];
  readonly startedAt: Date;
  readonly abortController?: AbortController;
  readonly clientSessionId?: string;
}

/** Zustand slice。 */
export interface DebateSlice {
  readonly sessionStatus: DebateSessionStatus;
  readonly asin: string | undefined;
  readonly trigger: DebateInvocationPayload['trigger'] | undefined;
  readonly startedAt: Date | undefined;
  readonly tokensByAxis: TokensByAxis;
  readonly completionReason: string | undefined;
  readonly errorReason: string | undefined;
  readonly cooldownUntil: string | undefined;
  readonly clientSessionId: string | undefined;
  startSession: (input: StartSessionInput) => void;
  appendToken: (event: StrandsStreamEvent) => void;
  handleSessionComplete: (reason: string) => void;
  handleError: (reason: string) => void;
  handleCooldown: (cooldownUntil: string) => void;
  cancel: () => void;
  reset: () => void;
}

const _emptyTokensByAxis = (): TokensByAxis => ({
  fact: [],
  psychology: [],
  reward: [],
  uncategorized: [],
});

const _initialState = {
  sessionStatus: 'idle' as DebateSessionStatus,
  asin: undefined,
  trigger: undefined,
  startedAt: undefined,
  tokensByAxis: _emptyTokensByAxis(),
  completionReason: undefined,
  errorReason: undefined,
  cooldownUntil: undefined,
  clientSessionId: undefined,
} as const;

/**
 * 軸タグから tokensByAxis のキーへのマッピング（純関数）。
 *
 * @param axis - StrandsStreamEvent.metadata.axis（'FACT' / 'PSYCHOLOGY' / 'REWARD' / undefined）
 * @returns tokensByAxis のキー名
 */
export function axisToBucket(axis: DebateAxis | undefined): keyof TokensByAxis {
  if (axis === 'FACT') {
    return 'fact';
  }
  if (axis === 'PSYCHOLOGY') {
    return 'psychology';
  }
  if (axis === 'REWARD') {
    return 'reward';
  }
  return 'uncategorized';
}

/** AbortController を slice の外側で保持する（store の equality 判定を汚染しないため）。 */
const _abortControllers = new WeakMap<DebateSlice, AbortController>();

/** Zustand slice 生成器。 */
export const createDebateSlice: StateCreator<DebateSlice, [], [], DebateSlice> = (
  set,
  get,
) => ({
  ..._initialState,

  startSession: (input) => {
    set({
      sessionStatus: 'streaming',
      asin: input.asin,
      trigger: input.trigger,
      startedAt: input.startedAt,
      tokensByAxis: _emptyTokensByAxis(),
      completionReason: undefined,
      errorReason: undefined,
      cooldownUntil: undefined,
      clientSessionId: input.clientSessionId,
    });
    if (input.abortController !== undefined) {
      _abortControllers.set(get(), input.abortController);
    }
  },

  appendToken: (event) => {
    if (event.type !== 'token' || event.delta_text === undefined) {
      return;
    }
    const bucket = axisToBucket(event.metadata?.axis);
    set((state) => ({
      tokensByAxis: {
        ...state.tokensByAxis,
        [bucket]: [...state.tokensByAxis[bucket], event.delta_text!],
      },
    }));
  },

  handleSessionComplete: (reason) => {
    set({ sessionStatus: 'complete', completionReason: reason });
  },

  handleError: (reason) => {
    set({ sessionStatus: 'error', errorReason: reason });
  },

  handleCooldown: (cooldownUntil) => {
    set({ sessionStatus: 'cooldown', cooldownUntil });
  },

  cancel: () => {
    const ctrl = _abortControllers.get(get());
    if (ctrl !== undefined) {
      ctrl.abort();
    }
    set({ sessionStatus: 'cancelled' });
  },

  reset: () => {
    set({ ..._initialState, tokensByAxis: _emptyTokensByAxis() });
  },
});
