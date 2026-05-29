# Unit-1 Platform — Infrastructure Design

> Unit-1 Platform（`platform-stack`）の AWS インフラ設計。論理コンポーネントを実 AWS サービスにマッピング。
> 参照: [NFR Design](../nfr-design/) / [logical-components.md](../nfr-design/logical-components.md) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md) / [unit-of-work.md](../../../inception/application-design/unit-of-work.md)
> 確定方針: Infra Q1=A / Q2=A / Q3=A / Q4=A / Q5=A / Q6=A / Q7=A
> リージョン: `ap-northeast-1`

---

## 0. サマリ

`platform-stack` は全 7 Unit が継承する共通基盤。論理コンポーネント（LC-01〜08）と NFR を実 AWS サービスへマッピングする。

| 論理 | AWS サービス | 確定根拠 |
|---|---|---|
| ネットワーク | VPC（2 AZ / 3 層サブネット）+ VPC Endpoint + NAT×1（dev） | Q1=A / SECURITY-07 |
| API + 認可 | API Gateway (REST, 単一) + Lambda Authorizer + usage plan | Q2=A / LC-04 |
| 認証基盤 | Cognito User Pool（基盤のみ） | unit-of-work Unit-1 |
| データ（共通） | DynamoDB（テーブル分離 + 共通設定）+ S3 + ElastiCache Redis + OpenSearch Serverless | Q3=A / Q7=A |
| 観測 | CloudWatch Logs/Metrics/Alarms + X-Ray + SNS | Q5=A / SECURITY-02/14 |
| セキュリティ | KMS + IAM 個別ロール + Secrets Manager + SSM Parameter Store | SECURITY-01/06 |
| 共通 Lambda | B-12 AuditLogger（Lambda Layer）/ B-14 Telemetry / health | LC-02/03/05 |

---

## 1. ネットワーク（Q1=A、SECURITY-07）

### VPC 構成
- **VPC**: `yudane-platform-<env>-vpc`、CIDR `10.0.0.0/16`、2 AZ（ap-northeast-1a / 1c）
- **サブネット 3 層**:
  - public（ALB / NAT 用、各 AZ /24）
  - private with egress（Lambda 配置、各 AZ /24）
  - isolated（DynamoDB/Redis/OpenSearch アクセス、各 AZ /24）
- **NAT**: dev = 1 基（コスト抑制）、prd = AZ ごと（決勝前に冗長化、Q6 と連動）
- **VPC Endpoint**:
  - Gateway 型: DynamoDB / S3（無料、isolated からアクセス）
  - Interface 型: Secrets Manager / SSM / CloudWatch Logs / Bedrock Runtime / ECR（Lambda の依存先）

### Security Group
- Lambda SG → Redis/OpenSearch SG への最小許可（ポート単位）
- `*` の許可禁止（cdk-nag aws-solutions-vpc 系で検査）

---

## 2. API Gateway + 認可（Q2=A、LC-04）

- **REST API（単一）**: `yudane-platform-<env>-api`。全 Unit がパスを分割して相乗り（`/v1/debate-sessions`、`/v1/reel`、`/v1/cart-watch-items` 等）
- **Lambda Authorizer**: JWT（Cognito）検証。結果キャッシュ TTL 5 分（レイテンシ低減）
- **rate limit**: usage plan + throttling（全 POST に 429 + `X-RateLimit-*`、SECURITY-11 / API-09）
- **ステージ**: `dev` / `prd`（Q6 連動）
- **認可の二層**: Authorizer（認証）+ Lambda 冒頭 `@require_owner`（sub↔path userId 照合、IDOR 対策、PAT-SEC-01）

---

## 3. 認証基盤（Cognito User Pool）

- **User Pool**: `yudane-auth-<env>-userpool`（命名は auth 領域だが基盤生成は Unit-1、実装フローは Unit-2）
- Unit-1 の責務: User Pool + App Client + ドメインの**土台生成**のみ
- MFA（TOTP）フロー / トリガー Lambda（B-01）は **Unit-2** が実装（SECURITY-12 は Unit-2）
- User Pool ID / Client ID を SSM Parameter Store（`/yudane/<env>/platform/userpool-id` 等）で他 Unit へ公開

---

## 4. データストア

### 4.1 DynamoDB（Q3=A: テーブル分離 + 共通設定規約）
- **テーブル所有**: 各 Unit が固有テーブルを持つ。Unit-1 は共通設定を規定:
  - 課金: オンデマンド（PAY_PER_REQUEST、予測困難なスパイク対応 §6.3）
  - PITR（Point-in-Time Recovery）有効
  - 暗号化: SSE-KMS（カスタマーマネージドキー、SECURITY-01）
  - TTL 属性規約: `ttl`（epoch 秒）
  - 命名: `yudane-<unit>-<env>-<entity>`（例 `yudane-cart-dev-watch-items`）
  - GSI 命名: `gsi-<attribute>`
- Unit-1 が持つ共通テーブル: なし（共通設定の Construct/規約のみ提供）

### 4.2 S3
- **Data Lake**: `yudane-platform-<env>-datalake`（B-14 のテレメトリ Parquet、パーティション `dt=YYYY-MM-DD`）
- **カタログキャッシュ**: `yudane-platform-<env>-catalog`（商品画像 / 静的推薦カタログ）
- 全バケット: SSE-KMS / パブリックアクセス全ブロック（SECURITY-09）/ バージョニング

### 4.3 ElastiCache Redis（Q7=A: platform-stack に配置、Unit-4/5 共有）
- `yudane-platform-<env>-redis`、dev = 最小ノード（cache.t4g.micro 1 ノード）、prd = レプリカ構成（決勝前）
- 用途: B-11 CreatorsApiClient の商品メタキャッシュ（TTL 6h）/ レート制限カウンタ / セッション
- isolated サブネット配置、Lambda SG からのみアクセス
- 接続情報は SSM（`/yudane/<env>/platform/redis-endpoint`）で公開

### 4.4 OpenSearch Serverless（Q7=A: platform-stack に配置、Unit-4 着手時に追加）
- `yudane-platform-<env>-vectors`（Titan Embeddings のベクトル検索、主利用 Unit-4 Reel）
- MVP は小規模コレクション。Unit-4 着手時に platform-stack へ追加
- VPC アクセス + データアクセスポリシーで Unit-4 Lambda ロールに限定

---

## 5. 観測・アラート（Q5=A、SECURITY-02/14）

### MVP（5/30）
- CloudWatch Logs（保持 90 日、SECURITY-14）
- X-Ray トレース（B-12 trace 連携）
- 主要 Alarm: 認証失敗率 / API 5xx 率 / Lambda エラー率 → SNS トピック `yudane-platform-<env>-alerts`
- EMF カスタムメトリクス土台（B-12 metric、PAT-OBS-01）

### 決勝（6/26）
- 北極星指標ダッシュボード（論破→Amazon 遷移率等、services.md 集計経路）
- 全 Alarm + 異常検知（CloudWatch Anomaly Detection）

---

## 6. セキュリティ基盤（SECURITY-01/06/09）

| 項目 | 構成 |
|---|---|
| KMS | カスタマーマネージドキー（DynamoDB / S3 / Redis / Logs 暗号化）、キーローテーション有効 |
| IAM | Lambda ごと個別ロール、`*` resource/action 禁止（cdk-nag aws-solutions-iam4/5）。Suppression は理由コメント必須 |
| Secrets Manager | Creators API Credential ID / Secret（ハードコード禁止、§6.4） |
| SSM Parameter Store | 非機密の設定値（モデル ID / エンドポイント / User Pool ID 等）、`/yudane/<env>/<unit>/<key>` |
| S3 | パブリックアクセス全ブロック、TLS 強制バケットポリシー |

---

## 7. 共通 Lambda リソース

| リソース | 構成 |
|---|---|
| B-12 AuditLogger | **Lambda Layer**（Powertools + sanitizer）として全 Unit に配布 |
| B-14 TelemetryIngestion | Lambda（`POST /v1/telemetry`）、VPC 内、EMF + S3 書き込み |
| Health | Lambda（`GET /v1/health`）、DynamoDB/Redis 浅い疎通（PAT-RESIL-04） |
| Lambda 共通設定 | Python 3.13 / Powertools / 個別ロール / X-Ray active / メモリ・タイムアウトは NFR Design 既定（具体値は code-generation で確定） |

---

## 8. 論理 → 物理マッピング表

| LC | 論理コンポーネント | 物理 AWS リソース |
|---|---|---|
| LC-01 | ApiClient Interceptor Chain | （クライアント側、インフラなし。接続先 = API GW） |
| LC-02 | Telemetry Pipeline | B-14 Lambda + S3 Data Lake + CloudWatch EMF |
| LC-03 | Audit Logging Facade | Lambda Layer + CloudWatch Logs + X-Ray |
| LC-04 | Authorization Layer | API GW Lambda Authorizer + Cognito User Pool |
| LC-05 | Health & Degrade Surface | Health Lambda + API GW route |
| LC-06 | Shared Contract & Codegen | （ビルド時、CI。ランタイムインフラなし） |
| LC-07 | Safeguard Policy Module | （共有ライブラリ、ランタイムは各 Unit Lambda 内） |
| LC-08 | ASIN Utility | （共有ライブラリ、同上） |

---

## 9. Extension コンプライアンスサマリ（Infrastructure Design 段階）

| Extension | 状態 | 反映 |
|---|---|---|
| SECURITY-01 暗号化 | ✅ | KMS（DynamoDB/S3/Redis/Logs）、TLS 強制 |
| SECURITY-02 ネットワークログ | ✅ | API GW 実行/アクセスログ → CloudWatch |
| SECURITY-06 IAM 最小権限 | ✅ | Lambda 個別ロール、`*` 禁止 + cdk-nag |
| SECURITY-07 ネットワーク | ✅ | VPC + VPC Endpoint（Q1=A） |
| SECURITY-09 ハードニング | ✅ | S3 パブリック遮断、エラー秘匿 |
| SECURITY-14 アラート | ✅ | 主要 Alarm + SNS、ログ 90 日（Q5=A） |
| cdk-nag | ✅ | AwsSolutionsChecks 全適用、Suppression に理由コメント |
