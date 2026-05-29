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
];
