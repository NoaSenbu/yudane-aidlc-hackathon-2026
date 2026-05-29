# Unit-1 Platform — Code Summary: S-04 TelemetryContracts（Step 7）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `shared/telemetry-contracts/package.json` / `tsconfig.json` | TS パッケージ |
| `shared/telemetry-contracts/src/index.ts` | allowlist / PII / メトリクス命名 / イベントカタログ / classifyField |
| `shared/telemetry-contracts/src/index.test.ts` | classify / 命名 / カタログの単体テスト |
| `shared/telemetry-contracts/python/telemetry_contracts.py` | Python 同等実装 |

## ルール準拠
- PII-01〜09（default-deny: 未登録キーは unclassified → full-mask、PII は allowlist より優先）
- TEL-01（イベントカタログ照合）/ NFR-OBS-02（メトリクス命名 `<unit>.<domain>.<metric>`、Q3=B: Unit-1 は雛形のみ）
- B-12 sanitizer（Step 8）がこの分類を参照して fail-safe マスクを実施

## 次ステップ
Step 8-9: B-12 AuditLogger / sanitizer / require_owner + PBT
