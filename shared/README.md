# shared

YUDANE 横断共通モジュール（TypeScript / Python 両対応）。Unit-1 Platform が owner、他 Unit は利用のみ。

| ディレクトリ | コンポーネント | 内容 |
|---|---|---|
| `schema/` | S-02 SchemaRegistry | OpenAPI 3.1（SSOT）+ 型生成（TS / Python） |
| `asin-extractor/` | S-01 AsinExtractor | Amazon URL → ASIN 抽出（TS / Python） |
| `safeguard-policy/` | S-03 SafeguardPolicy | 月間上限 / 冷却 / 負債の判定（TS / Python） |
| `telemetry-contracts/` | S-04 TelemetryContracts | メトリクス命名 / イベント型 / PII 分類 |

TypeScript を正本とし、Python 型はコード生成 + golden fixtures でクロス言語一致を担保する。
