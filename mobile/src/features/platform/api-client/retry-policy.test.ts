import { describe, expect, it } from 'vitest';
import fc from 'fast-check';

import { backoffDelayMs, shouldRetry } from './retry-policy';
import { RETRY_MAX_ATTEMPTS } from './types';

describe('shouldRetry（example-based）', () => {
  it('GET の 503 はリトライ', () => {
    expect(shouldRetry({ method: 'GET', status: 503, attempt: 0, explicitRetry: false })).toBe(
      true,
    );
  });

  it('POST はリトライしない（非冪等）', () => {
    expect(shouldRetry({ method: 'POST', status: 503, attempt: 0, explicitRetry: false })).toBe(
      false,
    );
  });

  it('GET でも 400 はリトライしない', () => {
    expect(shouldRetry({ method: 'GET', status: 400, attempt: 0, explicitRetry: false })).toBe(
      false,
    );
  });

  it('ネットワーク断（status なし）の GET はリトライ', () => {
    expect(
      shouldRetry({ method: 'GET', status: undefined, attempt: 0, explicitRetry: false }),
    ).toBe(true);
  });

  it('explicitRetry なら POST でもリトライ', () => {
    expect(shouldRetry({ method: 'POST', status: 503, attempt: 0, explicitRetry: true })).toBe(
      true,
    );
  });
});

describe('shouldRetry（PBT invariant）', () => {
  it('試行回数が上限以上なら必ず false（RETRY-03）', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('GET', 'POST', 'PATCH', 'DELETE'),
        fc.option(fc.constantFrom(429, 503, 500, 400), { nil: undefined }),
        fc.integer({ min: RETRY_MAX_ATTEMPTS, max: 100 }),
        fc.boolean(),
        (method, status, attempt, explicitRetry) =>
          shouldRetry({ method, status, attempt, explicitRetry }) === false,
      ),
      { seed: 20260529 },
    );
  });

  it('非冪等メソッド + explicitRetry=false は必ず false', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('POST', 'PATCH', 'DELETE', 'PUT'),
        fc.option(fc.constantFrom(429, 503), { nil: undefined }),
        fc.integer({ min: 0, max: RETRY_MAX_ATTEMPTS - 1 }),
        (method, status, attempt) =>
          shouldRetry({ method, status, attempt, explicitRetry: false }) === false,
      ),
      { seed: 20260529 },
    );
  });
});

describe('backoffDelayMs', () => {
  it('指数的に増加する（jitter 込みでも下限は単調）', () => {
    const d0 = backoffDelayMs(0, 300, 0);
    const d1 = backoffDelayMs(1, 300, 0);
    const d2 = backoffDelayMs(2, 300, 0);
    expect(d0).toBe(300);
    expect(d1).toBe(600);
    expect(d2).toBe(1_200);
  });

  it('jitter は base 指数値以上に加算される', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 5 }), (attempt) => {
        const base = 300 * 2 ** attempt;
        const d = backoffDelayMs(attempt, 300, 100);
        return d >= base && d <= base + 100;
      }),
      { seed: 20260529 },
    );
  });
});
