# Unit-1 Platform — Code Summary: B-14 TelemetryIngestion / Health（Step 10-11）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `backend/src/telemetry/ingestion.py` | 既知イベント filter（TEL-01）コアロジック |
| `backend/src/telemetry/handler.py` | POST /v1/telemetry ハンドラ（require_owner + Pydantic 検証 + EMF） |
| `backend/src/common/health/handler.py` | GET /v1/health（依存浅い疎通、PAT-RESIL-04） |
| `backend/tests/telemetry/test_ingestion.py` | accepted/dropped + idempotency |
| `backend/tests/common/test_health.py` | healthy/degraded/例外集約 |

## ルール準拠
- SECURITY-05（Pydantic 入力検証）/ SECURITY-08（require_owner）/ TEL-01/06（既知イベントのみ集計）
- NFR-AVAIL-01（ヘルスチェック）/ Q6=B（フォールバックは持たず可視化のみ）
- PBT-04 相当（filter_known_events は純関数で idempotent）

## 注記
S3 Data Lake 書き込みは Infrastructure（boto3）依存のため Build and Test / 実装統合時に結線。本ステップは EMF 集計と結果返却まで。

## 次ステップ
Step 12-13: M-12 ApiClient + PBT
