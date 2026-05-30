import { describe, expect, it, vi } from 'vitest';

import type { AmplifyAuthGateway } from './amplify-auth';
import { type AuthState, authMachineReducer } from './auth-machine';
import { createAuthTokenProvider } from './auth-token-provider';

describe('authMachineReducer', () => {
  it('idle → signIn → signingIn', () => {
    expect(authMachineReducer('idle', { type: 'signIn' })).toBe('signingIn');
  });

  it('signingIn → mfaRequired → mfaChallenge', () => {
    expect(authMachineReducer('signingIn', { type: 'mfaRequired' })).toBe('mfaChallenge');
  });

  it('signingIn → noMfa → authenticated', () => {
    expect(authMachineReducer('signingIn', { type: 'noMfa' })).toBe('authenticated');
  });

  it('mfaChallenge → submitMfa → confirmingMfa → success → authenticated', () => {
    const s1 = authMachineReducer('mfaChallenge', { type: 'submitMfa' });
    expect(s1).toBe('confirmingMfa');
    expect(authMachineReducer(s1, { type: 'success' })).toBe('authenticated');
  });

  it('confirmingMfa → failure → error → 再 signIn 可能', () => {
    const err = authMachineReducer('confirmingMfa', { type: 'failure' });
    expect(err).toBe('error');
    expect(authMachineReducer(err, { type: 'signIn' })).toBe('signingIn');
  });

  it('authenticated → requestMfaReset → mfaResetRequested', () => {
    expect(authMachineReducer('authenticated', { type: 'requestMfaReset' })).toBe(
      'mfaResetRequested',
    );
  });

  it('authenticated → signOut → idle', () => {
    expect(authMachineReducer('authenticated', { type: 'signOut' })).toBe('idle');
  });

  it('不正遷移は現状維持', () => {
    const invalid: AuthState = 'idle';
    expect(authMachineReducer(invalid, { type: 'success' })).toBe('idle');
  });
});

describe('createAuthTokenProvider', () => {
  function makeGateway(overrides: Partial<AmplifyAuthGateway> = {}): AmplifyAuthGateway {
    return {
      signUp: vi.fn(),
      confirmSignUp: vi.fn(),
      signIn: vi.fn(),
      confirmMfa: vi.fn(),
      setupMfa: vi.fn(),
      refresh: vi.fn(),
      signOut: vi.fn(),
      getAccessToken: vi.fn().mockResolvedValue('token-1'),
      ...overrides,
    };
  }

  it('refresh 成功で true', async () => {
    const gateway = makeGateway({
      refresh: vi.fn().mockResolvedValue({ accessToken: 'a', idToken: 'i', refreshToken: 'r' }),
    });
    const provider = createAuthTokenProvider(gateway, vi.fn());
    expect(await provider.refresh()).toBe(true);
  });

  it('refresh 失敗（null）で false', async () => {
    const gateway = makeGateway({ refresh: vi.fn().mockResolvedValue(null) });
    const provider = createAuthTokenProvider(gateway, vi.fn());
    expect(await provider.refresh()).toBe(false);
  });

  it('getAccessToken を委譲する', async () => {
    const gateway = makeGateway();
    const provider = createAuthTokenProvider(gateway, vi.fn());
    expect(await provider.getAccessToken()).toBe('token-1');
  });
});
