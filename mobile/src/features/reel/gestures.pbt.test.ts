import fc from 'fast-check';
import { describe, it } from 'vitest';

import { DOUBLE_TAP_MS, LEFT_SWIPE_COOLDOWN_COUNT, SWIPE_THRESHOLD_PX, resolveGesture } from './gestures';

describe('resolveGesture（PBT invariant）', () => {
  it('ダブルタップ（<=350ms）は必ず show-transition-overlay（オーバーレイ必須）', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: DOUBLE_TAP_MS }), (interval) => {
        return (
          resolveGesture({ gesture: 'double-tap', tapIntervalMs: interval }) ===
          'show-transition-overlay'
        );
      }),
      { seed: 20260530 },
    );
  });

  it('左スワイプ 3 回超は debateDisabled に関わらず cooldown-blocked', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: LEFT_SWIPE_COOLDOWN_COUNT + 1, max: 100 }),
        fc.boolean(),
        (count, disabled) =>
          resolveGesture({
            gesture: 'swipe-left',
            dx: -(SWIPE_THRESHOLD_PX + 10),
            leftSwipeCount: count,
            debateDisabled: disabled,
          }) === 'cooldown-blocked',
      ),
      { seed: 20260530 },
    );
  });

  it('閾値未満の水平スワイプは必ず next-card', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('swipe-left', 'swipe-right') as fc.Arbitrary<'swipe-left' | 'swipe-right'>,
        fc.integer({ min: 0, max: SWIPE_THRESHOLD_PX - 1 }),
        (gesture, mag) =>
          resolveGesture({ gesture, dx: gesture === 'swipe-left' ? -mag : mag }) === 'next-card',
      ),
      { seed: 20260530 },
    );
  });
});
