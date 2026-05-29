/**
 * M-08 ShareExtensionNativeModule — TypeScript Bridge ロジック層。
 *
 * iOS Share Extension（Swift）/ Android Intent Filter（Kotlin）の Native コードは
 * 実機統合時に Member D が iOS / Android 開発環境で着手する（v2/v3 確定方針）。
 * 本 Code Generation ではインターフェース型 + 純粋ロジック関数のみ提供。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.2 / Q1=A
 * iOS App Group: group.jp.amazon.yudane.share
 * Android Intent Filter: ACTION_SEND + text/plain
 */

/** Share Extension が受信した URL イベント。 */
export interface AsinExtractedEvent {
  /** Share Extension で受信した Amazon URL。 */
  url: string;
  /** Native 側で記録した受信時刻（ISO 8601）。 */
  receivedAt: string;
}

/** Native Module の Adapter インターフェース（実装は実機統合時）。 */
export interface ShareExtensionAdapter {
  /** イベントリスナーを登録する。 */
  addListener(eventName: string, handler: (event: AsinExtractedEvent) => void): { remove: () => void };
  /** 起動時に App Group / 共有 storage から保留中の URL を取り出す。 */
  consumePendingUrl(): Promise<AsinExtractedEvent | null>;
}

/** EventEmitter のスタブ生成（テスト用）。 */
export function createShareExtensionEventEmitter(): ShareExtensionAdapter {
  const listeners = new Map<string, Set<(event: AsinExtractedEvent) => void>>();
  return {
    addListener(eventName, handler) {
      let set = listeners.get(eventName);
      if (!set) {
        set = new Set();
        listeners.set(eventName, set);
      }
      set.add(handler);
      return {
        remove: () => {
          set?.delete(handler);
        },
      };
    },
    async consumePendingUrl() {
      // 実装は Native 側で App Group UserDefaults を読む
      return null;
    },
  };
}

/**
 * 起動時 / フォアグラウンド復帰時に保留中の URL をすべて消費する。
 *
 * @param adapter - ShareExtensionAdapter（テスト注入用）
 * @param onUrl - URL ごとに呼ばれるハンドラ
 */
export async function consumePendingUrls(
  adapter: ShareExtensionAdapter,
  onUrl: (event: AsinExtractedEvent) => Promise<void>,
): Promise<void> {
  let pending = await adapter.consumePendingUrl();
  while (pending) {
    await onUrl(pending);
    pending = await adapter.consumePendingUrl();
  }
}
