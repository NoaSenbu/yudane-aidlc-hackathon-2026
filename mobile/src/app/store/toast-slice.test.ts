import { describe, expect, it } from 'vitest';
import { create } from 'zustand';

import { createToastSlice, type ToastSlice } from './toast-slice';

describe('toast-slice', () => {
  it('showToast でトーストが追加される', () => {
    const useStore = create<ToastSlice>()((...a) => createToastSlice(...a));
    useStore.getState().showToast('今日もいい選択だったね', 'success');
    const { toasts } = useStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({ message: '今日もいい選択だったね', variant: 'success' });
  });

  it('dismissToast で指定 ID が消える', () => {
    const useStore = create<ToastSlice>()((...a) => createToastSlice(...a));
    useStore.getState().showToast('a');
    const id = useStore.getState().toasts[0]!.id;
    useStore.getState().dismissToast(id);
    expect(useStore.getState().toasts).toHaveLength(0);
  });

  it('variant 既定は info', () => {
    const useStore = create<ToastSlice>()((...a) => createToastSlice(...a));
    useStore.getState().showToast('hello');
    expect(useStore.getState().toasts[0]!.variant).toBe('info');
  });
});
