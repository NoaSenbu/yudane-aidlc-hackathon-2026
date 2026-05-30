import './global.css';

import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ApiClient } from './src/features/platform/api-client/api-client';
import { setApiClient } from './src/features/platform/api-client/api-fetch';
import { createQueryClient } from './src/app/providers/query-client';
import { MainTabs } from './src/navigation/MainTabs';

// ─── デモ用モック状態（モジュールレベル、リセットなし） ───────────────────────
let demoTotalExp = 24;
const dismissedAsins = new Set<string>();

const DEMO_CART_ITEMS = [
  { itemId: 'cw-01', asin: 'B0MSWCARD1', status: 'watching',          productMeta: { title: 'Sony WF-1000XM6',          priceYen: 24800 }, createdAt: '2026-05-29T10:00:00Z', updatedAt: '2026-05-29T10:00:00Z' },
  { itemId: 'cw-02', asin: 'B0MSWCARD2', status: 'notified-24h',      productMeta: { title: 'COMOLI バンドカラーシャツ', priceYen: 24200 }, createdAt: '2026-05-28T18:00:00Z', updatedAt: '2026-05-29T08:00:00Z' },
  { itemId: 'cw-03', asin: 'B0MSWCARD3', status: 'notified-6h',       productMeta: { title: 'Le Labo Santal 33',         priceYen: 24500 }, createdAt: '2026-05-29T06:00:00Z', updatedAt: '2026-05-29T12:00:00Z' },
  { itemId: 'cw-04', asin: 'B0CRTWTCH4', status: 'watching_orphaned', productMeta: { title: 'HHKB Professional HYBRID',  priceYen: 32800 }, createdAt: '2026-05-24T10:00:00Z', updatedAt: '2026-05-24T10:00:00Z' },
  { itemId: 'cw-05', asin: 'B0CRTWTCH5', status: 'watching',          productMeta: { title: '@aroma Brain Sleep ピロー', priceYen:  7200 }, createdAt: '2026-05-29T08:00:00Z', updatedAt: '2026-05-29T08:00:00Z' },
];

const DEMO_REEL_CARDS = [
  {
    cardId: 'card-demo-01',
    product: { asin: 'B0MSWCARD1', title: 'Sony WF-1000XM6', priceYen: 24800, imageUrl: '' },
    pitch: '会議6本の夜に。時給換算で 11時間分 なんですよ。これ買わない理由、なんかあります？',
    ownershipLabel: { text: '確保しておきました', rationale: '先週3回見てたやつ', source: 'llm' },
    tags: ['頑張ったあなたへ'],
    origin: 'late-night-boost',
    isHighPriceBoost: true,
  },
  {
    cardId: 'card-demo-02',
    product: { asin: 'B0MSWCARD2', title: 'COMOLI バンドカラーシャツ', priceYen: 24200, imageUrl: '' },
    pitch: '土曜のデートまであと3日。「また今度」、何度目ですか。',
    ownershipLabel: { text: '逃したら後悔します', rationale: '残り2点', source: 'llm' },
    tags: ['限定', 'デート'],
    origin: 'curated-popular',
    isHighPriceBoost: false,
  },
  {
    cardId: 'card-demo-03',
    product: { asin: 'B0MSWCARD3', title: 'Le Labo Santal 33', priceYen: 24500, imageUrl: '' },
    pitch: '深夜の労いに。毎晩0時以降に頑張ってる人が、自分を大事にする選択。',
    ownershipLabel: { text: 'ご用意しました', rationale: '深夜利用多数', source: 'template-fallback' },
    tags: ['深夜', '香り'],
    origin: 'late-night-boost',
    isHighPriceBoost: false,
  },
];

// ─── デモ用モック fetch ────────────────────────────────────────────────────────
function demoFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url =
    typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.href
        : (input as Request).url;
  const method = (init?.method ?? 'GET').toUpperCase();
  const jsonHeaders = { 'Content-Type': 'application/json' };

  return new Promise((resolve) =>
    setTimeout(() => {
      if (method === 'GET' && url.includes('/v1/home')) {
        resolve(
          new Response(
            JSON.stringify({
              candidateCount: DEMO_REEL_CARDS.length,
              cartWatchCount: DEMO_CART_ITEMS.filter((i) => !dismissedAsins.has(i.asin)).length,
              yudaneLevel: demoTotalExp,
              remainingBudgetYen: 38000,
            }),
            { status: 200, headers: jsonHeaders },
          ),
        );
      } else if (method === 'GET' && url.includes('/v1/reel')) {
        resolve(
          new Response(
            JSON.stringify({
              cards: DEMO_REEL_CARDS,
              nextCursor: null,
              generatedAt: new Date().toISOString(),
            }),
            { status: 200, headers: jsonHeaders },
          ),
        );
      } else if (method === 'POST' && url.includes('/v1/amazon-transitions')) {
        demoTotalExp += 1;
        resolve(
          new Response(
            JSON.stringify({ awarded: 1, totalExp: demoTotalExp, duplicate: false }),
            { status: 201, headers: jsonHeaders },
          ),
        );
      } else if (method === 'DELETE' && url.includes('/v1/cart-watch-items/')) {
        const asin = url.split('/v1/cart-watch-items/')[1]?.split('?')[0] ?? '';
        if (asin) dismissedAsins.add(asin);
        resolve(new Response(null, { status: 204 }));
      } else if (method === 'GET' && url.includes('/v1/cart-watch-items')) {
        const items = DEMO_CART_ITEMS.filter((i) => !dismissedAsins.has(i.asin));
        resolve(
          new Response(JSON.stringify({ items }), { status: 200, headers: jsonHeaders }),
        );
      } else {
        resolve(
          new Response(JSON.stringify({ error: 'not found' }), {
            status: 404,
            headers: jsonHeaders,
          }),
        );
      }
    }, 200),
  );
}

// ─── ApiClient（デモ用モック、auth は no-op） ────────────────────────────────
export const demoClient = new ApiClient({
  baseUrl: 'http://demo.local',
  auth: {
    getAccessToken: async () => 'demo-token',
    refresh: async () => true,
    onAuthExpired: () => {},
  },
  fetchImpl: demoFetch,
});

// apiFetch（useCartWatchItems / useCartDismiss 等）に同一クライアントを注入
setApiClient(demoClient);

const queryClient = createQueryClient();

export default function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <MainTabs client={demoClient} />
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
