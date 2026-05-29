# Unit-1 Platform — Tech Stack Decisions

> Unit-1 Platform で実体化する技術選定の確定と根拠。要件書 §7 / tech.md を Unit-1 の横断基盤責務に落とし込む。
> 参照: [nfr-requirements.md](./nfr-requirements.md) / [要件書 §7](../../../inception/requirements/requirements.md) / [tech.md](../../../../.kiro/steering/tech.md)
> 確定方針: Q1=A / Q2=A / Q3=B / Q4=A / Q5=A / Q6=B / Q7=A

---

## 0. 前提

技術スタックの大枠は要件書 §7 / tech.md で確定済み（プロジェクト全体の決定）。本書は **Unit-1 が実際に導入・設定する具体ライブラリとバージョン方針** を確定する。新規の技術選定ではなく「確定済みスタックの Unit-1 における実体化」が主旨。

---

## 1. モノレポ基盤

| 項目 | 決定 | 根拠 |
|---|---|---|
| リポジトリ構造 | モノレポ（mobile / backend / infra / shared） | unit-of-work.md Q4=A |
| TS パッケージ管理 | npm workspaces | shared/ を mobile から import（components.md Shared 運用方針） |
| Python パッケージ管理 | Poetry（editable install で shared を参照） | tech.md §5、AGENTS.md §5 |
| ロックファイル | package-lock.json / poetry.lock / cdk.json を必ずコミット | tech.md §5 |
| Node ランタイム | Node.js 22 LTS | 要件書 §7（CDK / SDK v3 推奨） |
| Python ランタイム | Python 3.13 | 要件書 §7（Lambda GA） |

---

## 2. Mobile（M-01 / M-12 / M-13 が依存）

| レイヤ | ライブラリ | バージョン方針 | 用途 |
|---|---|---|---|
| フレームワーク | React Native (New Architecture) | 0.76+ | Fabric + TurboModules 前提 |
| 言語 | TypeScript | 5.x | strict 設定（tech-typescript.md） |
| AWS SDK | AWS SDK v3 | 最新安定 | 通信レイヤを明示管理 |
| 認証 | aws-amplify/auth（Auth モジュールのみ） | v6 | Cognito。`amazon-cognito-identity-js` 不採用 |
| サーバー状態 | TanStack Query | v5 系 | retry=false（リトライは ApiClient に一元化、NFR-AVAIL Q6=B 整合） |
| クライアント状態 | Zustand | 最新安定 | persist ミドルウェア（AsyncStorage） |
| 永続化 | @react-native-async-storage/async-storage | 最新安定 | テレメトリ退避キュー（Q6 / TEL-05） |
| PBT | fast-check | 最新安定 | NFR-PBT（PBT-09） |

### Unit-1 が確立する Mobile 規約
- ApiClient のタイムアウト 2 系統（NFR-PERF-01/02）を共通設定として提供、各 Unit が上書き可
- TanStack Query の `retry: false` を既定化し、リトライを ApiClient（GET のみ）に一元化（二重リトライ防止）
- Zustand は feature ごとに slice 分割する規約（frontend-components.md §5）

---

## 3. Backend（B-12 / B-14 が依存）

| レイヤ | ライブラリ | バージョン方針 | 用途 |
|---|---|---|---|
| ランタイム | Python | 3.13 | Lambda |
| 観測 | AWS Lambda Powertools (Python) | 最新安定 | Logger / Tracer / Metrics（EMF）。B-12 AuditLogger の土台 |
| バリデーション | Pydantic | v2 | 入力検証（SECURITY-05）、生成モデルの基盤 |
| 型生成 | datamodel-code-generator | 最新安定 | OpenAPI → Pydantic（api-contracts.md §3.2） |
| PBT | Hypothesis | 最新安定 | NFR-PBT（PBT-09） |
| AWS SDK | boto3 | 最新安定 | DynamoDB / S3 / CloudWatch 等 |

### Unit-1 が確立する Backend 規約
- B-12 AuditLogger は **Lambda Powertools をラップ**し、PII マスキング（default-deny）と相関 ID 伝搬を上乗せ（重複実装を避ける）
- EMF メトリクスは Powertools Metrics を使用。命名規約 `<unit>.<domain>.<metric>`（NFR-OBS-02）
- 全 Lambda は Powertools の `@logger.inject_lambda_context` / `@tracer.capture_lambda_handler` を必須化

---

## 4. Infra / IaC（Unit-1 が owner）

| 項目 | 決定 | 根拠 |
|---|---|---|
| IaC | AWS CDK (TypeScript, v2 系最新) | 要件書 §7、tech.md |
| Lint | cdk-nag | tech.md §6（品質ゲート） |
| スタック分割 | Unit ごとに分割。Unit-1 = platform-stack.ts | unit-of-work.md |
| platform-stack 範囲 | VPC / API Gateway / Cognito User Pool / DynamoDB 共通 / ElastiCache Redis / OpenSearch Serverless / IAM 基本 | unit-of-work.md Unit-1 範囲 |

> 具体的なスタック構成・リソース定義・IAM ポリシーは次の **Infrastructure Design** ステージで確定。本書はライブラリ・ツール選定のみ。

---

## 5. Shared / 契約（S-01〜S-04、Q1=refinedA）

| 項目 | ツール | 出力先 | 根拠 |
|---|---|---|---|
| API 契約 | OpenAPI 3.1 | shared/schema/openapi.yaml（物理分割） | api-contracts.md §10 |
| TS 型生成 | openapi-typescript | shared/schema/types/api.ts | api-contracts.md §3.1 |
| Python 型生成 | datamodel-code-generator | backend/src/common/models/api.py | api-contracts.md §3.2 |
| Mock Server | Prism (Stoplight) | localhost:4010 | api-contracts.md §7（並行開発） |
| 契約テスト（Backend） | Schemathesis | CI | api-contracts.md §8 |
| 契約テスト（Mobile） | MSW (Mock Service Worker) | mobile/src/test/msw-handlers.ts | api-contracts.md §7/§8 |
| PII フィールド検査 | check-pii-fields.sh（拡張） | CI | Q4=refinedA / PII-07 |

---

## 6. CI/CD・セキュリティツール（Q4=A / SECURITY）

| 項目 | ツール | マイルストーン |
|---|---|---|
| CI | GitHub Actions | MVP |
| SCA / SBOM | Snyk + Dependabot | MVP（基本）/ 決勝（フル、SECURITY-10） |
| TS Lint / Format | ESLint (strict) + Prettier | MVP |
| Python Lint / 型 | ruff + mypy --strict | MVP |
| IaC Lint | cdk-nag | MVP |
| シークレット管理 | AWS Secrets Manager / SSM Parameter Store | MVP（Creators API 認証情報等、ハードコード禁止 §6.4） |

---

## 7. 技術選定の確定事項サマリ

- **新規技術の導入なし**: 要件書 §7 / tech.md の確定スタックを Unit-1 で実体化するのみ
- **B-12 は Powertools のラッパー**として実装し、車輪の再発明を避ける（PII マスク + 相関 ID + EMF を上乗せ）
- **リトライは ApiClient に一元化**（TanStack Query retry=false）、二重リトライ防止
- **メトリクスは Powertools Metrics（EMF）**、命名規約のみ Unit-1 が規定、カタログは各 Unit（Q3=B）
- **フォールバックの共通土台は持たない**（Q6=B）。ApiClient は DomainError の正確な伝播に責務を限定

---

## 8. 未決定事項（後続ステージで確定）

| 項目 | 確定ステージ |
|---|---|
| VPC / Subnet / VPC Endpoint 構成（SECURITY-07） | Infrastructure Design |
| DynamoDB テーブル設計（共通設定・GSI） | Infrastructure Design（共通分） / 各 Unit（固有テーブル） |
| Lambda メモリ / タイムアウト / 同時実行数 | NFR Design |
| ElastiCache Redis ノードタイプ / クラスタ構成 | Infrastructure Design |
| OpenSearch Serverless コレクション設定 | Infrastructure Design（Unit-4 が主利用） |
| 具体メトリクス名カタログ | 各 Unit の NFR / Functional Design |
