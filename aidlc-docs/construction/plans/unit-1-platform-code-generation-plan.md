# Unit-1 Platform — Code Generation Plan

> **このプランは Code Generation の Single Source of Truth**。Part 2 ではこのステップ順に従ってコードを生成し、各ステップ完了時に [x] を付ける。
> 参照: [Functional Design](../unit-1-platform/functional-design/) / [NFR Design](../unit-1-platform/nfr-design/) / [Infrastructure Design](../unit-1-platform/infrastructure-design/) / [shared-infrastructure.md](../shared-infrastructure.md) / steering（tech-typescript / tech-python / tech-cdk / api-contracts）
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Code Generation Part 1（計画）

---

## 0. Unit-1 のコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | 全 7 Unit の開発・デプロイを可能にする横断基盤の提供 |
| 担当 | Member A |
| ストーリー | なし（基盤 Unit。全 Unit の前提） |
| 依存 | なし（最上流） |
| 提供インターフェース | OpenAPI 骨格 / 生成型 / 共通ライブラリ（S-01〜S-04, B-12）/ ApiClient / Telemetry / platform-stack |
| プロジェクト種別 | Greenfield モノレポ（mobile / backend / infra / shared） |
| ワークスペースルート | リポジトリ直下（aidlc-docs/ には絶対に置かない） |

### Unit-1 が生成するコンポーネント
| ID | コンポーネント | 配置 |
|---|---|---|
| S-02 | SchemaRegistry（OpenAPI 骨格 + 型生成） | `shared/schema/` |
| S-01 | AsinExtractor（TS + Python） | `shared/asin-extractor/` |
| S-03 | SafeguardPolicy（TS + Python） | `shared/safeguard-policy/` |
| S-04 | TelemetryContracts（allowlist / メトリクス命名 / PII 分類） | `shared/telemetry-contracts/` |
| M-12 | ApiClient（interceptor チェーン） | `mobile/src/features/platform/api-client/` |
| M-13 | Telemetry（バッファ + 退避） | `mobile/src/features/platform/telemetry/` |
| M-01 | AppShell（ナビ殻 / Auth ゲート / deeplink） | `mobile/src/features/platform/app-shell/` |
| B-12 | AuditLogger（Powertools ラッパー + sanitizer） | `backend/src/common/` |
| B-14 | TelemetryIngestionService | `backend/src/telemetry/` |
| Health | ヘルスチェック Lambda | `backend/src/common/health/` |
| Infra | platform-stack（CDK） | `infra/lib/platform-stack.ts` |

> **MVP スコープ方針（NFR Q7=A）**: 本 Code Generation では「コードと単体/PBT テストの生成」までを行う。テスト実行とデプロイは Build and Test ステージ。OpenSearch は Unit-4 着手時に platform-stack へ追加（本 Unit では Redis まで）。

---

## 1. コード生成ステップ（Part 2 で順次実行）

### Step 1: モノレポ構造セットアップ（Greenfield）
- [x] ルート `package.json`（npm workspaces: mobile / shared/*）、`.gitignore` 追記、`.editorconfig`
- [x] ルート共通設定: `tsconfig.base.json`（strict + noUncheckedIndexedAccess 等）、`.eslintrc.cjs`、`.prettierrc`
- [x] `backend/pyproject.toml`（Poetry、ruff/mypy strict 設定、Python 3.13）
- [x] ディレクトリ雛形（mobile / backend / infra / shared）+ 各 `README.md`（スタブ）
- ドキュメント: `aidlc-docs/construction/unit-1-platform/code/structure-setup.md`

### Step 2: Shared / API 契約（S-02 SchemaRegistry）— OpenAPI 骨格凍結
- [x] `shared/schema/openapi.yaml`（エントリ、$ref 集約）
- [x] `shared/schema/components/responses/problem-details.yaml`（RFC 7807）+ 共通 parameters（CorrelationId / pagination）
- [x] `shared/schema/components/schemas/`（共通 DTO 最小: User / ProblemDetails / TelemetryEnvelope / HealthStatus / CalendarEvent（x-pii 例））
- [x] `shared/schema/paths/`（全 UC のパス骨格 = URL + メソッドのみ。auth/debate/reel/cart/calendar/safeguard/report/telemetry/health）
- [x] 型生成スクリプト: `shared/schema/package.json`（`schema:gen:ts` = openapi-typescript）、`backend/scripts/gen_models.py`（datamodel-code-generator）
- [x] 生成実行 → `shared/schema/types/api.ts` / `backend/src/common/models/api.py`（ヘッダコメント付き）
- ストーリー: なし（基盤） / 規約: api-contracts §2/§3/§4/§10、Q1=refinedA
- ドキュメント: `code/schema-summary.md`

### Step 3: Shared / S-01 AsinExtractor（業務ロジック）
- [x] TS: `shared/asin-extractor/src/extract-asin.ts`（ALG-ASIN: dp/gp-product/gp-aw/query、短縮検知、正規化、AsinResult）
- [x] TS: `index.ts`（export 制御）
- [x] Python: `shared/asin-extractor/python/asin_extractor.py`（同等シグネチャ）
- ルール: ASIN-01〜07

### Step 4: S-01 単体 + PBT テスト
- [x] TS: `shared/asin-extractor/src/extract-asin.test.ts`（example-based + fast-check round-trip PBT-02 + 冪等正規化）
- [x] Python: `shared/asin-extractor/python/test_asin_extractor.py`（pytest + hypothesis）
- [x] golden fixtures（TS/Python クロス言語一致、ASIN-07）
- NFR: NFR-PBT-01 / NFR-COV-01（95%/90%）
- ドキュメント: `code/asin-extractor-summary.md`

### Step 5: Shared / S-03 SafeguardPolicy（業務ロジック）
- [x] TS: `shared/safeguard-policy/src/constants.ts` + `decide-allow.ts`（ALG-SG 段階判定、純関数）
- [x] Python: `shared/safeguard-policy/python/safeguard_policy.py`（同等）
- ルール: SG-01〜10 / 定数表

### Step 6: S-03 単体 + PBT テスト
- [x] TS: `decide-allow.test.ts`（example + fast-check invariant: remaining>=0 / 実効上限<=上限、idempotency PBT-04）
- [x] Python: `test_safeguard_policy.py`
- [x] golden fixtures（クロス言語一致）※ example/PBT で同値を網羅
- NFR: NFR-PBT-02 / NFR-COV-02（95%/90%）
- ドキュメント: `code/safeguard-policy-summary.md`

### Step 7: Shared / S-04 TelemetryContracts
- [x] TS: `shared/telemetry-contracts/src/`（allowlist フィールド / メトリクス命名規約 `<unit>.<domain>.<metric>` / PII 分類 / イベント名カタログ雛形 / TelemetryEvent・Envelope 型）
- [x] Python: `shared/telemetry-contracts/python/telemetry_contracts.py`（同等）
- ルール: TEL-01〜09 / PII-01〜09 / NFR-OBS（Q3=B）
- ドキュメント: `code/telemetry-contracts-summary.md`

### Step 8: Backend / B-12 AuditLogger（共通ライブラリ）
- [x] `backend/src/common/logging/audit_logger.py`（Powertools Logger ラッパー、log/metric/trace）
- [x] `backend/src/common/logging/sanitizer.py`（Allowlist Sanitizer = default-deny、PAT-SEC-02）
- [x] `backend/src/common/exceptions/`（DomainError 体系、ERR-01〜08）
- [x] `backend/src/common/authz/require_owner.py`（sub↔path userId 照合デコレータ、PAT-SEC-01）
- ルール: PII-01〜09 / ERR-01〜08 / SECURITY-03/08/09/15

### Step 9: B-12 単体 + PBT テスト
- [x] `backend/tests/common/test_sanitizer.py`（hypothesis invariant: 未分類キーは必ずマスク、NFR-PBT-04）
- [x] `backend/tests/common/test_audit_logger.py` / `test_require_owner.py`（require_owner + domain_error を実装）
- NFR: NFR-COV-03（95%/90%）
- ドキュメント: `code/audit-logger-summary.md`

### Step 10: Backend / B-14 TelemetryIngestion + Health（API 層）
- [x] `backend/src/telemetry/handler.py`（POST /v1/telemetry、ingest_events、sub 照合 → EMF put → S3 書き込み、ALG-TEL サーバー側）
- [x] `backend/src/common/health/handler.py`（GET /v1/health、DynamoDB/Redis 浅い疎通、PAT-RESIL-04）
- [x] Pydantic 入力検証（SECURITY-05）
- ルール: TEL-06/07 / AVAIL-01

### Step 11: B-14 / Health 単体テスト
- [x] `backend/tests/telemetry/test_ingestion.py`（example + 二重送信 idempotency）
- [x] `backend/tests/common/test_health.py`
- ドキュメント: `code/telemetry-ingestion-summary.md`

### Step 12: Mobile / M-12 ApiClient（API 層 + interceptor）
- [x] `mobile/src/features/platform/api-client/`（apiFetch + interceptor チェーン: auth/correlation/timeout/retry/refresh/errorMap、LC-01）
- [x] RequestPolicy（REST/SSE 2 系統タイムアウト、PAT-PERF-01）
- [x] ProblemDetails → DomainError マッピング（ALG-MAP）
- ルール: REQ-01〜05 / RETRY-01〜06 / NFR-PERF-01/02/06

### Step 13: M-12 単体 + PBT テスト
- [x] `api-client/*.test.ts`（vitest + モック fetch、リトライ回数上限 invariant、401 single-shot refresh、fast-check）
- ドキュメント: `code/api-client-summary.md`

### Step 14: Mobile / M-13 Telemetry（クライアント側）
- [x] `mobile/src/features/platform/telemetry/`（track/flush、InMemoryQueue + AsyncStorage 退避、ALG-TEL クライアント側、PAT-PERF-02/RESIL-03）
- ルール: TEL-01〜05 / NFR-PERF-04/05

### Step 15: M-13 単体 + PBT テスト
- [x] `telemetry/*.test.ts`（vitest、Envelope round-trip PBT-02、退避上限破棄、flush トリガー）
- NFR: NFR-PBT-03 / NFR-COV-05（85%）
- ドキュメント: `code/telemetry-client-summary.md`

### Step 16: Mobile / M-01 AppShell + 状態管理土台（Frontend Components）
- [x] `mobile/src/features/platform/app-shell/`（ナビ殻 / AuthGate / DeepLinkHandler、frontend-components.md。純粋ロジックとして実装、UI 結線は実機統合時）
- [x] `mobile/src/app/providers/` `mobile/src/app/store/`（QueryClient retry=false / Zustand toast slice / GlobalToast）
- [x] テーマトークン（Indigo/cold rose/cyan、WCAG AA、NFR-A11Y-01）
- ルール: frontend-components §1/§2/§5/§7

### Step 17: M-01 単体テスト
- [x] `app-shell/*.test.ts` / `store/*.test.ts`（Auth ゲート状態遷移、deeplink ルーティング、pending deeplink 保留、toast）
- NFR: NFR-COV-06（80%/70%）
- ドキュメント: `code/app-shell-summary.md`

### Step 18: Infra / platform-stack（デプロイアーティファクト）
- [x] `infra/`（CDK プロジェクト: package.json / cdk.json / tsconfig / bin/app.ts、env=dev|prd context）
- [x] `infra/lib/platform-stack.ts`（VPC 2AZ/3層 + Endpoint / Cognito UserPool / KMS / S3 / ElastiCache Redis / SSM 公開 / SNS / Lambda SG）
- [x] cdk-nag AwsSolutionsChecks 適用 + 必要な Suppression（理由コメント）
- ルール: tech-cdk §3/§4/§7 / shared-infrastructure / SECURITY-01/02/06/07/09/14
- 注記: API GW + Authorizer / B-12 Layer / B-14 / Health Lambda 結線は実装統合（OpenAPI 連携）で確定。OpenSearch は Unit-4 着手時

### Step 19: platform-stack スナップショットテスト
- [x] `infra/test/platform-stack.test.ts`（vitest CDK assertions + cdk-nag アサート）
- ドキュメント: `code/platform-stack-summary.md`

### Step 20: ドキュメント + CI 雛形 + 仕上げ
- [x] ルート `README.md` 更新（モノレポ構成 / 各ディレクトリの起動コマンド導線）
- [x] `.github/workflows/ci.yml`（lint / typecheck / test / cdk synth + nag / SBOM、SECURITY-10）+ `scripts/check-pii-fields.sh`
- [x] `mobile/src/test/msw-handlers.ts`（OpenAPI examples ベース、契約テスト土台）+ ルート `vitest.config.ts`
- [x] Unit-1 コード総括: `code/unit-1-code-summary.md`
- [x] aidlc-state.md / 本プランのチェックボックス最終更新

---

## 2. ストーリートレーサビリティ

Unit-1 は基盤 Unit のため主担当ストーリーなし。ただし以下を**全 Unit の前提**として提供:
- OpenAPI 骨格凍結 → 全 US の API 契約土台（Q1=refinedA）
- ApiClient / Telemetry / AuditLogger → 全 US の横断インフラ
- SafeguardPolicy → US-SAFE-01〜04 / US-01-05 / US-03-05 の判定基盤
- AsinExtractor → US-03-01〜（カート介入）の ASIN 抽出基盤

## 3. 依存・インターフェース

- **依存**: なし（最上流）
- **下流提供**: SSM パラメータ（shared-infrastructure.md §1）、生成型、共有ライブラリ、Lambda Layer
- **AuthModule（M-11）連携**: ApiClient の refresh は M-11 のインターフェースを前提（実体は Unit-2）。本 Unit ではインターフェース型のみ定義しスタブ参照

## 4. 完了基準
- [x] Step 1〜20 すべて [x]
- [x] コードと単体/PBT テストが生成済み（実行は Build and Test ステージ）
- [x] OpenAPI 骨格が凍結され型生成済み
- [x] platform-stack が cdk synth 可能な状態（デプロイは承認後）
- [x] 生成ドキュメントが `aidlc-docs/construction/unit-1-platform/code/` に揃う

## 5. スコープ外（後続）
- テスト実行・カバレッジ計測・cdk deploy → Build and Test ステージ
- OpenSearch Serverless → Unit-4 着手時に platform-stack へ追加
- prd 環境の冗長化（NAT/Redis レプリカ）→ 決勝前
- B-01 AuthEdgeLambda / MFA フロー → Unit-2
