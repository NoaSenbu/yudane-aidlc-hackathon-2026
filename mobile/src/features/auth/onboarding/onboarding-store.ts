/**
 * オンボーディングのクライアント状態（PAT2-ONB-01、Zustand slice）。
 *
 * サーバー権威の step を反映しつつ、ドラフトを端末保持する。段階保存の冪等性
 * （step は後退しない）を純ロジックで保証する。
 */

import type { StateCreator } from 'zustand';

/** オンボのドラフト（5 項目）。 */
export interface OnboardingDraft {
  monthlyDisposableYen?: number;
  monthlySavingsYen?: number;
  favoriteBrands?: string[];
  ngCategories?: string[];
  hasDebt?: boolean;
  associatesDisclosureAcknowledged?: boolean;
}

/** オンボ slice。 */
export interface OnboardingSlice {
  step: number;
  draft: OnboardingDraft;
  setDraft: (patch: Partial<OnboardingDraft>) => void;
  advanceStep: (next: number) => void;
  resetOnboarding: () => void;
}

/**
 * step を冪等に前進させる純関数（後退しない）。
 *
 * @param current - 現在 step
 * @param next - 遷移先 step
 * @returns max(current, next)
 */
export function nextStep(current: number, next: number): number {
  return Math.max(current, next);
}

/** オンボ slice 生成器。 */
export const createOnboardingSlice: StateCreator<OnboardingSlice, [], [], OnboardingSlice> = (
  set,
) => ({
  step: 0,
  draft: {},
  setDraft: (patch) => set((state) => ({ draft: { ...state.draft, ...patch } })),
  advanceStep: (next) => set((state) => ({ step: nextStep(state.step, next) })),
  resetOnboarding: () => set({ step: 0, draft: {} }),
});
