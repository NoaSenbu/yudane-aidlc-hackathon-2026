import { describe, expect, it } from 'vitest';

import { authGateReducer, initialAuthGateState } from './auth-gate';
import type { DeepLinkTarget } from './navigation';

const target: DeepLinkTarget = { screen: 'cart', source: 'push', params: { itemId: 'i1' } };

describe('authGateReducer', () => {
  it('初期状態は unknown / pending なし', () => {
    expect(initialAuthGateState).toEqual({ authStatus: 'unknown', pendingDeepLink: null });
  });

  it('session-resolved(true) で authenticated', () => {
    const s = authGateReducer(initialAuthGateState, {
      type: 'session-resolved',
      authenticated: true,
    });
    expect(s.authStatus).toBe('authenticated');
  });

  it('session-resolved(false) で unauthenticated', () => {
    const s = authGateReducer(initialAuthGateState, {
      type: 'session-resolved',
      authenticated: false,
    });
    expect(s.authStatus).toBe('unauthenticated');
  });

  it('auth-expired で unauthenticated に戻る', () => {
    const authed = { authStatus: 'authenticated' as const, pendingDeepLink: null };
    expect(authGateReducer(authed, { type: 'auth-expired' }).authStatus).toBe('unauthenticated');
  });

  it('未認証中の deeplink は pending に保持', () => {
    const unauth = { authStatus: 'unauthenticated' as const, pendingDeepLink: null };
    const s = authGateReducer(unauth, { type: 'deeplink-received', target });
    expect(s.pendingDeepLink).toEqual(target);
  });

  it('認証済み中の deeplink は保留しない', () => {
    const authed = { authStatus: 'authenticated' as const, pendingDeepLink: null };
    const s = authGateReducer(authed, { type: 'deeplink-received', target });
    expect(s.pendingDeepLink).toBeNull();
  });

  it('sign-in 後に deeplink-consumed で pending クリア', () => {
    const withPending = { authStatus: 'unauthenticated' as const, pendingDeepLink: target };
    const signedIn = authGateReducer(withPending, { type: 'sign-in-success' });
    expect(signedIn.authStatus).toBe('authenticated');
    // pending は保持されたまま、消費イベントでクリア
    const consumed = authGateReducer(signedIn, { type: 'deeplink-consumed' });
    expect(consumed.pendingDeepLink).toBeNull();
  });
});
