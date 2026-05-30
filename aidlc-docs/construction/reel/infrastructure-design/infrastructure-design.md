# Unit-4 Reel — Infrastructure Design

> Unit-4 Reel（`reel-stack`）の AWS インフラ設計。論理コンポーネント（RLC-01〜10）を実 AWS リソースにマッピング。**Unit-1 platform-stack の共有基盤を SSM 参照で再利用し、reel 固有分のみを追加する**。
> 参照: [NFR Design](../nfr-design/) / [Functional Design](../functional-design/) / [shared-infrastructure.md](../../shared-infrastructure.md) / [Unit-1 Infrastructure Design](../../unit-1-platform/infrastructure-design/) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)
> 確定方針: Infra Q1〜Q7=A / リージョン: `ap-northeast-1`

---

## 0. サマリ

Unit-4 は新規基盤を作らず、Unit-1 が提供する VPC / API Gateway / Cognito / Redis / OpenSearch / KMS / IAM 規約 / 観測 / AuditLogger Layer / Secrets Manager を **SSM 参照で継承**する。`reel-stack` は **Unit-4 固有のリソース**（DynamoDB 2 テーブル / Lambda 4 種 / API パス / SSM 設定）のみを足す。

| 論理（RLC） | AWS サービス | MVP / 決勝 | 確定根拠 |
|---|---|---|---|
| RLC-01/02/03/04/05 Feed/推薦/ラベル | Lambda B-03（**VPC 外** + SnapStart） | 両方 | Q3=A |
| RLC-06 Catalog Gateway | MVP=B-03 プロセス内ダミー / 決勝=Lambda B-11（**VPC 内**） | 差あり | Q3=A / NFR R-PAT-VPC-01 |
| RLC-07 Transition Recorder | Lambda B-13（VPC 外）+ DynamoDB | 両方 | Q3=A / Q2=A |
| RLC-08 Special Link | Lambda B-10（VPC 外、純関数）+ Secrets Manager | 両方 | Q5=A |
| RLC-09 Reel Screen | （クライアント、インフラなし） | 両方 | — |
| RLC-10 Metrics | CloudWatch EMF + X-Ray + SNS（継承） | 両方 | Q6=A |
| ストレージ | DynamoDB `amazon-transitions` / `impressions`（reel 所有） | 両方 | Q2=A |
| 共有（継承） | Redis / OpenSearch / API GW / Cognito / KMS / Layer | 決勝で Redis/OpenSearch | Q1=A |

---

## 1. Unit-1 基盤の継承（Q1=A、SSM 参照）

`reel-stack` は以下を `StringParameter.valueForStringParameter()` で参照（Export/Import・ARN ハードコード禁止、shared-infrastructure.md §1）。

| 共有リソース | SSM パラメータ | Unit-4 での用途 |
|---|---|---|
| VPC ID / Isolated Subnet IDs | `/yudane/<env>/platform/vpc-id` / `isolated-subnet-ids` | 決勝の B-11（VPC 内）配置 |
| Lambda Security Group ID | `/yudane/<env>/platform/lambda-sg-id` | 決勝の B-11 → Redis/OpenSearch 接続 |
| API Gateway ID / Root Resource | `/yudane/<env>/platform/api-id` / `api-root-resource-id` | `/v1/reel`・`/v1/amazon-transitions` を追加 |
| Cognito User Pool / Client | `/yudane/<env>/platform/userpool-id` / `userpool-client-id` | Authorizer（共通） |
| ElastiCache Redis エンドポイント | `/yudane/<env>/platform/redis-endpoint` | **決勝**の商品メタ L1 キャッシュ |
| OpenSearch エンドポイント | （Unit-1 が Unit-4 着手時に platform へ追加・SSM 公開） | **決勝**のベクトル検索（B-204） |
| KMS Key ARN | `/yudane/<env>/platform/kms-key-arn` | DynamoDB / Logs の SSE |
| アラート SNS Topic | `/yudane/<env>/platform/alerts-topic-arn` | reel 固有 Alarm の通知先 |
| AuditLogger Lambda Layer ARN | `/yudane/<env>/platform/auditlogger-layer-arn` | 全 reel Lambda に付与 |

> **Unit-1 への依頼事項**: OpenSearch Serverless コレクションは Unit-1 infra に「Unit-4 着手時に platform-stack へ追加」と明記済み。決勝の B-204 採用時に Unit-1（Member A）へ追加とデータアクセスポリシー（reel Lambda ロール限定）を依頼する。MVP では不要。

---

## 2. ストレージ（Q2=A、DynamoDB）

共通設定（On-Demand / PITR / SSE-KMS / `ttl` / 命名 `yudane-<unit>-<env>-<entity>`）は Unit-1 規約を継承。

### 2.1 `yudane-reel-<env>-amazon-transitions`（B-13 所有）

| 項目 | 設計 |
|---|---|
| PK | `userId` |
| SK | `transitionId`（サーバー採番 ULID） |
| 冪等性 | 属性 `clientTransitionId` + 条件付き書き込み `attribute_not_exists(clientTransitionId)`（R-PAT-TXN-01 / PBT-04）|
| GSI | `gsi-month`（PK=`userId#monthBucket`、SK=`recordedAt`）— 月間遷移集計・北極星指標 |
| 主要属性 | `asin` / `context`（reel/debate-agree/cart-attack）/ `recordedAt` / `monthBucket` |
| TTL | `ttl`（古い遷移ログの自動失効、保持期間は Code Generation で確定） |
| 課金 / 暗号化 | On-Demand / SSE-KMS（platform KMS）/ PITR 有効 |

### 2.2 `yudane-reel-<env>-impressions`（B-03 所有）

| 項目 | 設計 |
|---|---|
| PK | `userId` |
| SK | `shownAt#cardId` |
| 用途 | 既出抑制（カーソル seen-set 補助）/ A/B 計測（services.md `ReelImpressions`） |
| TTL | `ttl`（短期、セッション既出抑制目的） |
| 課金 / 暗号化 | On-Demand / SSE-KMS / PITR（任意） |

### 2.3 参照のみ（Unit-4 は作成しない、所有境界）

| テーブル | 所有 Unit | Unit-4 のアクセス |
|---|---|---|
| `SafeguardStates`（月間カウント・cooldown/debt フラグ） | Unit-7（Unit-1 規約） | 遷移ゲート判定 read + `transitionCountMonth` の条件付き increment |
| EXP / Achievements | Unit-2 スキーマ | B-13 が遷移時に EXP +1 を冪等 UpdateItem（同期、`ExpAwardDto` 返却）。嗜好ベクトル（PreferenceVectors）は B-08 日次バッチが非同期更新（Unit-4 は書かない） |

> **IAM**: B-13 ロールは reel 所有 2 テーブルへフルアクセス、`SafeguardStates` へは条件付き UpdateItem、`Achievements`（Unit-2 スキーマ）へは EXP の冪等 UpdateItem に限定（最小権限、SECURITY-06）。所有境界・書き込み権限の最終確定は Unit-2/7 と調整（Infrastructure Design の依頼事項）。

---

## 3. コンピュート（Q3=A、Lambda 配置と VPC 境界）

Python 3.13 / 個別 IAM ロール / AuditLogger Layer / X-Ray active を全 Lambda に適用（shared-infra §3.4）。メモリ・タイムアウトの具体値は Code Generation で確定。

| Lambda | 論理 | VPC | SnapStart | トリガー | 外部依存 |
|---|---|---|---|---|---|
| `yudane-reel-<env>-feed` | RLC-01/02/03/04/05（B-03）+ **RLC-08 同梱（B-10 純関数）** | **VPC 外** | ON + Alias | API GW `GET /v1/reel` | Bedrock Runtime（ラベル）/ 決勝: B-11 invoke |
| `yudane-reel-<env>-transition` | RLC-07（B-13）+ **RLC-08 同梱（B-10 純関数）** | **VPC 外** | ON + Alias | API GW `POST /v1/amazon-transitions` | DynamoDB / SafeguardStates / Achievements / SSM（タグ） |
| `yudane-reel-<env>-catalog` | RLC-06（B-11） | **決勝のみ VPC 内**（Isolated Subnet + Lambda SG） | — | feed からの内部 invoke（決勝） | Redis / Creators API / OpenSearch |

> **B-10 Special Link は専用 Lambda を設けない**（外部呼び出しのない純 URL 生成のため）。`shared/` または `backend/src/reel/` の共有モジュールとして feed / transition Lambda が import する（invoke ホップ・コスト回避、過剰設計回避）。

### VPC 境界の物理化（R-PAT-VPC-01）
- **MVP**: 全 Lambda VPC 外。カタログは feed Lambda（B-03）に **DummyCatalogAdapter を同梱**（別 Lambda・Redis・VPC なし）。ENI コールドスタート回避 + invoke ホップ排除
- **決勝**: catalog Lambda（B-11）を VPC 内（Isolated Subnet）に追加し、feed Lambda（VPC 外）から Lambda invoke。Redis / OpenSearch は platform の Lambda SG からのみ到達
- B-13 の DynamoDB / SafeguardStates アクセスは VPC 外から可（DynamoDB は VPC Gateway Endpoint 不要、AWS API 直）

---

## 4. ネットワーク / API（Q4=A）

- **単一 platform API に相乗り**: platform-stack の API Gateway（SSM `api-id` / `api-root-resource-id` 参照）に reel パスを追加
  - `GET /v1/reel`（cursor / limit クエリ + `X-Correlation-Id`）→ feed Lambda
  - `POST /v1/amazon-transitions`（body + `X-Correlation-Id`）→ transition Lambda
- **認可**: 共通 Lambda Authorizer（JWT、TTL 5 分、継承）+ Lambda 冒頭 `@require_owner`（sub↔userId 照合、IDOR、PAT-SEC-01）
- **レート制限**: `POST /v1/amazon-transitions` を usage plan + throttling で 429 + `X-RateLimit-*`（REEL-API-07 / SECURITY-11 / API-09）
- 契約は OpenAPI（`shared/schema/paths/reel.yaml`）に非破壊追記（429 含む）。契約 PR 先行（api-contracts §2）

---

## 5. 外部統合（Q5=A）

| 外部 | 接続 | 認証情報 | MVP / 決勝 |
|---|---|---|---|
| Bedrock（Claude Haiku 4.5、ラベル/コピー） | VPC 外 B-03 → Bedrock Runtime（決勝で Interface Endpoint も可） | IAM（モデル invoke 権限）。モデル ID は SSM `/yudane/<env>/reel/bedrock-model-id` | **MVP から有効** |
| Amazon Creators API（商品メタ） | 決勝の VPC 内 B-11 → NAT / Interface Endpoint | Secrets Manager（Credential ID/Secret、実行時取得） | **決勝のみ**（MVP はダミー） |
| Amazon Associates（Special Link タグ） | B-10 が URL にタグ付与（外部呼び出しなし、純関数共有モジュール） | **SSM**（Associates タグは URL に公開される非機密値） | 両方（MVP は dev 仮リンク / prd 未承認ブロック） |

- 認証情報のハードコード禁止（SECURITY-09 / §6.4）。SSM は非機密設定（モデル ID / 重み / 閾値）

### reel 固有 SSM パラメータ

| パラメータ | 用途 |
|---|---|
| `/yudane/<env>/reel/bedrock-model-id` | ラベル/コピー生成モデル（Haiku 4.5） |
| `/yudane/<env>/reel/associates-tag` | Associates トラッキングタグ（非機密、URL に公開される値。Creators OAuth 認証情報は Secrets Manager） |
| `/yudane/<env>/reel/ranking-weights` | リランク重み（relatedness/timeBoost/... の既定値） |
| `/yudane/<env>/reel/creators-approved` | Approved Mobile Application 承認フラグ（環境ガード、§8 A-10） |

---

## 6. 観測・アラート（Q6=A、Unit-1 継承）

- 全 reel Lambda: AuditLogger Layer（構造化ログ + PII マスク + 相関 ID + EMF）+ X-Ray active
- **EMF メトリクス**（サーバー、B-12 metric Facade）: `reel.feed_latency` / `reel.catalog_cache_hit_rate` / `reel.transition_409_rate`
- **クライアントイベント**（M-13 → B-14）: `reel.viewed` / `swiped` / `double_tap` / `amazon_tap` / `boost_shown` / `label_fallback`
- **MVP Alarm**（→ platform SNS `alerts-topic-arn`）: feed Lambda エラー率 / transition Lambda エラー率 / 遷移 409 率の異常スパイク
- **決勝**: 北極星ダッシュボード（リール経由 Amazon 遷移率）+ レイテンシ p95 監視 + Anomaly Detection
- CloudWatch Logs 保持 90 日（SECURITY-14）

---

## 7. セキュリティ基盤（継承 + reel 固有）

| 項目 | 構成 |
|---|---|
| 暗号化（SECURITY-01） | DynamoDB / Logs を platform KMS で SSE、API は TLS 1.2+ |
| IAM（SECURITY-06） | Lambda ごと個別ロール。B-13 は reel 2 テーブル + SafeguardStates 条件付き UpdateItem + Achievements EXP 冪等 UpdateItem。B-03 は Bedrock invoke + 決勝 B-11 invoke。`*` 禁止 + cdk-nag |
| ネットワーク（SECURITY-07） | 決勝 B-11 のみ VPC 内、Redis/OpenSearch は Lambda SG 限定。MVP は VPC なし |
| ハードニング（SECURITY-09） | 外部 API 失敗を `external-api.*` に正規化（詳細秘匿）、fail-closed Safeguard ゲート |
| レート制限（SECURITY-11） | `POST /v1/amazon-transitions` の usage plan 429 |
| 機密管理 | Creators/Associates 認証情報は Secrets Manager、非機密は SSM |
| コンテンツ（NG-6/NG-8） | ラベル出力モデレーション（B-03）/ Special Link 短縮禁止（B-10）はアプリ層、インフラは Bedrock/Secrets 接続を提供 |

---

## 8. 論理 → 物理マッピング表

| RLC | 論理コンポーネント | 物理 AWS リソース | VPC |
|---|---|---|---|
| RLC-01/02/03/04/05 | Feed Orchestrator / Candidate / Reranker / Booster / Label | `reel-<env>-feed` Lambda + Bedrock | VPC 外 |
| RLC-06 | Product Catalog Gateway | MVP=feed 同梱ダミー / 決勝=`reel-<env>-catalog` Lambda + Redis | 決勝のみ VPC 内 |
| RLC-07 | Amazon Transition Recorder | `reel-<env>-transition` Lambda + DynamoDB(amazon-transitions) + SafeguardStates + Achievements(EXP) | VPC 外 |
| RLC-08 | Special Link Generator | **共有モジュール**（feed/transition Lambda に同梱）+ SSM(Associates タグ) | VPC 外 |
| RLC-09 | Reel Screen | （クライアント、API GW 接続のみ） | — |
| RLC-10 | Reel Metrics | CloudWatch EMF / X-Ray / SNS（継承）+ B-14（クライアントイベント） | — |
| 継承 | Authorization / Audit / Safeguard Policy / ASIN | API GW Authorizer / AuditLogger Layer / S-03・S-01 ライブラリ | — |

---

## 9. Extension コンプライアンスサマリ（Infrastructure Design 段階）

| Extension | 状態 | 反映 |
|---|---|---|
| SECURITY-01 暗号化 | ✅ | DynamoDB/Logs KMS（継承）|
| SECURITY-06 IAM 最小権限 | ✅ | Lambda 個別ロール + テーブル/Secrets 限定 + cdk-nag |
| SECURITY-07 ネットワーク | ✅ | 決勝 B-11 のみ VPC 内（MVP は VPC なし）|
| SECURITY-09 ハードニング | ✅ | 外部 API 詳細秘匿 / fail-closed |
| SECURITY-11 レート制限 | ✅ | POST 429 usage plan |
| SECURITY-14 アラート | ✅ | reel Alarm → platform SNS、ログ 90 日 |
| cdk-nag | ✅ | reel-stack に AwsSolutionsChecks 全適用 |
| SECURITY-12 認証 | N/A | Unit-2 の責務 |
