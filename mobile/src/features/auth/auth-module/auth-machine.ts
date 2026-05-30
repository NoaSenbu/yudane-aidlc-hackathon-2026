/**
 * MFA チャレンジ駆動の認証状態機械（PAT2-MFA-01、純ロジック）。
 *
 * Amplify Auth v6 のチャレンジに対応する状態遷移を表現する。UI / SDK 依存から分離し
 * テスト可能にする。設計: business-logic-model.md ALG-MFA / business-rules.md MFA-01〜07。
 */

/** 認証状態。 */
export type AuthState =
  | 'idle'
  | 'signingIn'
  | 'mfaChallenge'
  | 'confirmingMfa'
  | 'authenticated'
  | 'error'
  | 'mfaResetRequested';

/** 認証イベント。 */
export type AuthEvent =
  | { type: 'signIn' }
  | { type: 'mfaRequired' }
  | { type: 'noMfa' }
  | { type: 'submitMfa' }
  | { type: 'success' }
  | { type: 'failure' }
  | { type: 'requestMfaReset' }
  | { type: 'signOut' };

/**
 * 認証状態機械の遷移関数（純粋）。
 *
 * @param state - 現在状態
 * @param event - イベント
 * @returns 次状態（不正遷移は現状維持）
 */
export function authMachineReducer(state: AuthState, event: AuthEvent): AuthState {
  switch (state) {
    case 'idle':
      if (event.type === 'signIn') return 'signingIn';
      return state;
    case 'signingIn':
      if (event.type === 'mfaRequired') return 'mfaChallenge';
      if (event.type === 'noMfa') return 'authenticated';
      if (event.type === 'failure') return 'error';
      return state;
    case 'mfaChallenge':
      if (event.type === 'submitMfa') return 'confirmingMfa';
      if (event.type === 'failure') return 'error';
      return state;
    case 'confirmingMfa':
      if (event.type === 'success') return 'authenticated';
      if (event.type === 'failure') return 'error';
      return state;
    case 'authenticated':
      if (event.type === 'signOut') return 'idle';
      if (event.type === 'requestMfaReset') return 'mfaResetRequested';
      return state;
    case 'error':
      // エラーから再試行可能（MFA-05 ロックは Cognito 側でカウント）
      if (event.type === 'signIn') return 'signingIn';
      if (event.type === 'requestMfaReset') return 'mfaResetRequested';
      return state;
    case 'mfaResetRequested':
      // 72h 冷却後にリセット完了 → idle（MFA-04、冷却は別途タイムスタンプ管理）
      if (event.type === 'signOut') return 'idle';
      return state;
    default:
      return state;
  }
}
