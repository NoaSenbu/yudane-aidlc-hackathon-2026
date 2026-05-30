/**
 * M-08 share intake hook — Share 受信 → ASIN 抽出 → Backend 登録の純粋ロジック層。
 *
 * AsinResult 判別ユニオン（business-rules.md ASIN-06）を尊重し、
 * `result.ok` で分岐する（Issue B1 対応）。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.2
 */

import { extractAsin, type AsinResult } from '@yudane/asin-extractor';

import type { AsinExtractedEvent } from './share-extension-module';

/** Toast 表示インターフェース（実機 UI 結線時に注入）。 */
export interface ToastAdapter {
  show(message: string): void;
}

/** Share intake hook の依存（実装の純粋関数を testable に）。 */
export interface UseShareIntakeDeps {
  toast: ToastAdapter;
  onAsinExtracted: (params: { url: string; asin: string }) => Promise<void> | void;
}

/**
 * Share Extension からの URL イベントを処理する純粋ロジック。
 *
 * @param event - Share Extension が受信した URL イベント
 * @param deps - 依存（Toast / Backend 登録ハンドラ）
 */
export async function handleShareEvent(
  event: AsinExtractedEvent,
  deps: UseShareIntakeDeps,
): Promise<void> {
  const result: AsinResult = extractAsin(event.url);
  if (!result.ok) {
    // US-03-01 AC-5: Amazon URL 形式以外は登録しない
    deps.toast.show('商品として認識できなかったよ');
    return;
  }
  // Mobile 側で即時 ASIN 表示（Q2=A 反映、UX レイテンシ最小化）
  await deps.onAsinExtracted({ url: event.url, asin: result.asin });
}

/**
 * UI 結線用 hook ラッパ（実機統合時に React Native の useEffect で結線）。
 *
 * v3 注: 本実装は @tanstack/react-query / react-native の依存追加待ちで純粋関数のみ提供。
 * 実機統合時は M-08 の addListener / AppState change と handleShareEvent を結線する。
 */
export function useShareIntake(): {
  /** Share イベントが起きたときに呼ぶエントリポイント（純粋関数で結線可）。 */
  handleEvent: (event: AsinExtractedEvent, deps: UseShareIntakeDeps) => Promise<void>;
} {
  return { handleEvent: handleShareEvent };
}
