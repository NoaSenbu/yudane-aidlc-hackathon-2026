/**
 * Unit-5 Cart Intercept — Mobile features の export 集約。
 *
 * 本 Code Generation では純粋ロジック層のみ（Unit-1 M-01 AppShell スタンス継承）。
 * RN UI コンポーネント（CartInterceptScreen.tsx）は実機統合時に Member D が結線する。
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1
 */

export {
  type AsinExtractedEvent,
  type ShareExtensionAdapter,
  consumePendingUrls,
  createShareExtensionEventEmitter,
} from './share-extension-module';
export { useShareIntake } from './use-share-intake';
export { useCartIntake } from './use-cart-intake';
export { useCartDismiss } from './use-cart-dismiss';
export { useCartWatchItem } from './use-cart-watch-item';
export { useCartWatchItems } from './use-cart-watch-items';
export {
  ASSOCIATES_DISCLOSURE_TEXT,
  applyOptimisticDismiss,
  computeTimelineProgress,
  getAnimationConfig,
  rollbackOptimisticDismiss,
  shouldShowOrphanedWarning,
  type CartScreenMode,
  type TimelineProgress,
} from './cart-intercept-screen-state';
export {
  decodeDeepLink,
  encodeDeepLink,
  resolveCartTapNavigation,
  validatePushPayload,
  type CartTapNavigation,
  type PushNotificationsAdapter,
  type PushPayload,
} from './push-notification-handler';
