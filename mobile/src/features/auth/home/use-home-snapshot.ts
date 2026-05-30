/**
 * M-02 HomeScreen の概況スナップショット hook（ALG-HOME、Q6=A 概況のみ）。
 *
 * 候補件数 / 監視件数 / 委ね Lv / 残額を集約表示。詳細は Unit-8 DameReportScreen へ。
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import type { HomeSnapshot } from '@yudane/schema';

import { ApiClient } from '../../platform/api-client';

/**
 * ホーム概況を取得する hook を生成する。
 *
 * @param client - Unit-1 ApiClient
 * @returns TanStack Query の結果
 */
export function useHomeSnapshot(client: ApiClient): UseQueryResult<HomeSnapshot> {
  return useQuery({
    queryKey: ['home-snapshot'],
    queryFn: () => client.request<HomeSnapshot>('/v1/home'),
  });
}
