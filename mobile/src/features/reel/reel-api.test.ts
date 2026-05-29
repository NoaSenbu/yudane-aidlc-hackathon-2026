import { describe, expect, it, vi } from 'vitest';

import { fetchReel, recordAmazonTransition, type ReelApiClient } from './reel-api';
import type { AmazonTransitionRequest } from './types';

function fakeClient(returnValue: unknown): { client: ReelApiClient; calls: { path: string; init?: unknown }[] } {
  const calls: { path: string; init?: unknown }[] = [];
  const client: ReelApiClient = {
    apiFetch: vi.fn(async (path: string, init?: unknown) => {
      calls.push({ path, init });
      return returnValue as never;
    }),
  };
  return { client, calls };
}

describe('fetchReel', () => {
  it('カーソル・limit をクエリに乗せる', async () => {
    const { client, calls } = fakeClient({ cards: [], nextCursor: null, generatedAt: 'x' });
    await fetchReel(client, 'CURSOR1', 10);
    expect(calls[0]?.path).toBe('/v1/reel?cursor=CURSOR1&limit=10');
  });

  it('カーソルなしは素の /v1/reel', async () => {
    const { client, calls } = fakeClient({ cards: [], nextCursor: null, generatedAt: 'x' });
    await fetchReel(client);
    expect(calls[0]?.path).toBe('/v1/reel');
  });
});

describe('recordAmazonTransition', () => {
  it('POST で冪等キーを含む body を送る', async () => {
    const { client, calls } = fakeClient({ awarded: 1, totalExp: 42, duplicate: false });
    const req: AmazonTransitionRequest = {
      cardId: 'card-1',
      asin: 'B0EXAMPLE1',
      context: 'reel',
      clientTransitionId: 'ct_card-1_card-1',
    };
    const result = await recordAmazonTransition(client, req);
    expect(calls[0]?.path).toBe('/v1/amazon-transitions');
    expect((calls[0]?.init as { method: string }).method).toBe('POST');
    expect((calls[0]?.init as { body: AmazonTransitionRequest }).body.clientTransitionId).toBe(
      'ct_card-1_card-1',
    );
    expect(result.awarded).toBe(1);
  });
});
