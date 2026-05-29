# backend

YUDANE バックエンド（Python 3.13 Lambda 群、Poetry 管理）。

## Unit-1 Platform が提供するもの

- `src/common/logging/` — B-12 AuditLogger（Powertools ラッパー + Allowlist Sanitizer）
- `src/common/exceptions/` — DomainError 体系（ERR-01〜08）
- `src/common/authz/` — `require_owner` デコレータ（IDOR 対策、SECURITY-08）
- `src/common/health/` — ヘルスチェック Lambda（GET /v1/health）
- `src/telemetry/` — B-14 TelemetryIngestionService（POST /v1/telemetry）
- `src/common/models/api.py` — OpenAPI 由来の生成モデル（手動編集禁止）

各 Unit は `src/<unit>/` に自身の Lambda を追加する。

## コマンド

```bash
poetry install
poetry run pytest          # Hypothesis PBT を含む
poetry run ruff check .
poetry run mypy --strict src
```
