/** Unit-4 Reel feature の公開エクスポート（M-03）。 */

export {
  DEBATE_TRIGGER,
  DOUBLE_TAP_MS,
  LEFT_SWIPE_COOLDOWN_COUNT,
  POST_TAP_REDIRECT_MS,
  SWIPE_THRESHOLD_PX,
  resolveGesture,
  type GestureAction,
  type GestureInput,
  type ReelGesture,
} from './gestures';
export { BOOST_NUDGE_IDLE_MS, shouldNudge, type BoostNudgeInput } from './boost-nudge';
export { makeClientTransitionId } from './client-transition-id';
export { fetchReel, recordAmazonTransition, type ReelApiClient } from './reel-api';
export { useReelFeed, REEL_FEED_QUERY_KEY } from './use-reel-feed';
export { useAmazonRedirect } from './use-amazon-redirect';
export { ReelScreen, type ReelScreenProps } from './reel-screen';
export type {
  AmazonTransitionRequest,
  ExpAward,
  OwnershipLabel,
  ProductMeta,
  ReelCard,
  ReelPage,
} from './types';
