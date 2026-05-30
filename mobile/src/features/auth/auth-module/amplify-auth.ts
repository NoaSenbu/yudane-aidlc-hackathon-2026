/**
 * Amplify Auth v6 の薄いラッパー（MFA-06/07）。
 *
 * Amplify への依存をここに隔離する。状態機械（auth-machine）とトークン供給
 * （auth-token-provider）が利用する。実 Amplify 呼び出しは実機統合時に結線。
 */

/** トークンセット。 */
export interface TokenSet {
  accessToken: string;
  idToken: string;
  refreshToken: string;
}

/** サインイン結果（MFA 要否を含む）。 */
export type SignInResult =
  | { kind: 'mfa-required'; session: string }
  | { kind: 'authenticated'; tokens: TokenSet };

/**
 * Amplify Auth の操作インターフェース。
 *
 * 実装は `aws-amplify/auth` を呼ぶ。テストではモックを注入する。
 */
export interface AmplifyAuthGateway {
  signUp(email: string, password: string): Promise<void>;
  confirmSignUp(email: string, code: string): Promise<void>;
  signIn(email: string, password: string): Promise<SignInResult>;
  confirmMfa(session: string, totp: string): Promise<TokenSet>;
  setupMfa(): Promise<{ qrUri: string; secret: string }>;
  refresh(): Promise<TokenSet | null>;
  signOut(): Promise<void>;
  getAccessToken(): Promise<string | null>;
}
