/**
 * MSW ハンドラ（契約テスト土台、api-contracts.md §7/§8）。
 *
 * OpenAPI の examples に対応するモックレスポンスを集約する。
 * Mobile の Integration / Contract テストはこのハンドラ群を使う。
 */

import { http, HttpResponse } from 'msw';

const BASE = 'http://localhost:4010';

export const handlers = [
  // GET /v1/health
  http.get(`${BASE}/v1/health`, () =>
    HttpResponse.json({
      status: 'healthy',
      checkedAt: '2026-05-30T00:00:00Z',
      dependencies: { dynamodb: 'ok', redis: 'ok' },
    }),
  ),

  // POST /v1/telemetry
  http.post(`${BASE}/v1/telemetry`, () =>
    HttpResponse.json({ accepted: 1, dropped: 0 }, { status: 202 }),
  ),

  // 認可エラーのサンプル（IDOR）
  http.get(`${BASE}/v1/users/:userId`, ({ params }) => {
    if (params.userId === 'forbidden') {
      return HttpResponse.json(
        {
          type: 'https://api.yudane.app/errors/auth.idor',
          title: 'このリソースにアクセスする権限がありません',
          status: 403,
        },
        { status: 403 },
      );
    }
    return HttpResponse.json({ id: params.userId, createdAt: '2026-05-30T00:00:00Z' });
  }),

  // POST/PATCH /v1/users/{userId}/profile（US-AUTH-01 オンボ段階保存）
  http.post(`${BASE}/v1/users/:userId/profile`, ({ params }) =>
    HttpResponse.json(
      { userId: params.userId, onboardingStep: 1, profileCompleted: false },
      { status: 201 },
    ),
  ),
  http.patch(`${BASE}/v1/users/:userId/profile`, ({ params }) =>
    HttpResponse.json({ userId: params.userId, onboardingStep: 5, profileCompleted: true }),
  ),

  // GET /v1/home（ホーム概況、Q6=A）
  http.get(`${BASE}/v1/home`, () =>
    HttpResponse.json({
      candidateCount: 12,
      cartWatchCount: 3,
      yudaneLevel: 5,
      remainingBudgetYen: 42_000,
    }),
  ),
];
