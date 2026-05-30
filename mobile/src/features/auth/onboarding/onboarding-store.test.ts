import { describe, expect, it } from 'vitest';
import fc from 'fast-check';
import { create } from 'zustand';

import { createOnboardingSlice, nextStep, type OnboardingSlice } from './onboarding-store';

describe('nextStep（PAT2-ONB-01 冪等）', () => {
  it('前進する', () => {
    expect(nextStep(1, 2)).toBe(2);
  });

  it('後退しない', () => {
    expect(nextStep(3, 1)).toBe(3);
  });

  it('PBT: 結果は常に max（current, next）', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 5 }),
        fc.integer({ min: 0, max: 5 }),
        (current, next) => nextStep(current, next) === Math.max(current, next),
      ),
      { seed: 20260529 },
    );
  });
});

describe('onboarding-store', () => {
  it('setDraft でドラフトをマージ', () => {
    const useStore = create<OnboardingSlice>()((...a) => createOnboardingSlice(...a));
    useStore.getState().setDraft({ monthlyDisposableYen: 100_000 });
    useStore.getState().setDraft({ hasDebt: false });
    expect(useStore.getState().draft).toEqual({ monthlyDisposableYen: 100_000, hasDebt: false });
  });

  it('advanceStep は後退しない', () => {
    const useStore = create<OnboardingSlice>()((...a) => createOnboardingSlice(...a));
    useStore.getState().advanceStep(3);
    useStore.getState().advanceStep(1);
    expect(useStore.getState().step).toBe(3);
  });

  it('resetOnboarding で初期化', () => {
    const useStore = create<OnboardingSlice>()((...a) => createOnboardingSlice(...a));
    useStore.getState().setDraft({ hasDebt: true });
    useStore.getState().advanceStep(4);
    useStore.getState().resetOnboarding();
    expect(useStore.getState().step).toBe(0);
    expect(useStore.getState().draft).toEqual({});
  });
});
