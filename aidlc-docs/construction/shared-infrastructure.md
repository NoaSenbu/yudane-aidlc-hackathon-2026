# Shared Infrastructure（全 Unit 継承）

> Unit-1 Platform（`platform-stack`）が提供し、**全 Unit が継承・参照する共通インフラ規約**。
> 各 Unit のスタック（auth/debate/reel/cart/calendar/safeguard/report）はこの規約に従う。
> 参照: [Unit-1 infrastructure-design.md](./unit-1-platform/infrastructure-design/infrastructure-design.md) / [deployment-architecture.md](./unit-1-platform/infrastructure-design/deployment-architecture.md) / [tech-cdk.md](../../.kiro/steering/tech-cdk.md)
> 確定方針: Infra Q1-Q7=A

---

## 1. platform-stack が公開する共有リソース

| リソース | 参照方法（SSM Parameter） |
|---|---|
| VPC ID | `/yudane/<env>/platform/vpc-id` |
| Private Subnet IDs | `/yudane/<env>/platform/private-subnet-ids` |
| Isolated Subnet IDs | `/yudane/<env>/platform/isolated-subnet-ids` |
| API Gateway ID / Root Resource | `/yudane/<env>/platform/api-id` / `api-root-resource-id` |
| Cognito User Pool ID / Client ID | `/yudane/<env>/platform/userpool-id` / `userpool-client-id` |
| ElastiCache Redis エンドポイント | `/yudane/<env>/platform/redis-endpoint` |
| KMS Key ARN | `/yudane/<env>/platform/kms-key-arn` |
| アラート SNS Topic ARN | `/yudane/<env>/platform/alerts-topic-arn` |
| Lambda Security Group ID | `/yudane/<env>/platform/lambda-sg-id` |
| AuditLogger Lambda Layer ARN | `/yudane/<env>/platform/auditlogger-layer-arn` |

各 Unit スタックは `StringParameter.valueForStringParameter()` で参照（Export/Import 不使用、tech-cdk §3）。

---

## 2. 命名規約（全 Unit 共通）

| 対象 | 規則 | 例 |
|---|---|---|
| Stack | `<unit>-<env>-stack` | `debate-prd-stack` |
| DynamoDB テーブル | `yudane-<unit>-<env>-<entity>` | `yudane-cart-dev-watch-items` |
| GSI | `gsi-<attribute>` | `gsi-user-id` |
| S3 バケット | `yudane-<unit>-<env>-<purpose>` | `yudane-platform-dev-datalake` |
| Lambda | `yudane-<unit>-<env>-<function>` | `yudane-debate-dev-streaming` |
| SSM Parameter | `/yudane/<env>/<unit>/<key>` | `/yudane/dev/debate/bedrock-model-id` |
| Cognito リソース | `yudane-<unit>-<env>-<resource>` | `yudane-auth-dev-userpool` |
| Construct（コード） | PascalCase | `DebateLambdaConstruct` |

---

## 3. 全 Unit 必須のインフラ規約

### 3.1 暗号化（SECURITY-01）
- DynamoDB / S3 / Redis / CloudWatch Logs は platform の KMS キー（`kms-key-arn`）で SSE
- 全 API は TLS 1.2+

### 3.2 IAM（SECURITY-06）
- Lambda ごとに個別ロール（共有ロール禁止）
- `*` resource / action は理由コメント + cdk-nag suppression 必須
- 最小権限（参照する DynamoDB テーブル / S3 プレフィックスに限定）

### 3.3 ネットワーク（SECURITY-07）
- 業務 Lambda は VPC（private with egress）に配置
- DynamoDB / S3 アクセスは VPC Gateway Endpoint 経由
- Redis / OpenSearch は platform の Lambda SG からのみ

### 3.4 観測（SECURITY-02/03/14）
- 全 Lambda は AuditLogger Layer（B-12）を使用（構造化ログ + PII マスク + 相関 ID + EMF）
- X-Ray active tracing 有効
- CloudWatch Logs 保持 90 日
- 重大アラートは platform の SNS トピックへ

### 3.5 設定・機密（SECURITY-09）
- 機密（API キー / シークレット）は Secrets Manager
- 非機密設定は SSM Parameter Store
- `cdk.json` / `cdk.context.json` への機密直書き禁止

### 3.6 API 契約（Q1=refinedA）
- 全エンドポイントは platform の単一 API Gateway にパスを追加（`/v1/...`）
- OpenAPI 骨格は Unit-1 が凍結、各 Unit は省略可能フィールドを非破壊で追記
- 認可は Authorizer（認証）+ `@require_owner` デコレータ（sub 照合、IDOR 対策）

### 3.7 テレメトリ（Q3=B）
- メトリクスは EMF（B-12 metric Facade）、命名 `<unit>.<domain>.<metric>`
- 具体メトリクス名は各 Unit が S-04 TelemetryContracts に追記
- 次元に高カーディナリティ値（userId/asin）を入れない

---

## 4. デプロイ順序（unit-of-work-dependency.md）

```
platform-stack（Unit-1）
  → auth-stack（Unit-2）
    → debate-stack / reel-stack / cart-stack（コア 3、並行）
      → calendar-stack / safeguard-stack / report-stack（サポート 3、並行）
```

- 各 Unit はデプロイ前に platform-stack の SSM パラメータが存在することを前提とする
- cdk-nag（AwsSolutionsChecks）を全スタックで適用

---

## 5. 環境（Q6=A）

| 環境 | removalPolicy | 用途 |
|---|---|---|
| dev | DESTROY | 開発・予選 MVP |
| prd | RETAIN | 決勝本番 |

破壊的操作（`cdk destroy` prd / IAM・DynamoDB・S3・KMS 削除）は事前承認必須（tech-cdk §10）。
