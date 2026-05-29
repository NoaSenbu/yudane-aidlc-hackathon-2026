import { describe, expect, it } from 'vitest';

import {
  decideNavigation,
  resolvePushTarget,
  resolveUrlTarget,
} from './navigation';

describe('resolvePushTarget', () => {
  it('cart-attack + itemId は cart 画面へ', () => {
    expect(resolvePushTarget({ type: 'cart-attack', itemId: 'item-1' })).toEqual({
      screen: 'cart',
      source: 'push',
      params: { itemId: 'item-1' },
    });
  });

  it('calendar は home へ', () => {
    expect(resolvePushTarget({ type: 'calendar' })).toMatchObject({ screen: 'home' });
  });

  it('未知 type は home フォールバック', () => {
    expect(resolvePushTarget({ type: 'mystery' })).toMatchObject({ screen: 'home' });
  });
});

describe('resolveUrlTarget', () => {
  it('既知 screen の deeplink を解決する', () => {
    expect(resolveUrlTarget('yudane://reel?origin=push')).toEqual({
      screen: 'reel',
      source: 'url',
      params: { origin: 'push' },
    });
  });

  it('未知 host は home フォールバック', () => {
    expect(resolveUrlTarget('yudane://unknown')).toMatchObject({ screen: 'home' });
  });

  it('パース不能は home フォールバック', () => {
    expect(resolveUrlTarget('!!!')).toMatchObject({ screen: 'home' });
  });
});

describe('decideNavigation', () => {
  const target = { screen: 'cart', source: 'push' } as const;

  it('認証済み + target は対象画面へ', () => {
    expect(decideNavigation('authenticated', target)).toEqual({ screen: 'cart' });
  });

  it('未認証 + target は保留（pending）', () => {
    expect(decideNavigation('unauthenticated', target)).toEqual({ pending: target });
  });

  it('認証済み + target なしは home', () => {
    expect(decideNavigation('authenticated', null)).toEqual({ screen: 'home' });
  });

  it('unknown + target なしは home', () => {
    expect(decideNavigation('unknown', null)).toEqual({ screen: 'home' });
  });
});
