/**
 * M-09 PushNotificationHandler — TypeScript ロジック層（v2/v3 確定方針）。
 *
 * 本 Code Generation では expo-notifications 依存追加は対象外。代わりに
 * PushNotificationsAdapter インターフェース型を定義 + 純粋ロジック関数のみ生成。
 * 実体は実機統合時に Member D が結線する。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.3 / Q5=C / Q7=A
 */

/** Deep Link payload（functional-design.md §1.3、Property 3 productId 必須）。 */
export interface PushPayload {
  type: 'cart-attack-30m' | 'cart-attack-6h' | 'cart-attack-24h' | 'calendar' | 'admin';
  productId?: string; // cart-attack-* で必須（値は ASIN、Unit-3 契約整合）
  step?: '30m' | '6h' | '24h';
}

/** Notification Adapter（実体は実機統合時に expo-notifications で結線）。 */
export interface PushNotificationsAdapter {
  requestPermissionsAsync(): Promise<{ granted: boolean }>;
  getDevicePushTokenAsync(): Promise<{ data: string; type: 'APNS' | 'GCM' }>;
}

/** Push permission 状態。 */
export type PushPermissionState = 'granted' | 'denied' | 'undetermined';

/** Token rotation 結果。 */
export interface PushTokenRotation {
  token: string;
  platform: 'APNS' | 'GCM';
  rotatedAt: string;
}

/** 通知タップ時のナビゲーション先決定結果。 */
export type CartTapNavigation =
  | { kind: 'cart-detail'; asin: string; step: '30m' | '6h' | '24h' }
  | { kind: 'cart-list'; reason: 'invalid-payload' | 'missing-product-id' };

/**
 * Push payload を validate する（Property 3、productId 必須）。
 *
 * @param payload - 任意のオブジェクト
 * @returns valid な PushPayload か null
 */
export function validatePushPayload(payload: unknown): PushPayload | null {
  if (!payload || typeof payload !== 'object') return null;
  const obj = payload as Record<string, unknown>;
  const type = obj['type'];
  if (typeof type !== 'string') return null;
  const validTypes = ['cart-attack-30m', 'cart-attack-6h', 'cart-attack-24h', 'calendar', 'admin'];
  if (!validTypes.includes(type)) return null;

  const result: PushPayload = { type: type as PushPayload['type'] };
  if (typeof obj['productId'] === 'string') {
    result.productId = obj['productId'];
  }
  if (typeof obj['step'] === 'string' && ['30m', '6h', '24h'].includes(obj['step'])) {
    result.step = obj['step'] as '30m' | '6h' | '24h';
  }
  return result;
}

/**
 * 通知タップから Cart 関連のナビゲーション先を決定する純粋関数。
 *
 * Property 3: cart-attack-* で productId 不正時は CartInterceptScreen 一覧 fallback。
 *
 * @param payload - 通知 payload
 * @returns ナビゲーション先（純粋関数で結線可能）
 */
export function resolveCartTapNavigation(payload: PushPayload): CartTapNavigation {
  if (!payload.type.startsWith('cart-attack')) {
    // cart-attack-* 以外は本関数の対象外（呼出側で判定）
    return { kind: 'cart-list', reason: 'invalid-payload' };
  }
  if (!payload.productId) {
    // Property 3 不変条件違反 → 一覧 fallback
    return { kind: 'cart-list', reason: 'missing-product-id' };
  }
  // 詳細画面へ navigate
  return {
    kind: 'cart-detail',
    asin: payload.productId,
    step: payload.step ?? '30m',
  };
}

/** Deep Link URL を生成する（Backend と整合）。 */
export function encodeDeepLink(asin: string, step: '30m' | '6h' | '24h'): string {
  return `yudane://cart-attack/${asin}?step=${step}`;
}

/** Deep Link URL から PushPayload を生成する（PBT-01 Round-trip 対応）。 */
export function decodeDeepLink(url: string): PushPayload | null {
  try {
    // yudane://cart-attack/{asin}?step={step}
    const match = url.match(/^yudane:\/\/cart-attack\/([A-Z0-9]{10})\?step=(30m|6h|24h)$/);
    if (!match) return null;
    const [, asin, step] = match;
    return {
      type: `cart-attack-${step}` as PushPayload['type'],
      productId: asin,
      step: step as '30m' | '6h' | '24h',
    };
  } catch {
    return null;
  }
}
