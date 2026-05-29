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

  // GET /v1/reel（Unit-4、examples/reel.yaml と整合）
  http.get(`${BASE}/v1/reel`, () =>
    HttpResponse.json({
      cards: [
        {
          cardId: 'card-01J9ABC',
          product: {
            asin: 'B0EXAMPLE1',
            title: 'ワイヤレスノイズキャンセリングイヤホン',
            priceYen: 32800,
            imageUrl: 'https://example.invalid/img/earbuds.jpg',
            reviewSummary: '静寂性が高評価',
          },
          pitch: '今日の会議6本、よく戦った。ご褒美は当然じゃね？',
          ownershipLabel: { text: '確保しておきました', rationale: '先週よく見てたやつ', source: 'llm' },
          tags: ['頑張ったあなたへ'],
          origin: 'late-night-boost',
          isHighPriceBoost: true,
        },
      ],
      nextCursor: null,
      generatedAt: '2026-05-30T13:00:00Z',
    }),
  ),

  // POST /v1/amazon-transitions（Unit-4）
  http.post(`${BASE}/v1/amazon-transitions`, () =>
    HttpResponse.json({ awarded: 1, totalExp: 42, duplicate: false }, { status: 201 }),
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
