/**
 * Auth ゲートの状態遷移（frontend-components.md §2.3）。
 *
 * 起動時 unknown → セッション検証で authenticated/unauthenticated。
 * onAuthExpired で unauthenticated に戻る。純粋 reducer としてテスト可能にする。
 */

import type { AuthStatus, DeepLinkTarget } from './navigation';

/** Auth ゲートの状態。 */
export interface AuthGateState {
  authStatus: AuthStatus;
  pendingDeepLink: DeepLinkTarget | null;
}

/** Auth ゲートのイベント。 */
export type AuthGateEvent =
  | { type: 'session-resolved'; authenticated: boolean }
  | { type: 'sign-in-success' }
  | { type: 'auth-expired' }
  | { type: 'deeplink-received'; target: DeepLinkTarget }
  | { type: 'deeplink-consumed' };

/** 初期状態。 */
export const initialAuthGateState: AuthGateState = {
  authStatus: 'unknown',
  pendingDeepLink: null,
};

/**
 * Auth ゲートの状態遷移関数（純粋）。
 *
 * @param state - 現在状態
 * @param event - イベント
 * @returns 次状態
 */
export function authGateReducer(state: AuthGateState, event: AuthGateEvent): AuthGateState {
  switch (event.type) {
    case 'session-resolved':
      return {
        ...state,
        authStatus: event.authenticated ? 'authenticated' : 'unauthenticated',
      };
    case 'sign-in-success':
      return { ...state, authStatus: 'authenticated' };
    case 'auth-expired':
      // セッションクリアして未認証へ戻す。pending は保持（再認証後に解決）
      return { ...state, authStatus: 'unauthenticated' };
    case 'deeplink-received':
      // 未認証なら保留。認証済みなら即時遷移なので保留しない
      if (state.authStatus !== 'authenticated') {
        return { ...state, pendingDeepLink: event.target };
      }
      return state;
    case 'deeplink-consumed':
      return { ...state, pendingDeepLink: null };
    default:
      return state;
  }
}
