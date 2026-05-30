# Unit-4 Reel — Infrastructure Design Plan

> Construction Phase / Per-Unit Loop / Unit-4 Reel のインフラ設計計画。論理コンポーネント（RLC-01〜10）を実 AWS リソースにマッピング。
> 参照: [NFR Design](../reel/nfr-design/) / [Functional Design](../reel/functional-design/) / [shared-infrastructure.md](../shared-infrastructure.md) / [Unit-1 Infrastructure Design](../unit-1-platform/infrastructure-design/) / [tech-cdk.md](../../../.kiro/steering/tech-cdk.md)
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / Infrastructure Design / 担当: Member C / リージョン: `ap-northeast-1`

---

## 0. 位置づけ（Unit-1 基盤の再利用前提）

Unit-1 Platform が **VPC / API Gateway（単一）/ Lambda Authorizer / Cognito / ElastiCache Redis / OpenSearch Serverless（Unit-4 着手時追加）/ KMS / IAM 規約 / 観測（CloudWatch・X-Ray・SNS）/ AuditLogger Lambda Layer / Secrets Manager / SSM** を整備済み。これらは [shared-infrastructure.md](../shared-infrastructure.md) の SSM パラメータ（`StringParameter.valueForStringParameter()`）で参照する（Export/Import 不使用）。

そのため Unit-4 の Infrastructure Design は **新規基盤を作らず、`reel-stack` に Unit-4 固有のリソースだけを足す** 軽量スコープ。NFR Design の MVP/決勝 構成差（MVP=VPC なし・ダミーカタログ / 決勝=VPC 内 B-11・Redis・OpenSearch）をそのまま物理化する。

### Unit-1 から継承する共有リソース（再掲・再利用）

| 共有リソース | SSM 参照 | Unit-4 での用途 |
|---|---|---|
| VPC / Isolated Subnet | `/yudane/<env>/platform/vpc-id` 等 | 決勝の B-11（VPC 内）配置 |
| API Gateway（単一）+ Authorizer | `/yudane/<env>/platform/api-id` 等 | `/v1/reel`・`/v1/amazon-transitions` をパス追加 |
| ElastiCache Redis | `/yudane/<env>/platform/redis-endpoint` | 決勝の商品メタ L1 キャッシュ（B-11） |
| OpenSearch Serverless | （Unit-1 が Unit-4 着手時に platform へ追加） | 決勝のベクトル検索（B-204） |
| KMS / Lambda SG / SNS / AuditLogger Layer | 各 SSM | 暗号化・SG・アラート・ログ |
| Secrets Manager | Creators/Associates Credential | B-10/B-11 が実行時参照 |

### Unit-4 が `reel-stack` で新規に作るリソース（候補）

- DynamoDB: `AmazonTransitions` / `ReelImpressions`（Unit-4 所有）
- Lambda: B-03（推薦, VPC 外）/ B-13（遷移, VPC 外）/ B-10（リンク, VPC 外）/ B-11（カタログ, **決勝のみ VPC 内**）
- SSM: reel 固有設定（Bedrock モデル ID / Associates タグ / 重み・閾値）
- API Gateway パス追加（`/v1/reel` GET / `/v1/amazon-transitions` POST + 429）

---

## 1. 設計判断のための質問

以下の質問に `[Answer]:` タグで回答してください（推奨は **A**）。回答完了後「done」等でお知らせください。

### Question 1（Shared Infrastructure: 共有資源の参照方針）
Unit-1 platform-stack の共有資源（VPC / API GW / Redis / KMS / SG / Layer）の **参照方針**をどうしますか？

A) **SSM Parameter 参照に全面準拠（shared-infrastructure.md §1）**: `StringParameter.valueForStringParameter()` で参照し、Export/Import・直接 ARN ハードコードはしない。reel-stack は platform-stack の後にデプロイ（デプロイ順序 §4 準拠）— 推奨（疎結合・Unit-1 規約準拠）
B) 一部を CloudFormation Export/Import で参照（密結合だが型が効く）
X) Other（[Answer]: の後に記述）
A
[Answer]: 

### Question 2（Storage: DynamoDB テーブル設計）
Unit-4 所有の DynamoDB テーブルの **キー設計・構成**をどうしますか？（共通設定 = On-Demand / PITR / SSE-KMS / TTL は Unit-1 規約を継承）

A) **2 テーブル（用途分離）+ 冪等性・集計用キー**:
- `yudane-reel-<env>-amazon-transitions`: PK=`userId`, SK=`transitionId`。冪等性は属性 `clientTransitionId` に条件付き書き込み（`attribute_not_exists`）。GSI=`gsi-month`（PK=`userId#monthBucket` で月間集計）。`ttl` で古いログ自動失効
- `yudane-reel-<env>-impressions`: PK=`userId`, SK=`shownAt#cardId`（既出抑制 / A/B、`ttl` 短期）
- SafeguardStates / EXP は **Unit-7 / Unit-2 所有テーブルを参照・更新**（Unit-4 は新規作成しない、NFR Design の所有境界）
— 推奨
B) 単一テーブル設計（Single Table Design）に全エンティティ集約（柔軟だが設計コスト高・ハッカソンには過剰）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3（Compute: Lambda 配置と VPC 境界の物理化）
Unit-4 Lambda の **VPC 配置・ランタイム構成**をどうしますか？（NFR Design R-PAT-VPC-01 = MVP は VPC なし / 決勝のみ B-11 を VPC 内）

A) **MVP は全 Lambda を VPC 外（SnapStart）/ 決勝のみ B-11 を VPC 内に追加**:
- B-03（推薦）/ B-13（遷移）/ B-10（リンク）: VPC 外、Python 3.13、SnapStart（ON_PUBLISHED_VERSIONS）+ Alias、AuditLogger Layer
- B-11（カタログ）: **MVP は B-03 同梱（プロセス内ダミー、別 Lambda なし）** / **決勝は VPC 内 Lambda**（Isolated Subnet、Lambda SG、Redis/OpenSearch 到達）
- メモリ/タイムアウトの具体値は Code Generation で確定（本ステージは配置と境界のみ）
— 推奨
B) MVP から B-11 を独立 Lambda（VPC 外）にして将来 VPC 化（invoke ホップが MVP から発生、NFR Design の過剰設計回避と不整合）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4（Networking: API Gateway パス追加と Authorizer）
`/v1/reel`・`/v1/amazon-transitions` の **API Gateway への追加方針**をどうしますか？

A) **単一 platform API にパスを相乗り + 共通 Authorizer + POST 429**: platform-stack の API Gateway（SSM 参照）に reel パスを追加。認証は共通 Lambda Authorizer（JWT、TTL 5 分）、`@require_owner` で sub 照合。`POST /v1/amazon-transitions` は usage plan で 429 + `X-RateLimit-*`（REEL-API-07 / SECURITY-11）。`GET /v1/reel` はカーソル/limit クエリ — 推奨（shared-infra §3.6 準拠）
B) reel 専用の API Gateway を新設（分離されるが Authorizer/ドメイン/コスト二重化、規約違反）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5（External Integration: Creators API / Bedrock / Associates の接続）
外部サービス（Creators API / Bedrock / Associates）への **接続・認証情報管理**をどうしますか？

A) **Secrets Manager + SSM + VPC Endpoint（決勝）/ MVP はダミー・直呼び**:
- Creators/Associates 認証情報: Secrets Manager（実行時取得、ハードコード禁止）。MVP はダミーカタログのため Creators 接続なし
- Bedrock（Haiku 4.5、ラベル/コピー生成）: VPC 外 B-03 から Bedrock Runtime を呼ぶ（MVP から有効。Bedrock は VPC Endpoint 不要だが決勝で Interface Endpoint 経由も可）。モデル ID は SSM（`/yudane/<env>/reel/bedrock-model-id`）
- 決勝の B-11（VPC 内）→ Creators API は NAT or Interface Endpoint 経由
— 推奨
B) 認証情報を SSM SecureString に統一（Secrets Manager を使わない、ローテーション弱い）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6（Monitoring: Unit-4 の観測リソース）
Unit-4 の **観測・アラートのインフラ**をどうしますか？（Unit-1 の CloudWatch/X-Ray/SNS/EMF 土台を継承）

A) **Unit-1 観測基盤を継承 + reel 固有 Alarm を SNS へ**: 全 Lambda は AuditLogger Layer + X-Ray active。reel メトリクス（feed_latency / catalog_cache_hit_rate / transition_409_rate / reel.* イベント）は EMF。MVP は主要 Alarm（B-03/B-13 エラー率・遷移 409 率の異常）を platform の SNS トピックへ。北極星ダッシュボード（リール経由遷移率）は決勝 — 推奨
B) Unit-1 継承のみ、reel 固有 Alarm は決勝で追加（MVP の異常検知が薄い）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 7（Deployment: reel-stack の構成と環境）
`reel-stack` の **スタック構成・環境・デプロイ**をどうしますか？

A) **単一 reel-stack / dev・prd 2 環境 / cdk-nag / platform 後にデプロイ**:
- `reel-<env>-stack`（命名規約準拠）。dev=removalPolicy DESTROY / prd=RETAIN
- platform-stack の SSM パラメータ存在を前提（デプロイ順序: platform → auth → reel）
- cdk-nag（AwsSolutionsChecks）全適用、Suppression は理由コメント必須
- 決勝の VPC 内 B-11 / OpenSearch 連携は同一 reel-stack 内で `env`/feature フラグで出し分け（MVP は無効）
— 推奨
B) MVP-stack と決勝-stack を物理分割（管理が複雑、ハッカソンには過剰）
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問（現在地）
- [x] Functional / NFR Design 成果物の分析 + Unit-1 インフラ基盤・shared-infrastructure の確認
- [x] Infrastructure Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q7 に回答（全 A 確定）
- [x] 回答の分析・曖昧さ検出 → clarification 不要（全 A、曖昧さなし）
- [x] ユーザーが Clarification に回答（曖昧さがある場合）— N/A

### Part 2: インフラ設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/reel/infrastructure-design/infrastructure-design.md`
  - 論理→物理マッピング / DynamoDB テーブル設計 / Lambda 配置・VPC 境界 / API パス / 外部接続 / 観測 / セキュリティ / MVP・決勝差
- [x] `aidlc-docs/construction/reel/infrastructure-design/deployment-architecture.md`
  - reel-stack 構成 / SSM 参照 / デプロイ順序 / 環境（dev/prd）/ cdk-nag / デプロイ図
- [x] （shared-infrastructure.md は Unit-1 が整備済み。OpenSearch 追加を決勝時の Unit-1 依頼事項として注記）
- [x] 自己レビュー（整合性・要件充足・診断エラー・過剰設計の再点検）— diagnostics 0、MVP は VPC/Redis/OpenSearch 不使用で過剰なし、所有境界を明記
- [x] 完了メッセージ提示 + 承認ゲート（次ステージ = Code Generation）— 2026-05-30 承認（横断矛盾 3 件修正後）

---

## 3. Extension 適合の予定（Infrastructure Design 段階）

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-01（暗号化） | DynamoDB/S3/Logs を platform KMS で SSE（継承） |
| SECURITY-06（IAM 最小権限） | B-03/B-13/B-10/B-11 ごと個別ロール、参照テーブル/Secrets に限定、cdk-nag |
| SECURITY-07（ネットワーク） | 決勝の B-11 を VPC 内、Redis/OpenSearch は Lambda SG 限定（MVP は VPC なし） |
| SECURITY-09（ハードニング） | S3 パブリック遮断、エラー秘匿（継承） |
| SECURITY-11（レート制限） | `POST /v1/amazon-transitions` に usage plan 429 |
| SECURITY-14（アラート） | reel 固有 Alarm → platform SNS、ログ 90 日 |
| cdk-nag | reel-stack に AwsSolutionsChecks 全適用 |
