# Unit-1 Platform — Code Summary: B-12 AuditLogger / authz（Step 8-9）

## 生成ファイル

| ファイル | 役割 |
|---|---|
| `backend/src/common/exceptions/domain_error.py` | DomainError 体系（ERR-01〜08）+ ProblemDetails 変換 |
| `backend/src/common/logging/sanitizer.py` | Allowlist Sanitizer（default-deny、PAT-SEC-02） |
| `backend/src/common/logging/audit_logger.py` | Powertools ラッパー（log/metric/trace、PAT-OBS-01/02） |
| `backend/src/common/authz/require_owner.py` | sub↔path userId 照合デコレータ（PAT-SEC-01 / IDOR） |
| `backend/conftest.py` | テストの sys.path 設定 |
| `backend/tests/common/test_sanitizer.py` | fail-safe invariant PBT + 冪等性 PBT |
| `backend/tests/common/test_require_owner.py` | 認証 / IDOR の単体テスト |
| `backend/tests/common/test_domain_error.py` | ProblemDetails 変換（internal 秘匿含む） |

## ルール準拠
- PII-01〜09（default-deny: 未分類キーは必ず full-mask、message 二次マスク、出力直前 1 回）
- ERR-01〜08（カテゴリ+コード 2 階層、type URL 化、internal は detail 秘匿 SECURITY-09）
- SECURITY-08（require_owner で sub 照合、fail-closed）/ SECURITY-15（グローバルエラー基盤）
- NFR-PBT-04（「未分類キーは必ずマスク」invariant を hypothesis で検証）
- NFR-COV-03（目標 95%/90%）

## 注記
AuditLogger は aws-lambda-powertools 依存のため、テスト実行は Build and Test ステージ（poetry install 後）。

## 次ステップ
Step 10-11: B-14 TelemetryIngestion / Health
