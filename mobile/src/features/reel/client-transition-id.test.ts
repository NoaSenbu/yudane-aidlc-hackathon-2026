import fc from 'fast-check';
import { describe, expect, it } from 'vitest';

import { makeClientTransitionId } from './client-transition-id';

describe('makeClientTransitionId', () => {
  it('同一 cardId は同一 ID（既定: 1 カード 1 遷移、冪等）', () => {
    expect(makeClientTransitionId('card-1')).toBe(makeClientTransitionId('card-1'));
  });

  it('attemptKey を変えれば別 ID', () => {
    expect(makeClientTransitionId('card-1', 'a')).not.toBe(makeClientTransitionId('card-1', 'b'));
  });

  it('PBT: 同一入力は決定論的に同一 ID', () => {
    fc.assert(
      fc.property(fc.string(), fc.option(fc.string(), { nil: undefined }), (cardId, attempt) =>
        makeClientTransitionId(cardId, attempt) === makeClientTransitionId(cardId, attempt),
      ),
      { seed: 20260530 },
    );
  });
});
