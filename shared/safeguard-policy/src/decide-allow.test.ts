import { describe, expect, it } from 'vitest';
import fc from 'fast-check';

import { WARN_THRESHOLD_RATIO } from './constants';
import { decideAllow, type SafeguardInput } from './decide-allow';

/** 既定フラグ（全 false）。 */
const noFlags = { cooldownOn: false, quietWeek: false, hasDebt: false };

/** SafeguardInput を生成する arbitrary。 */
const inputArb: fc.Arbitrary<SafeguardInput> = fc.record({
  transitionCountMonth: fc.integer({ min: 0, max: 100 }),
  monthlyLimitYen: fc.integer({ min: 1_000, max: 1_000_000 }),
  currentBudgetUsedYen: fc.integer({ min: 0, max: 2_000_000 }),
  flags: fc.record({
    cooldownOn: fc.boolean(),
    quietWeek: fc.boolean(),
    hasDebt: fc.boolean(),
  }),
});

describe('decideAllow（example-based、PBT-10 併存）', () => {
  it('cooldownOn は最優先で block', () => {
    const r = decideAllow({
      transitionCountMonth: 0,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 0,
      flags: { ...noFlags, cooldownOn: true },
    });
    expect(r).toMatchObject({ decision: 'block', reasonCode: 'safeguard.cooldown' });
  });

  it('quietWeek も block', () => {
    const r = decideAllow({
      transitionCountMonth: 0,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 0,
      flags: { ...noFlags, quietWeek: true },
    });
    expect(r).toMatchObject({ decision: 'block', reasonCode: 'safeguard.quiet-week' });
  });

  it('上限超過で block（通常）', () => {
    const r = decideAllow({
      transitionCountMonth: 5,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 100_000,
      flags: noFlags,
    });
    expect(r).toMatchObject({ decision: 'block', reasonCode: 'safeguard.monthly-limit-exceeded' });
  });

  it('負債者は実効上限が半減し debt-restricted', () => {
    const r = decideAllow({
      transitionCountMonth: 5,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 60_000,
      flags: { ...noFlags, hasDebt: true },
    });
    // 実効上限 = 100000 * (0.35/0.7) = 50000、使用 60000 で超過
    expect(r.effectiveLimitYen).toBe(50_000);
    expect(r).toMatchObject({ decision: 'block', reasonCode: 'safeguard.debt-restricted' });
  });

  it('80% 超で warn（遷移は止めない）', () => {
    const r = decideAllow({
      transitionCountMonth: 3,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 85_000,
      flags: noFlags,
    });
    expect(r).toMatchObject({ decision: 'warn', reasonCode: 'safeguard.near-limit' });
  });

  it('余裕があれば allow', () => {
    const r = decideAllow({
      transitionCountMonth: 1,
      monthlyLimitYen: 100_000,
      currentBudgetUsedYen: 10_000,
      flags: noFlags,
    });
    expect(r).toMatchObject({ decision: 'allow', reasonCode: 'allowed' });
  });
});

describe('decideAllow（PBT-03 invariant）', () => {
  it('remainingYen は常に 0 以上', () => {
    fc.assert(
      fc.property(inputArb, (input) => decideAllow(input).remainingYen >= 0),
      { seed: 20260529 },
    );
  });

  it('実効上限は月間上限を超えない（負債者は必ず下がる）', () => {
    fc.assert(
      fc.property(inputArb, (input) => {
        const r = decideAllow(input);
        return r.effectiveLimitYen <= input.monthlyLimitYen;
      }),
      { seed: 20260529 },
    );
  });

  it('cooldown/quietWeek が立っていれば必ず block（最優先）', () => {
    fc.assert(
      fc.property(inputArb, (input) => {
        if (input.flags.cooldownOn || input.flags.quietWeek) {
          return decideAllow(input).decision === 'block';
        }
        return true;
      }),
      { seed: 20260529 },
    );
  });

  it('PBT-04 idempotency: 同一入力は同一結果（純関数）', () => {
    fc.assert(
      fc.property(inputArb, (input) => {
        const a = decideAllow(input);
        const b = decideAllow(input);
        return JSON.stringify(a) === JSON.stringify(b);
      }),
      { seed: 20260529 },
    );
  });

  it('フラグなしで上限未満かつ 80% 未満なら allow', () => {
    fc.assert(
      fc.property(inputArb, (input) => {
        const noFlag = { cooldownOn: false, quietWeek: false, hasDebt: false };
        const i = { ...input, flags: noFlag };
        const r = decideAllow(i);
        if (i.currentBudgetUsedYen < i.monthlyLimitYen * WARN_THRESHOLD_RATIO) {
          return r.decision === 'allow';
        }
        return true;
      }),
      { seed: 20260529 },
    );
  });
});
