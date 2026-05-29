# Unit-1 Platform — Code Summary: S-01 AsinExtractor（Step 3-4）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `shared/asin-extractor/package.json` | TS パッケージ（vitest + fast-check） |
| `shared/asin-extractor/tsconfig.json` | base 継承 |
| `shared/asin-extractor/src/extract-asin.ts` | ALG-ASIN 実装（AsinResult 結果型） |
| `shared/asin-extractor/src/index.ts` | export 制御 |
| `shared/asin-extractor/src/extract-asin.test.ts` | example + fast-check round-trip PBT |
| `shared/asin-extractor/python/asin_extractor.py` | Python 同等実装 |
| `shared/asin-extractor/python/test_asin_extractor.py` | pytest + hypothesis |
| `shared/asin-extractor/fixtures/golden-cases.json` | クロス言語一致 fixtures |

## ルール準拠
- ASIN-01〜07（10桁正規化 / 優先順位 dp>gp-product>gp-aw>query / 短縮は呼び出し側展開 / 結果型 / クロス言語一致）
- NFR-PBT-01（round-trip PBT-02 + 冪等正規化）、example-based 併存（PBT-10）、seed 固定（PBT-08）
- NFR-COV-01（目標 Line 95%+ / Branch 90%+、実行は Build and Test）

## 次ステップ
Step 5-6: S-03 SafeguardPolicy 実装 + PBT
