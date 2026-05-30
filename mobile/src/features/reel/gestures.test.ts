import { describe, expect, it } from 'vitest';

import { resolveGesture } from './gestures';

describe('resolveGesture（example-based）', () => {
  it('ダブルタップ（350ms 以内）は必ず確認オーバーレイ（FR-REEL-05）', () => {
    expect(resolveGesture({ gesture: 'double-tap', tapIntervalMs: 200 })).toBe(
      'show-transition-overlay',
    );
  });

  it('ダブルタップが遅すぎる（>350ms）は次カード扱い', () => {
    expect(resolveGesture({ gesture: 'double-tap', tapIntervalMs: 500 })).toBe('next-card');
  });

  it('左スワイプ 60px 以上 → 論破遷移', () => {
    expect(resolveGesture({ gesture: 'swipe-left', dx: -80 })).toBe('navigate-debate');
  });

  it('左スワイプ 60px 未満 → 次カード（誤操作扱い）', () => {
    expect(resolveGesture({ gesture: 'swipe-left', dx: -30 })).toBe('next-card');
  });

  it('論破不要 ON の左スワイプ → スキップトースト（US-02-03 AC-3）', () => {
    expect(resolveGesture({ gesture: 'swipe-left', dx: -80, debateDisabled: true })).toBe(
      'skip-toast',
    );
  });

  it('同一カード左スワイプ 3 回超 → クールダウン（US-02-03 AC-4）', () => {
    expect(resolveGesture({ gesture: 'swipe-left', dx: -80, leftSwipeCount: 4 })).toBe(
      'cooldown-blocked',
    );
  });

  it('右スワイプ 60px 以上 → カート監視登録（US-02-04）', () => {
    expect(resolveGesture({ gesture: 'swipe-right', dx: 80 })).toBe('register-cart-watch');
  });

  it('縦スクロールは次カード', () => {
    expect(resolveGesture({ gesture: 'vertical-scroll' })).toBe('next-card');
  });
});
