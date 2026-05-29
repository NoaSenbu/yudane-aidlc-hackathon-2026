/**
 * GlobalToast slice（frontend-components.md §5）。横断トーストの共通土台。
 *
 * 肯定フィードバック（M-2「今日もいい選択だったね」等）の中身は各 Unit が出すが、
 * トースト基盤は Unit-1 が提供する。Zustand の StateCreator として実装。
 */

import type { StateCreator } from 'zustand';

/** トーストの種別。 */
export type ToastVariant = 'info' | 'success' | 'warning' | 'danger';

/** トースト 1 件。 */
export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
}

/** Toast slice の状態とアクション。 */
export interface ToastSlice {
  toasts: Toast[];
  showToast: (message: string, variant?: ToastVariant) => void;
  dismissToast: (id: string) => void;
}

let toastSeq = 0;

/** Toast slice 生成器。ルートストアに合成する。 */
export const createToastSlice: StateCreator<ToastSlice, [], [], ToastSlice> = (set) => ({
  toasts: [],
  showToast: (message, variant = 'info') => {
    toastSeq += 1;
    const toast: Toast = { id: `toast-${toastSeq}`, message, variant };
    set((state) => ({ toasts: [...state.toasts, toast] }));
  },
  dismissToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },
});
