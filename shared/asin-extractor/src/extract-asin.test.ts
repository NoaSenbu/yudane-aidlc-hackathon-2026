import { describe, expect, it } from 'vitest';
import fc from 'fast-check';

import { extractAsin, isValidAsin } from './extract-asin';

/** 有効な ASIN を生成する arbitrary（10 桁英数字、大文字）。 */
const asinArb = fc
  .stringMatching(/^[A-Z0-9]{10}$/)
  .filter((s) => s.length === 10);

describe('isValidAsin', () => {
  it('10 桁英数字を有効と判定する', () => {
    expect(isValidAsin('B0CABCDE12')).toBe(true);
  });

  it('長さ違い・小文字・記号を無効と判定する', () => {
    expect(isValidAsin('B0CABCDE1')).toBe(false);
    expect(isValidAsin('b0cabcde12')).toBe(false);
    expect(isValidAsin('B0CABCDE-2')).toBe(false);
  });
});

describe('extractAsin（example-based、PBT-10 併存）', () => {
  it('/dp/ASIN を抽出する', () => {
    const r = extractAsin('https://www.amazon.co.jp/dp/B0CABCDE12');
    expect(r).toMatchObject({ ok: true, asin: 'B0CABCDE12', source: 'path-dp' });
  });

  it('/gp/product/ASIN を抽出する', () => {
    const r = extractAsin('https://www.amazon.co.jp/gp/product/B0CABCDE12?ref=x');
    expect(r).toMatchObject({ ok: true, source: 'path-gp-product' });
  });

  it('/gp/aw/d/ASIN を抽出する', () => {
    const r = extractAsin('https://www.amazon.com/gp/aw/d/B0CABCDE12');
    expect(r).toMatchObject({ ok: true, source: 'path-gp-aw' });
  });

  it('クエリ ?asin= を抽出する', () => {
    const r = extractAsin('https://www.amazon.co.jp/some/path?asin=B0CABCDE12');
    expect(r).toMatchObject({ ok: true, source: 'query-asin' });
  });

  it('小文字 ASIN を大文字へ正規化する', () => {
    const r = extractAsin('https://www.amazon.co.jp/dp/b0cabcde12');
    expect(r).toMatchObject({ ok: true, asin: 'B0CABCDE12' });
  });

  it('許可外ホストは unsupported-host', () => {
    const r = extractAsin('https://example.com/dp/B0CABCDE12');
    expect(r).toMatchObject({ ok: false, reason: 'unsupported-host' });
  });

  it('短縮 URL は no-match（展開は呼び出し側、ASIN-05）', () => {
    const r = extractAsin('https://amzn.to/abcd');
    expect(r).toMatchObject({ ok: false, reason: 'no-match' });
  });

  it('パース不能な入力は no-match', () => {
    const r = extractAsin('not a url');
    expect(r).toMatchObject({ ok: false, reason: 'no-match' });
  });
});

describe('extractAsin（PBT-02 round-trip）', () => {
  it('任意の有効 ASIN を含む /dp/ URL から元の ASIN を復元する', () => {
    fc.assert(
      fc.property(asinArb, (asin) => {
        const url = `https://www.amazon.co.jp/dp/${asin}`;
        const r = extractAsin(url);
        return r.ok && r.asin === asin;
      }),
      { seed: 20260529 },
    );
  });

  it('末尾スラッシュ・追加クエリの有無で結果が変わらない（正規化の安定性）', () => {
    fc.assert(
      fc.property(asinArb, fc.boolean(), fc.boolean(), (asin, slash, query) => {
        const base = `https://www.amazon.co.jp/dp/${asin}`;
        const url = `${base}${slash ? '/' : ''}${query ? '?ref=abc' : ''}`;
        const r = extractAsin(url);
        return r.ok && r.asin === asin;
      }),
      { seed: 20260529 },
    );
  });
});
