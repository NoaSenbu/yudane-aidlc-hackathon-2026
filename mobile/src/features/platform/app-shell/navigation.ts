/**
 * M-01 AppShell のナビゲーション・ロジック（frontend-components.md §2）。
 *
 * UI（React Navigation）から分離した純粋ロジック。状態遷移・deeplink 解決をテスト可能にする。
 */

/** 画面識別子。 */
export type Screen = 'home' | 'reel' | 'debate' | 'cart' | 'report' | 'safeguard';

/** 認証状態。 */
export type AuthStatus = 'unknown' | 'authenticated' | 'unauthenticated';

/** ディープリンクの解決先。 */
export interface DeepLinkTarget {
  screen: Screen;
  params?: Record<string, string>;
  source: 'push' | 'share' | 'url';
}

const KNOWN_SCREENS: ReadonlySet<Screen> = new Set([
  'home',
  'reel',
  'debate',
  'cart',
  'report',
  'safeguard',
]);

/**
 * プッシュ通知ペイロードを DeepLinkTarget に解決する（frontend-components.md §2.4）。
 *
 * @param payload - 通知ペイロード（type と任意の itemId）
 * @returns 解決先。未知 type は home にフォールバック
 */
export function resolvePushTarget(payload: {
  type: string;
  itemId?: string;
}): DeepLinkTarget {
  switch (payload.type) {
    case 'cart-attack':
      return {
        screen: 'cart',
        source: 'push',
        ...(payload.itemId ? { params: { itemId: payload.itemId } } : {}),
      };
    case 'calendar':
      return { screen: 'home', source: 'push' };
    default:
      // admin / 未知は home（フォールバック）
      return { screen: 'home', source: 'push' };
  }
}

/**
 * URL スキームの deeplink を解決する。`yudane://<screen>?k=v` 形式を想定。
 *
 * @param url - アプリスキーム URL
 * @returns 解決先。解決不能なら home にフォールバック
 */
export function resolveUrlTarget(url: string): DeepLinkTarget {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname as Screen;
    if (KNOWN_SCREENS.has(host)) {
      const params: Record<string, string> = {};
      parsed.searchParams.forEach((v, k) => {
        params[k] = v;
      });
      return {
        screen: host,
        source: 'url',
        ...(Object.keys(params).length > 0 ? { params } : {}),
      };
    }
  } catch {
    // パース失敗 → フォールバック
  }
  return { screen: 'home', source: 'url' };
}

/**
 * 認証状態とディープリンクから、実際に遷移すべき画面を決める。
 *
 * 未認証時の deeplink は保留（pending）し、null を返す（認証後に解決）。
 *
 * @param authStatus - 現在の認証状態
 * @param target - 解決済みディープリンク（なければ null）
 * @returns 遷移先 screen。保留する場合は { pending: target }
 */
export function decideNavigation(
  authStatus: AuthStatus,
  target: DeepLinkTarget | null,
): { screen: Screen } | { pending: DeepLinkTarget } | { screen: 'home' } {
  if (authStatus !== 'authenticated') {
    // 未認証で deeplink が来たら保留（frontend-components.md §2.4）
    if (target) {
      return { pending: target };
    }
    return { screen: 'home' };
  }
  if (target) {
    return { screen: target.screen };
  }
  return { screen: 'home' };
}
