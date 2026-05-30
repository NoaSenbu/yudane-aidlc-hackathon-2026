/**
 * Special Link ビルダー — Amazon Associates Special Link URL を構築する純関数群（R6）。
 */

export class SpecialLinkValidationError extends Error {
  constructor(
    public readonly kind: 'invalid-asin' | 'missing-tag',
    message: string,
  ) {
    super(message);
    this.name = 'SpecialLinkValidationError';
  }
}

/** ASIN が半角英数字 10 文字（^[A-Z0-9]{10}$）か検証する。 */
export function isValidAsin(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Z0-9]{10}$/.test(value);
}

/**
 * Amazon Associates Special Link URL を構築する（R6.1, R6.3）。
 * @throws SpecialLinkValidationError - ASIN 不正 / タグ空
 */
export function buildSpecialLink(asin: string, trackingTag: string): string {
  if (!isValidAsin(asin)) {
    throw new SpecialLinkValidationError(
      'invalid-asin',
      `ASIN "${String(asin)}" は半角英数字10文字ではありません`,
    );
  }
  if (!trackingTag || trackingTag.trim().length === 0) {
    throw new SpecialLinkValidationError('missing-tag', 'トラッキングタグが設定されていません');
  }
  return `https://www.amazon.co.jp/dp/${asin}?tag=${encodeURIComponent(trackingTag)}`;
}

/**
 * Special Link URL から ASIN を再抽出する（R6.2 round-trip 検証用）。
 * @returns 抽出した ASIN。抽出不能なら null
 */
export function extractAsin(url: string): string | null {
  const match = /\/dp\/([A-Z0-9]{10})(?:[/?]|$)/.exec(url);
  return match?.[1] ?? null;
}
