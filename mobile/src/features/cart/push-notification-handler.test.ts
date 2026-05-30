/**
 * M-09 PushNotificationHandler 単体 + PBT テスト。
 *
 * Validates: NFR-PBT-01 Round-trip / Property 3 productId 不正時 fallback。
 */

import fc from 'fast-check';
import { describe, expect, it } from 'vitest';

import {
  decodeDeepLink,
  encodeDeepLink,
  resolveCartTapNavigation,
  validatePushPayload,
  type PushPayload,
} from './push-notification-handler';

describe('validatePushPayload', () => {
  it('正常 cart-attack-30m payload を validate', () => {
    const result = validatePushPayload({
      type: 'cart-attack-30m',
      productId: 'B0CXXXXXXX',
      step: '30m',
    });
    expect(result).toEqual({
      type: 'cart-attack-30m',
      productId: 'B0CXXXXXXX',
      step: '30m',
    });
  });

  it('未知の type は null', () => {
    expect(validatePushPayload({ type: 'unknown' })).toBeNull();
  });

  it('null / undefined は null', () => {
    expect(validatePushPayload(null)).toBeNull();
    expect(validatePushPayload(undefined)).toBeNull();
  });

  it('type 欠落は null', () => {
    expect(validatePushPayload({ productId: 'B0CXXXXXXX' })).toBeNull();
  });
});

describe('resolveCartTapNavigation', () => {
  it('正常 cart-attack-30m → cart-detail へ navigate', () => {
    const result = resolveCartTapNavigation({
      type: 'cart-attack-30m',
      productId: 'B0CXXXXXXX',
      step: '30m',
    });
    expect(result.kind).toBe('cart-detail');
    if (result.kind === 'cart-detail') {
      expect(result.asin).toBe('B0CXXXXXXX');
      expect(result.step).toBe('30m');
    }
  });

  it('cart-attack-* で productId 不正時は cart-list fallback（Property 3）', () => {
    const result = resolveCartTapNavigation({ type: 'cart-attack-30m' });
    expect(result.kind).toBe('cart-list');
    if (result.kind === 'cart-list') {
      expect(result.reason).toBe('missing-product-id');
    }
  });

  it('calendar / admin は cart-list（呼出側で別経路）', () => {
    const result = resolveCartTapNavigation({ type: 'calendar' });
    expect(result.kind).toBe('cart-list');
  });
});

describe('Deep Link Round-trip (PBT-01)', () => {
  it('decode(encode(payload)) === payload（正常 ASIN + step）', () => {
    fc.assert(
      fc.property(
        fc
          .stringMatching(/^[A-Z0-9]{10}$/)
          .filter((s) => /^[A-Z0-9]{10}$/.test(s)),
        fc.constantFrom('30m', '6h', '24h'),
        (asin, step) => {
          const encoded = encodeDeepLink(asin, step as '30m' | '6h' | '24h');
          const decoded = decodeDeepLink(encoded);
          return (
            decoded !== null &&
            decoded.productId === asin &&
            decoded.step === step
          );
        },
      ),
      { numRuns: 30 },
    );
  });

  it('不正 URL は decode で null', () => {
    expect(decodeDeepLink('invalid')).toBeNull();
    expect(decodeDeepLink('https://example.com')).toBeNull();
    expect(decodeDeepLink('yudane://other')).toBeNull();
  });
});
