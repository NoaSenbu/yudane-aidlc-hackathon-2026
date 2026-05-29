import fc from 'fast-check';
import { describe, it } from 'vitest';

import { BOOST_NUDGE_IDLE_MS, shouldNudge } from './boost-nudge';

describe('shouldNudge（PBT invariant）', () => {
  it('インタラクション済みなら idle に関わらず必ず false', () => {
    fc.assert(
      fc.property(fc.boolean(), fc.integer({ min: 0, max: 60_000 }), (boost, idle) =>
        shouldNudge({ isHighPriceBoost: boost, idleMs: idle, interacted: true }) === false,
      ),
      { seed: 20260530 },
    );
  });

  it('非ブースト枠なら必ず false', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 60_000 }), fc.boolean(), (idle, interacted) =>
        shouldNudge({ isHighPriceBoost: false, idleMs: idle, interacted }) === false,
      ),
      { seed: 20260530 },
    );
  });

  it('ブースト枠・未操作なら idle>=閾値 と発火が一致', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 60_000 }), (idle) =>
        shouldNudge({ isHighPriceBoost: true, idleMs: idle, interacted: false }) ===
        (idle >= BOOST_NUDGE_IDLE_MS),
      ),
      { seed: 20260530 },
    );
  });
});
