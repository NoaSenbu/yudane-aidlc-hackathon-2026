# Unit-1 Platform — Code Generation 総括

> Unit-1 Platform のコード生成（Step 1〜20）の全体サマリ。
> 確定方針: FD（Q1=refinedA/Q2/Q3/Q4=refinedA/Q5/Q6/Q7=A）/ NFR-Req（Q1/Q2/Q3=B/Q4/Q5/Q6=B/Q7=A）/ NFR-Design（Q1〜Q4=A）/ Infra（Q1〜Q7=A）

## 生成物の全体像（ワークスペース直下）

### shared/（横断共通、TS + Python）
- `schema/` — OpenAPI 3.1 骨格（全 UC パス + 共通コンポーネント）+ 生成型 + Prism/型生成スクリプト
- `asin-extractor/` — S-01（TS + Python + golden fixtures + PBT）
- `safeguard-policy/` — S-03（TS + Python + invariant/idempotency PBT）
- `telemetry-contracts/` — S-04（allowlist / PII 分類 / メトリクス命名）

### mobile/（React Native + TypeScript）
- `src/features/platform/api-client/` — M-12（interceptor チェーン / retry / refresh / error map + PBT）
- `src/features/platform/telemetry/` — M-13（バッファ + 退避 + round-trip PBT）
- `src/features/platform/app-shell/` — M-01（ナビ/Auth ゲート/deeplink 純粋ロジック + テスト）
- `src/app/`（theme / store / providers）— テーマトークン / GlobalToast / QueryClient
- `src/test/msw-handlers.ts` — 契約テスト土台

### backend/（Python 3.13 Lambda）
- `src/common/exceptions/` — DomainError 体系 + ProblemDetails 変換
- `src/common/logging/` — B-12 AuditLogger（Powertools ラッパー）+ Allowlist Sanitizer
- `src/common/authz/` — require_owner（IDOR 対策）
- `src/common/health/` — ヘルスチェック
- `src/common/models/api.py` — 生成 Pydantic モデル
- `src/telemetry/` — B-14 TelemetryIngestion
- `tests/` — sanitizer fail-safe PBT / require_owner / domain_error / ingestion / health

### infra/（AWS CDK v2）
- `lib/platform-stack.ts` — VPC / Cognito / KMS / S3 / Redis / SNS / SSM 出力
- `bin/app.ts` — env 切替 + cdk-nag
- `test/platform-stack.test.ts` — CDK assertions + cdk-nag

### ルート / CI
- `package.json`（npm workspaces）/ `tsconfig.base.json` / `eslint.config.mjs` / `.prettierrc` / `vitest.config.ts`
- `.github/workflows/ci.yml` — frontend / backend / infra / SBOM の 4 ジョブ
- `scripts/check-pii-fields.sh` — CalendarEvent への PII 混入検出

### docs
- `aidlc-docs/construction/shared-infrastructure.md` — 全 Unit 継承の共通インフラ規約
- `aidlc-docs/construction/unit-1-platform/code/*.md` — 各ステップのサマリ

## Extension コンプライアンス（実装段階）
- SECURITY-01/02/03/05/06/07/08/09/11/13/14/15: platform-stack / AuditLogger / require_owner / sanitizer / DomainError で実装
- SECURITY-10: CI に SBOM ジョブ / SECURITY-12: User Pool MFA REQUIRED 土台（フローは Unit-2）
- PBT-02（ASIN/Telemetry round-trip）/ PBT-03（Safeguard invariant）/ PBT-04（idempotency）/ PBT-08（seed 固定）/ PBT-10（example 併存）

## スコープ外（後続ステージ / Unit）
- テスト実行・カバレッジ計測・型生成の実行・cdk synth/deploy → Build and Test ステージ
- API Gateway の OpenAPI 詳細結線 / Lambda 統合 → 実装統合
- OpenSearch Serverless → Unit-4 着手時に platform-stack へ追加
- B-01 AuthEdgeLambda / MFA フロー → Unit-2

## 検証メモ
- 全コードは規約（tech-typescript / tech-python / tech-cdk / api-contracts）に準拠
- ネットワーク制約により依存インストール・テスト実行・型生成は未実行（Build and Test ステージで実施）
- Markdown / コードの静的整合は確認済み
