import { describe, expect, it } from 'vitest';

import { shouldNudge } from './boost-nudge';

describe('shouldNudge（example-based）', () => {
  it('ブースト枠で 3 秒無操作 → 発火（US-02-01 AC-2）', () => {
    expect(shouldNudge({ isHighPriceBoost: true, idleMs: 3_000, interacted: false })).toBe(true);
  });

  it('ブースト枠でないなら発火しない', () => {
    expect(shouldNudge({ isHighPriceBoost: false, idleMs: 5_000, interacted: false })).toBe(false);
  });

  it('インタラクションがあれば発火しない', () => {
    expect(shouldNudge({ isHighPriceBoost: true, idleMs: 5_000, interacted: true })).toBe(false);
  });

  it('3 秒未満は発火しない', () => {
    expect(shouldNudge({ isHighPriceBoost: true, idleMs: 2_999, interacted: false })).toBe(false);
  });
});
