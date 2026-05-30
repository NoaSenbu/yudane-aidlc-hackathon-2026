/** Unit-4 Reel の Mobile 型（M-03）。OpenAPI 生成型に対応する最小ビュー型。 */

/** 商品メタ。 */
export interface ProductMeta {
  asin: string;
  title: string;
  priceYen: number;
  imageUrl: string;
  reviewSummary?: string;
}

/** 所有感ラベル（US-02-05）。 */
export interface OwnershipLabel {
  text: string;
  rationale: string;
  source: 'llm' | 'template-fallback';
}

/** リールカード。 */
export interface ReelCard {
  cardId: string;
  product: ProductMeta;
  pitch: string;
  ownershipLabel: OwnershipLabel;
  tags: string[];
  origin:
    | 'purchase-related'
    | 'co-purchase'
    | 'late-night-boost'
    | 'calendar'
    | 'onboarding-seed'
    | 'curated-popular';
  isHighPriceBoost: boolean;
}

/** リールページ（カーソルページング）。 */
export interface ReelPage {
  cards: ReelCard[];
  nextCursor: string | null;
  generatedAt: string;
}

/** Amazon 遷移記録リクエスト。 */
export interface AmazonTransitionRequest {
  cardId: string;
  asin: string;
  context: 'reel' | 'debate-agree' | 'cart-attack';
  clientTransitionId: string;
}

/** EXP 加算結果。 */
export interface ExpAward {
  awarded: number;
  totalExp: number;
  duplicate: boolean;
}
