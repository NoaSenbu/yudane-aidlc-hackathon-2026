/**
 * useReelFeed: リールフィードのカーソルページング（M-03、TanStack useInfiniteQuery）。
 *
 * サーバー I/O は reel-api（fetchReel）に委譲。ApiClient は呼び出し側から渡す。
 * Outside-In TDD: ロジック（fetchReel / getNextPageParam）は reel-api.test.ts でカバー。
 */

import { useInfiniteQuery } from '@tanstack/react-query';

import { fetchReel, type ReelApiClient } from './reel-api';
import type { ReelPage } from './types';

/** リールフィードのクエリキー。 */
export const REEL_FEED_QUERY_KEY = ['reel', 'feed'] as const;

/**
 * リールフィードを無限スクロールで取得するフック。
 *
 * @param client - ApiClient（M-12）。
 * @param limit - 1 ページ件数。
 * @returns TanStack useInfiniteQuery の結果（pages: ReelPage[]）。
 */
export function useReelFeed(client: ReelApiClient, limit?: number) {
  return useInfiniteQuery({
    queryKey: REEL_FEED_QUERY_KEY,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }: { pageParam: string | undefined }): Promise<ReelPage> =>
      fetchReel(client, pageParam, limit),
    getNextPageParam: (lastPage: ReelPage): string | undefined => lastPage.nextCursor ?? undefined,
  });
}
