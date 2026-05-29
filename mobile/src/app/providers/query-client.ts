/**
 * TanStack Query の QueryClient 既定設定（tech-stack-decisions §2 / NFR-AVAIL Q6=B）。
 *
 * retry=false でリトライを ApiClient（GET のみ）に一元化し、二重リトライを防ぐ。
 */

import { QueryClient } from '@tanstack/react-query';

/** YUDANE 共通の QueryClient を生成する。 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // リトライは ApiClient に一元化（二重リトライ防止）
        retry: false,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}
