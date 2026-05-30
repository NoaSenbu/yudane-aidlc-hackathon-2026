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

  // GET /v1/cart-watch-items（監視リスト一覧、R8.1）
  http.get(`${BASE}/v1/cart-watch-items`, () =>
    HttpResponse.json({
      items: [
        { itemId: 'cw-01', asin: 'B0MSWCARD1', status: 'watching',          productMeta: { title: 'Sony WF-1000XM6',          priceYen: 24800 }, createdAt: '2026-05-29T10:00:00Z', updatedAt: '2026-05-29T10:00:00Z' },
        { itemId: 'cw-02', asin: 'B0MSWCARD2', status: 'notified-24h',      productMeta: { title: 'COMOLI バンドカラーシャツ', priceYen: 24200 }, createdAt: '2026-05-28T18:00:00Z', updatedAt: '2026-05-29T08:00:00Z' },
        { itemId: 'cw-03', asin: 'B0MSWCARD3', status: 'notified-6h',       productMeta: { title: 'Le Labo Santal 33',         priceYen: 24500 }, createdAt: '2026-05-29T06:00:00Z', updatedAt: '2026-05-29T12:00:00Z' },
        { itemId: 'cw-04', asin: 'B0CRTWTCH4', status: 'watching_orphaned', productMeta: { title: 'HHKB Professional HYBRID',  priceYen: 32800 }, createdAt: '2026-05-24T10:00:00Z', updatedAt: '2026-05-24T10:00:00Z' },
        { itemId: 'cw-05', asin: 'B0CRTWTCH5', status: 'watching',          productMeta: { title: '@aroma Brain Sleep ピロー', priceYen:  7200 }, createdAt: '2026-05-29T08:00:00Z', updatedAt: '2026-05-29T08:00:00Z' },
      ],
    }),
  ),

  // DELETE /v1/cart-watch-items/{asin}（監視解除 204、R8.4）
  http.delete(`${BASE}/v1/cart-watch-items/:asin`, () =>
    new HttpResponse(null, { status: 204 }),
  ),
];
