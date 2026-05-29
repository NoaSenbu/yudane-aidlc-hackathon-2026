/**
 * S-01 AsinExtractor — Amazon URL から ASIN を抽出・検証する。
 *
 * 設計: business-logic-model.md ALG-ASIN / business-rules.md ASIN-01〜07。
 * 失敗は例外でなく結果型（AsinResult）で表現する（Q3=A）。
 */

/** ASIN の抽出元パターン。 */
export type AsinSource =
  | 'path-dp'
  | 'path-gp-product'
  | 'path-gp-aw'
  | 'query-asin'
  | 'short-url';

/** ASIN 抽出の結果型。 */
export type AsinResult =
  | { ok: true; asin: string; source: AsinSource; normalizedFrom: string }
  | {
      ok: false;
      reason: 'no-match' | 'invalid-checksum-format' | 'unsupported-host';
      input: string;
    };

/** 許可するホスト（amazon 各国ドメイン + 短縮）。 */
const ALLOWED_AMAZON_HOST = /(^|\.)amazon\.[a-z.]+$/;
const SHORT_HOSTS = new Set(['amzn.to', 'amzn.asia']);

/** ASIN らしき文字列（10 桁英数字）。 */
const ASIN_PATTERN = /^[A-Z0-9]{10}$/;

/** パス抽出ルール（優先順位順、ASIN-04）。 */
const PATH_RULES: ReadonlyArray<{ source: AsinSource; re: RegExp }> = [
  { source: 'path-dp', re: /\/dp\/([A-Za-z0-9]{10})(?:[/?]|$)/ },
  { source: 'path-gp-product', re: /\/gp\/product\/([A-Za-z0-9]{10})(?:[/?]|$)/ },
  { source: 'path-gp-aw', re: /\/gp\/aw\/d\/([A-Za-z0-9]{10})(?:[/?]|$)/ },
];

/**
 * ASIN が有効な形式かを判定する（ASIN-01）。
 *
 * @param asin - 判定対象（大文字正規化済みを想定）
 * @returns 10 桁英数字なら true
 */
export function isValidAsin(asin: string): boolean {
  return ASIN_PATTERN.test(asin);
}

/**
 * Amazon URL から ASIN を抽出する。
 *
 * dp / gp-product / gp-aw / クエリ asin の順でマッチし、最初に見つかったものを
 * 大文字正規化して返す。短縮 URL（amzn.to / amzn.asia）は展開を呼び出し側に委ね、
 * source='short-url' のフラグのみ返す（ASIN-05）。
 *
 * @param url - Amazon 共有 URL
 * @returns 抽出結果（AsinResult）
 */
export function extractAsin(url: string): AsinResult {
  const trimmed = url.trim();
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return { ok: false, reason: 'no-match', input: url };
  }

  const host = parsed.hostname.toLowerCase();

  // 短縮 URL は実展開を呼び出し側へ（ここでは検知のみ）
  if (SHORT_HOSTS.has(host)) {
    return { ok: false, reason: 'no-match', input: url };
  }

  if (!ALLOWED_AMAZON_HOST.test(host)) {
    return { ok: false, reason: 'unsupported-host', input: url };
  }

  // パスパターンを優先順位順に評価
  for (const rule of PATH_RULES) {
    const m = rule.re.exec(parsed.pathname);
    if (m && m[1]) {
      return finalize(m[1], rule.source, url);
    }
  }

  // クエリ ?asin=
  const queryAsin = parsed.searchParams.get('asin');
  if (queryAsin) {
    return finalize(queryAsin, 'query-asin', url);
  }

  return { ok: false, reason: 'no-match', input: url };
}

/**
 * 抽出した候補を正規化・検証して結果化する（ASIN-02）。
 */
function finalize(candidate: string, source: AsinSource, original: string): AsinResult {
  const asin = candidate.toUpperCase();
  if (!isValidAsin(asin)) {
    return { ok: false, reason: 'invalid-checksum-format', input: original };
  }
  return { ok: true, asin, source, normalizedFrom: original };
}
