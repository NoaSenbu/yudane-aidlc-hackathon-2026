# Unit-5 Cart Intercept — Infrastructure Design

> AI-DLC Construction Phase / Per-Unit Loop / Infrastructure Design ステージ。
> [Plan v3](../../plans/unit-5-cart-intercept-infrastructure-design-plan.md) Q1〜Q10 確定（Q1=A / Q2=A / Q3=B / Q4=A / Q5=A / Q6=A' / Q7=A / Q8=A / Q9=A / Q10=A）に基づく物理マッピング詳細。
>
> 参照:
> - [functional-design.md §3](../functional-design/functional-design.md#3-infrastructureinfralibcart-stackts)（cart-stack.ts コード）
> - [nfr-design-patterns.md](../nfr-design/nfr-design-patterns.md)（19 パターン適用マトリクス）
> - [logical-components.md](../nfr-design/logical-components.md)（Mermaid + 相互作用 3 パターン）
> - [Unit-1 functional-design.md §3.1](../../unit-1-platform/functional-design/functional-design.md)（PlatformStack の kmsKey / idempotencyKeysTable）
> - [.kiro/steering/tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)（CDK 命名規則 / cdk-nag）

---

## Overview

本ドキュメントは Unit-5 Cart Intercept の **論理コンポーネント → 物理 AWS リソース** へのマッピングを定義する。Functional Design / NFR Design で論理レベルが確定済みのため、本ステージでは Stack 命名・環境分離・IAM 詳細・SSM パス・タグ戦略・cdk-nag suppressions・容量サニティを物理レベルで完結させることが目的。Plan v3 で確定した Q1〜Q10 を物理マッピング表（§10）として一望できる構造。

---

## Architecture

物理アーキテクチャは大きく以下の 3 階層で構成される:

1. **Persistence 層**: DDB CartWatchItems / NotificationLogs（On-Demand / KMS / TTL / GSI1）
2. **Compute 層**: Lambda 6 関数（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher / cart_attack_scheduler_retry）+ EventBridge Scheduler（One-time + rate(15min)）
3. **Integration 層**: EUM Application（APNs/FCM）+ SNS Topic + Slack Bridge Lambda + CloudWatch Alarms 5 系統

3 階層すべてが PlatformStack の `kmsKey` / `idempotencyKeysTable` / `idempotencyBucket` と Cross-Stack 直接参照（Q1=A）で結合する。詳細な Stack 構成図は [logical-components.md §1 Mermaid](../nfr-design/logical-components.md) を参照。

---

## Components and Interfaces

物理コンポーネントの詳細は §2（Lambda 詳細設定）/ §3（IAM Role / Policy）/ §4（EUM）/ §5（SNS + Slack）/ §6（CloudWatch Alarms）で展開する。各コンポーネントの Cross-Stack interface は §9（SSM Parameter 一覧）で集約する。

---

## Data Models

DDB スキーマ詳細（CartWatchItems / NotificationLogs の PK / SK / GSI1 / 属性）は [data-model.md](../functional-design/data-model.md) を参照。本ドキュメントでは物理リソース命名（§1.2）と環境別差異（§10 物理マッピング表）に焦点を当てる。

---

## Correctness Properties

[functional-design.md §0.2 Property 1〜6](../functional-design/functional-design.md) を本物理レイヤーで担保する観点を Property 単位に整理する。

### Property 1: 追撃時系列の単調性（物理担保）

**Validates: Requirements 5.3** FR-CART-02（3 段追撃の正確性）

EventBridge Scheduler の at 時刻精度 + Schedule 名 prefix `cart-attack-{userId}-{itemId}-{step}` で 30m / 6h / 24h ジョブの時系列が逆転しないことを物理的に担保する。CDK Snapshot TDD で Schedule 命名規則を fix。

### Property 4: NG-6 静的検証（CI Gate）

**Validates: Requirements 9** NG-6（脅迫・罪悪感強要の禁止）

Lambda bundle 前に `npm run check-ng-keywords` を CI で実行し、`backend/src/cart/notification_templates.py` の 30 パターン全てが NG-6 禁止ワード辞書に該当しないことを検証する。違反検出時は CI が fail、deploy ブロック。

### Property 5: Safeguard 通知抑制（IAM 担保）

**Validates: Requirements 5.10** FR-FUNNEL-04（Safeguard 介入時の通知抑制）

notification_dispatcher Lambda の IAM Role が SafeguardStates Table に対して `dynamodb:GetItem` の最小権限を持ち（§3.1.5）、`evaluate_notification` 関数で `block` 判定された場合は SendMessages を呼ばずに NotificationLogs に `status=suppressed_by_safeguard` を記録する。

### Property 6: DoS / SECURITY-15（容量上限担保）

**Validates: Requirements 6.4** SECURITY-15（DoS / レート制限）

cart_intake Lambda の `count_active(user_id)` Filter で active 状態のアイテム数が 100 件超過時に 429 を返却（[data-model.md §1.3](../functional-design/data-model.md)）。さらに Reserved Concurrency（共有 100 + 個別 60 = 160）で Lambda 暴走時の AWS アカウント全体への影響を限定する。

---

## Error Handling

物理レイヤーのエラーハンドリング:

- **Lambda Error**: 各 Lambda の Errors メトリクスを CloudWatch Alarm 4 で監視、SNS → Slack 通知
- **DDB Throttling**: On-Demand のため自動スケール、ConditionalCheckFailedException は status 遷移の競合として正常扱い（[data-model.md §1.3](../functional-design/data-model.md)）
- **EUM SendMessages 失敗**: NotificationDispatcherDlq に payload 退避、retentionPeriod 14 日で手動復旧
- **EventBridge Scheduler CreateSchedule 失敗**: B-04 内で部分失敗許容、B-05 retry batch（rate(15min)）が補完、3 回失敗で `watching_orphaned` 遷移 + Alarm 5
- **Slack Bridge Lambda 失敗**: Lambda 標準 retry（2 回）+ DLQ 不要（Alarm 失われても CloudWatch 上で確認可能）
- **CDK Deploy 失敗**: CFN 自動 rollback（Q10=A 反映、§5 deployment-architecture.md 参照）

---

## Testing Strategy

物理レイヤーのテスト:

- **Snapshot TDD**: `template.hasResourceProperties` で全リソース定義を検証（[functional-design.md §0.1 TDD 適用方針](../functional-design/functional-design.md)）。**[AGENTS.md §12 TDD 開発スタイル](../../../../.kiro/steering/AGENTS.md#12-tdd-開発スタイル全-unit-必須) / [tech-cdk.md §6.1 Snapshot TDD](../../../../.kiro/steering/tech-cdk.md#61-snapshot-tdd-cdk-必須) と完全整合**（2026-05-29 追記、Issue C1 対応）。
- **Smoke Test**: deploy 後に [deployment-architecture.md §7](./deployment-architecture.md) のチェックリスト 6 項目（dev）/ 11 項目（prd）を CI で自動実行
- **Integration Test IT-08〜10**: Lambda + DDB + Scheduler + EUM の連携を実 AWS 環境で検証（[functional-design.md §5](../functional-design/functional-design.md)）
- **cdk-nag Static Check**: `npm run synth -- --strict` で全 cdk-nag finding を CI で評価、§7 の 4 件 suppression のみ許可
- **コスト Linter**: `cdk synth` の出力から Reserved Concurrency / DDB Mode / Lambda Memory を grep して NFR §6.4 試算と乖離していないかを CI で確認（決勝後のプロダクト化判断時に拡張）

---

## 0. ステージ確定事項サマリ（Plan v3 → 物理マッピング）

| Plan v3 確定 | 物理マッピング | 環境別差異 |
|---|---|---|
| Q1=A: CDK construct 直接参照 | `props: { platformStack, authStack, safeguardStack }` で型安全な参照 | dev / prd で同一構造 |
| Q2=A: dev + prd の 2 環境 | `App.ts` で 2 Stack インスタンス（`cart-dev-stack` / `cart-prd-stack`、shared-infrastructure.md §2 / tech-cdk.md §4 命名規約準拠） | dev = 個人 sandbox 4 + 共有 dev、prd = デモ用 1 環境 |
| Q3=B: Function bundle 同梱 | poetry path dependencies で `shared/*` を Function zip に同梱 | dev / prd で同一バンドル方式 |
| Q4=A: default Group + Schedule 名 prefix | 攻撃ジョブ = `cart-attack-{userId}-{itemId}-{step}` / retry = `cart-retry-batch` | Schedule 名に `{init?}-` を sandbox 環境で挿入 |
| Q5=A: dev/prd 別 Application | `CfnApp` × 2、SSM `/yudane/{env}/cart/eum-application-id` | dev = APNs Sandbox cert / prd = APNs Production cert（B-504 backlog） |
| Q6=A': CartStack 内 cartAlertTopic | `sns.Topic` + Slack Webhook（Secrets Manager 経由） | dev / prd で別シークレット |
| Q7=A: 必須 4 タグ | `Environment` / `Unit` / `Owner` / `CostCenter` を Stack 全リソースに付与 | `Environment` のみ dev/prd で異なる |
| Q8=A: deploy-dev.yml に cart ジョブ追加 | `.github/workflows/deploy-dev.yml` の jobs に `cdk-deploy-cart-dev` を追加 | dev のみ自動 deploy、prd は manual approval |
| Q9=A: sandbox 内 Lambda 実体作成 | 4 名 × 個人 sandbox + 共有 dev + prd = 6 環境 | 個人 sandbox は `developerInitial` props で命名分離 |
| Q10=A: CDK Rollback + DDB PITR | `cdk deploy --rollback` + DDB PITR 35 日（prd のみ） | dev は PITR off |

> **2026-05-29 修正（Issue A3 対応）**: 命名規約を [shared-infrastructure.md §2](../../shared-infrastructure.md#2-命名規約全-unit-共通) / [tech-cdk.md §4](../../../../.kiro/steering/tech-cdk.md#4-cdk-固有命名) に揃えた。Stack は `<unit>-<env>-stack`（yudane- prefix なし）、DynamoDB / Lambda / EUM / SNS は `yudane-<unit>-<env>-<entity>`（unit-env 順）。個人 sandbox は Stack `<unit>-dev-<initial>-stack` / リソース `yudane-<unit>-dev-<initial>-<entity>`。

---

## 1. リソース命名規約と環境別マッピング

### 1.1 Stack 命名

```
cart-{env}-stack                   # 共有 dev / prd
cart-dev-{initial}-stack           # 個人 sandbox（developerInitial 指定時のみ）
```

| 環境 | Stack 名 |
|---|---|
| 共有 dev | `cart-dev-stack` |
| Member A sandbox | `cart-dev-a-stack` |
| Member B sandbox | `cart-dev-b-stack` |
| Member C sandbox | `cart-dev-c-stack` |
| Member D sandbox | `cart-dev-d-stack` |
| prd | `cart-prd-stack` |

### 1.2 リソース命名（`resourceName(props, suffix)` ヘルパー）

```typescript
// infra/lib/utils/resource-name.ts（Unit-1 で確定済み、本 Stack でも継承）
// shared-infrastructure.md §2: yudane-<unit>-<env>-<entity> 形式（unit-env 順）
export function resourceName(props: BaseStackProps, suffix: string): string {
  const initSegment = props.envName === 'dev' && props.developerInitial
    ? `-${props.developerInitial}`
    : '';
  return `yudane-cart-${props.envName}${initSegment}-${suffix}`;
}
```

#### 主要リソース命名マトリクス

| リソース | 共有 dev | Member D sandbox | prd |
|---|---|---|---|
| DDB CartWatchItems | `yudane-cart-dev-watch-items` | `yudane-cart-dev-d-watch-items` | `yudane-cart-prd-watch-items` |
| DDB NotificationLogs | `yudane-cart-dev-notification-logs` | `yudane-cart-dev-d-notification-logs` | `yudane-cart-prd-notification-logs` |
| Lambda cart_intake | `yudane-cart-dev-intake` | `yudane-cart-dev-d-intake` | `yudane-cart-prd-intake` |
| Lambda cart_dismiss | `yudane-cart-dev-dismiss` | `yudane-cart-dev-d-dismiss` | `yudane-cart-prd-dismiss` |
| Lambda cart_list | `yudane-cart-dev-list` | `yudane-cart-dev-d-list` | `yudane-cart-prd-list` |
| Lambda push_token | `yudane-cart-dev-push-token` | `yudane-cart-dev-d-push-token` | `yudane-cart-prd-push-token` |
| Lambda notification_dispatcher | `yudane-cart-dev-notification-dispatcher` | `yudane-cart-dev-d-notification-dispatcher` | `yudane-cart-prd-notification-dispatcher` |
| Lambda cart_attack_scheduler_retry | `yudane-cart-dev-attack-scheduler-retry` | `yudane-cart-dev-d-attack-scheduler-retry` | `yudane-cart-prd-attack-scheduler-retry` |
| EUM Application | `yudane-cart-dev` | `yudane-cart-dev-d` | `yudane-cart-prd` |
| SNS Topic（cartAlertTopic） | `yudane-cart-dev-alerts` | `yudane-cart-dev-d-alerts` | `yudane-cart-prd-alerts` |
| Schedule（攻撃ジョブ） | `cart-attack-{userId}-{itemId}-{step}` | `cart-attack-d-{userId}-{itemId}-{step}` | 同 dev 形式 |
| Schedule（retry batch） | `cart-retry-batch` | `cart-retry-batch-d` | `cart-retry-batch` |

> **注**: Schedule 名は EventBridge Scheduler の制約「64 文字以内」「`[0-9a-zA-Z-_.]` のみ」を満たす。`{userId}` は Cognito sub の最初 8 文字（hash）で短縮、`{itemId}` は ULID 26 文字。`cart-attack-XXXXXXXX-01HG...-30m` で 47 文字、上限内に収まる。

### 1.3 SSM Parameter パス

shared-infrastructure.md §1 規約 `/yudane/<env>/<unit>/<key>` の **4 階層固定** に準拠。個人 sandbox は env を `dev-{init}` 化（階層挿入ではなく env suffix）。

```
/yudane/{env}/cart/cart-watch-items-table-arn
/yudane/{env}/cart/notification-logs-table-arn
/yudane/{env}/cart/eum-application-id          # Q5=A 反映
/yudane/{env}/cart/alert-topic-arn             # Q6=A' 反映
```

| 環境 | env 値 | パス例 |
|---|---|---|
| 共有 dev | `dev` | `/yudane/dev/cart/eum-application-id` |
| Member D sandbox | `dev-d` | `/yudane/dev-d/cart/eum-application-id` |
| prd | `prd` | `/yudane/prd/cart/eum-application-id` |

> **2026-05-29 修正（Issue B7 対応）**: 当初は `/yudane/{env}/{init?}/cart/<key>` の 5 階層 + 階層挿入案だった。shared-infrastructure.md §1 規約の `/yudane/<env>/<unit>/<key>` 4 階層固定と乖離していたため、env を `dev-d` 形式で表現して規約を維持しつつ sandbox 分離を実現（個人 sandbox 例: `/yudane/dev-d/cart/eum-application-id`）。

### 1.4 Secrets Manager（Q6=A' Slack Webhook）

shared-infrastructure.md §2 規約 `yudane-<unit>-<env>-<purpose>` の Hyphen 区切りに準拠。

```
yudane-cart-{env}-slack-webhook-url
```

| 環境 | シークレット名 | 内容 |
|---|---|---|
| dev | `yudane-cart-dev-slack-webhook-url` | Slack `#yudane-dev` チャンネル用 Webhook URL |
| prd | `yudane-cart-prd-slack-webhook-url` | Slack `#yudane-emergency` チャンネル用 Webhook URL |

> 個人 sandbox は dev シークレットを共有（4 名で同 Webhook を参照、CloudWatch Alarm のメッセージに `{stack}` を含めて発信元判別）。
>
> **2026-05-29 修正（Issue C4 対応）**: 当初の `yudane/{env}/cart/slack-webhook-url` Slash 区切りを Hyphen 区切りの shared-infrastructure 規約に統一。Secrets Manager は両方許容するが、規約遵守でリソース命名を一貫化。

---

## 2. Lambda 詳細設定（Q3=B Function bundle 同梱）

### 2.1 Lambda 一覧と物理パラメータ

| Lambda | Memory | Timeout | Reserved Concurrency | SnapStart | VPC | DLQ |
|---|---|---|---|---|---|---|
| cart_intake | 512MB | 30s | 共有 100 | ✅ | 外 | — |
| cart_dismiss | 256MB | 5s | 共有 100 | ✅ | 外 | — |
| cart_list | 256MB | 5s | 共有 100 | — | 外 | — |
| push_token | 256MB | 5s | 共有 100 | — | 外 | — |
| notification_dispatcher | 512MB | 30s | **50（個別）** | ✅ | 外 | NotificationDispatcherDlq |
| cart_attack_scheduler_retry | 512MB | 60s | **10（個別）** | — | 外 | — |

> **Reserved Concurrency 集計**: notification_dispatcher 50 + cart_attack_scheduler_retry 10 = **個別合計 60**、共有プール 100、**理論最大同時実行 160**（アカウント上限 1000 の 16%、十分余裕）。実運用では各 Lambda がピーク同時に動く確率は低く、共有 100 のうち実利用は 5-20 程度の見込み。

### 2.2 SnapStart 適用 3 関数の publish 戦略

[NFR Requirements Q4 = B'](../nfr-requirements/nfr-requirements.md) 反映。

```typescript
// CDK 定義（cart-stack.ts 内）
const cartIntakeFunction = new lambda.Function(this, 'CartIntakeFunction', {
  // ... 通常設定
  snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
  currentVersionOptions: {
    description: `cart-intake v${process.env.CDK_DEPLOY_VERSION ?? 'latest'}`,
    removalPolicy: RemovalPolicy.RETAIN,  // 古いバージョンを保持して rollback 容易化
  },
});

const intakeAlias = new lambda.Alias(this, 'CartIntakeAlias', {
  aliasName: 'live',
  version: cartIntakeFunction.currentVersion,
});
```

**API Gateway Integration**: API Gateway は `cartIntakeFunction.functionArn` ではなく `intakeAlias.functionArn` を invoke。これで SnapStart の Snapshot がアクティブになる。

**ロールバック手順**:

1. `cdk deploy` 失敗 → CFN が自動的に直前 version へ rollback
2. 手動ロールバック: `aws lambda update-alias --function-name yudane-cart-prd-intake --name live --function-version <prev-version>`

### 2.3 Function bundle の poetry path dependencies（Q3=B）

```toml
# backend/pyproject.toml（Unit-1 §6 で確定済み、本 Unit でもそのまま流用）
[tool.poetry.dependencies]
python = "^3.13"
boto3 = "^1.35.0"
pydantic = "^2.10.0"
yudane-asin-extractor = { path = "../shared/asin-extractor", develop = true }
yudane-safeguard-policy = { path = "../shared/safeguard-policy", develop = true }
yudane-telemetry-contracts = { path = "../shared/telemetry-contracts", develop = true }
```

CDK でのバンドル:

```typescript
// infra/lib/cart-stack.ts
const cartIntakeFunction = new lambda.Function(this, 'CartIntakeFunction', {
  code: lambda.Code.fromAsset('../backend', {
    bundling: {
      image: lambda.Runtime.PYTHON_3_13.bundlingImage,
      command: [
        'bash', '-c',
        'pip install poetry && ' +
        'poetry export -f requirements.txt --output /asset-output/requirements.txt && ' +
        'pip install -r /asset-output/requirements.txt -t /asset-output && ' +
        'cp -r src/cart src/common /asset-output/'
      ],
    },
  }),
  handler: 'cart.handlers.cart_intake.lambda_handler',
  // ...
});
```

> **bundle サイズ計測**: 6 Lambda × 4-6MB → 平均 5MB、Lambda zip 上限 50MB の 10%。SnapStart 効果（cold start 30-50% 短縮）は Layer 不使用で最大化。

---

## 3. IAM Role / Policy 詳細（5 Lambda × 6 種類 = 30 statement の最小権限）

### 3.1 Lambda Execution Role 一覧

各 Lambda に **個別 Role**（SECURITY-06 最小権限）。

#### 3.1.1 `cart-intake-lambda-role`

| 権限 | Resource | 用途 |
|---|---|---|
| `dynamodb:GetItem` / `PutItem` / `UpdateItem` | `cartWatchItemsTable.tableArn` + `/index/GSI1-status` | CartWatchItem CRUD |
| `dynamodb:GetItem` / `PutItem` / `UpdateItem` | `props.platformStack.idempotencyKeysTable.tableArn` | with_idempotency middleware |
| `s3:PutObject` / `GetObject` | `props.platformStack.idempotencyBucket.bucketArn/*` | 大容量 idempotency response 保存 |
| `scheduler:CreateSchedule` / `GetSchedule` | `arn:aws:scheduler:{region}:{account}:schedule/default/cart-*` | 攻撃ジョブ作成（FD §3.2 cdk-nag wildcard suppression と整合）|
| `iam:PassRole` | `schedulerInvokeRole.roleArn` | Scheduler が NotificationDispatcher を invoke する Role |
| `kms:Encrypt` / `Decrypt` | `props.platformStack.kmsKey.keyArn` | DDB / S3 暗号化 |
| `logs:CreateLogStream` / `PutLogEvents` | `arn:aws:logs:*:*:log-group:/aws/lambda/yudane-cart-{env}-intake:*` | CloudWatch Logs |

#### 3.1.2 `cart-dismiss-lambda-role`

| 権限 | Resource |
|---|---|
| `dynamodb:GetItem` / `UpdateItem` | `cartWatchItemsTable.tableArn` |
| `scheduler:DeleteSchedule` / `GetSchedule` | `arn:aws:scheduler:{region}:{account}:schedule/default/cart-*` |
| `kms:Encrypt` / `Decrypt` | `props.platformStack.kmsKey.keyArn` |
| `logs:CreateLogStream` / `PutLogEvents` | 該当 LogGroup |

#### 3.1.3 `cart-list-lambda-role`

| 権限 | Resource |
|---|---|
| `dynamodb:Query` / `GetItem` | `cartWatchItemsTable.tableArn` + `/index/GSI1-status` |
| `kms:Decrypt` | `props.platformStack.kmsKey.keyArn` |
| `logs:CreateLogStream` / `PutLogEvents` | 該当 LogGroup |

#### 3.1.4 `cart-push-token-lambda-role`

| 権限 | Resource |
|---|---|
| `dynamodb:GetItem` / `UpdateItem` | `props.authStack.usersTable.tableArn` |
| `mobiletargeting:UpdateEndpoint` | `arn:aws:mobiletargeting:{region}:{account}:apps/{eumAppId}/endpoints/*` |
| `kms:Encrypt` / `Decrypt` | `props.platformStack.kmsKey.keyArn` |
| `logs:CreateLogStream` / `PutLogEvents` | 該当 LogGroup |

#### 3.1.5 `notification-dispatcher-lambda-role`

| 権限 | Resource |
|---|---|
| `dynamodb:GetItem` / `UpdateItem` | `cartWatchItemsTable.tableArn` |
| `dynamodb:GetItem` | `props.authStack.usersTable.tableArn` |
| `dynamodb:GetItem` | `props.safeguardStack.safeguardStatesTable.tableArn` |
| `dynamodb:PutItem` | `notificationLogsTable.tableArn` |
| `mobiletargeting:SendMessages` | `arn:aws:mobiletargeting:{region}:{account}:apps/{eumAppId}` *（cdk-nag IAM5 suppression: Endpoint ID 動的）* |
| `sqs:SendMessage` | `notificationDispatcherDlq.queueArn` |
| `kms:Encrypt` / `Decrypt` | `props.platformStack.kmsKey.keyArn` |
| `logs:CreateLogStream` / `PutLogEvents` | 該当 LogGroup |

#### 3.1.6 `cart-attack-scheduler-retry-lambda-role`

| 権限 | Resource |
|---|---|
| `dynamodb:Query` | `cartWatchItemsTable.tableArn/index/GSI1-status` |
| `dynamodb:GetItem` / `UpdateItem` | `cartWatchItemsTable.tableArn` |
| `scheduler:CreateSchedule` / `GetSchedule` | `arn:aws:scheduler:{region}:{account}:schedule/default/cart-*` |
| `iam:PassRole` | `schedulerInvokeRole.roleArn` |
| `kms:Encrypt` / `Decrypt` | `props.platformStack.kmsKey.keyArn` |
| `logs:CreateLogStream` / `PutLogEvents` | 該当 LogGroup |
| `cloudwatch:PutMetricData` | `*` *（cdk-nag IAM5 suppression: EMF metric は wildcard 必須）* |

### 3.2 EventBridge Scheduler Invoke Role

```typescript
this.schedulerInvokeRole = new iam.Role(this, 'SchedulerInvokeRole', {
  roleName: resourceName(props, 'cart-scheduler-invoke-role'),
  assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com', {
    conditions: {
      StringEquals: { 'aws:SourceAccount': this.account },
    },
  }),
});

this.schedulerInvokeRole.addToPolicy(new iam.PolicyStatement({
  actions: ['lambda:InvokeFunction'],
  resources: [
    this.notificationDispatcherFunction.functionArn,
    this.cartAttackSchedulerRetryFunction.functionArn,
  ],
}));
```

> **Confused Deputy 防御（SECURITY-08 整合）**: `aws:SourceAccount` 条件で同一 AWS アカウント内のみ Scheduler が assume 可能。

---

## 4. End User Messaging Push（Q5=A 反映）

### 4.1 CDK 定義（CfnApp + CfnAPNSChannel + CfnGCMChannel）

```typescript
// infra/lib/cart-stack.ts
import * as pinpoint from 'aws-cdk-lib/aws-pinpoint';

const eumApp = new pinpoint.CfnApp(this, 'CartEumApp', {
  name: resourceName(props, 'cart'),
  tags: { Environment: props.envName, Unit: 'cart', Owner: 'member-d', CostCenter: 'yudane-hackathon-2026' },
});

// dev 環境のみ APNs Sandbox cert
if (props.envName === 'dev') {
  new pinpoint.CfnAPNSSandboxChannel(this, 'ApnsSandboxChannel', {
    applicationId: eumApp.ref,
    enabled: true,
    // .p8 Key 値は AWS Secrets Manager から動的注入（CDK Custom Resource）
    tokenKey: cdk.SecretValue.secretsManager('yudane-cart-dev-apns-sandbox-key').toString(),
    tokenKeyId: cdk.SecretValue.secretsManager('yudane-cart-dev-apns-sandbox-key-id').toString(),
    teamId: cdk.SecretValue.secretsManager('yudane-cart-dev-apns-team-id').toString(),
    bundleId: 'jp.amazon.yudane.dev',
  });
}

// prd 環境のみ APNs Production cert（B-504 backlog 完了後に有効化）
if (props.envName === 'prd') {
  new pinpoint.CfnAPNSChannel(this, 'ApnsChannel', {
    applicationId: eumApp.ref,
    enabled: true,
    tokenKey: cdk.SecretValue.secretsManager('yudane-cart-prd-apns-key').toString(),
    tokenKeyId: cdk.SecretValue.secretsManager('yudane-cart-prd-apns-key-id').toString(),
    teamId: cdk.SecretValue.secretsManager('yudane-cart-prd-apns-team-id').toString(),
    bundleId: 'jp.amazon.yudane',
  });
}

new pinpoint.CfnGCMChannel(this, 'GcmChannel', {
  applicationId: eumApp.ref,
  enabled: true,
  apiKey: cdk.SecretValue.secretsManager(`yudane-cart-${props.envName}-fcm-server-key`).toString(),
});

// SSM Parameter 登録
new ssm.StringParameter(this, 'EumApplicationIdParam', {
  parameterName: `${ssmPathPrefix}/eum-application-id`,
  stringValue: eumApp.ref,
});
```

### 4.2 名前空間移行リスク（Plan v3 Q5 注記）

旧 Pinpoint EoL 2026-10-30 で `aws-mobiletargeting` / `aws-pinpoint` 名前空間が将来置換される可能性あり。**ハッカソン期間（〜2026-06-26）では現状の `aws-pinpoint` で問題なし**。プロダクト化判断時に CDK 公式 changelog 確認が必要。

### 4.3 Apple Developer Program 登録（B-504 backlog 連携）

[B-504](../../../doc/backlog.md) の状態で本 Stack の prd デプロイが gating される:

| B-504 状態 | 本 Stack の prd Stack の挙動 |
|---|---|
| 未登録 | prd Stack はデプロイ可能だが `CfnAPNSChannel` を Skip（条件分岐で `enabled: false`）、Push は dev 環境のみで実機検証 |
| 登録完了（〜2026-06-12） | prd Stack 再デプロイで `CfnAPNSChannel` 有効化、決勝デモで本番 Push 可能 |
| 期限超過 | Member A エスカレーション、決勝デモシナリオから Push パート縮退 |

---

## 5. SNS Topic + Slack Webhook（Q6=A' 反映）

### 5.1 CDK 定義

```typescript
// infra/lib/cart-stack.ts
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subs from 'aws-cdk-lib/aws-sns-subscriptions';

this.cartAlertTopic = new sns.Topic(this, 'CartAlertTopic', {
  topicName: resourceName(props, 'cart-alerts'),
  displayName: `YUDANE Cart Alerts (${props.envName})`,
  masterKey: props.platformStack.kmsKey,  // KMS 暗号化（SECURITY-01）
});

// Slack Webhook Subscription（Lambda で Webhook を呼ぶ patch、SNS の HTTPS subscription は Slack 形式と非互換のため）
const slackBridgeFunction = new lambda.Function(this, 'SlackBridgeFunction', {
  functionName: resourceName(props, 'cart-slack-bridge'),
  runtime: lambda.Runtime.PYTHON_3_13,
  architecture: lambda.Architecture.ARM_64,
  memorySize: 128,
  timeout: Duration.seconds(10),
  handler: 'slack_bridge.lambda_handler',
  code: lambda.Code.fromAsset('../backend', { /* bundling */ }),
  environment: {
    SLACK_WEBHOOK_SECRET_ARN: `arn:aws:secretsmanager:${this.region}:${this.account}:secret:yudane-cart-${props.envName}-slack-webhook-url-*`,
  },
});

slackBridgeFunction.addToRolePolicy(new iam.PolicyStatement({
  actions: ['secretsmanager:GetSecretValue'],
  resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:yudane-cart-${props.envName}-slack-webhook-url-*`],
}));

this.cartAlertTopic.addSubscription(new subs.LambdaSubscription(slackBridgeFunction));

// SSM Parameter 登録（将来 PlatformStack alertTopic と統合する際に参照）
new ssm.StringParameter(this, 'AlertTopicArnParam', {
  parameterName: `${ssmPathPrefix}/alert-topic-arn`,
  stringValue: this.cartAlertTopic.topicArn,
});
```

### 5.2 SECURITY 整合（Plan v3 Q6 修正反映）

- **SECURITY-01（暗号化）**: SNS Topic に KMS CMEK、Secrets Manager で Slack Webhook 暗号化
- **SECURITY-09（ハードニング: デフォルト認証情報禁止）**: コード・ドキュメントに Webhook URL を直接記載しない
- **AGENTS.md §8**: 認証情報は AWS Secrets Manager / SSM 経由で管理

### 5.3 将来統合手順（PlatformStack `alertTopic` 整備時）

1. Unit-1 owner Member A が PlatformStack に `alertTopic: sns.Topic` を追加（観測性スタック [B-001](../../../doc/backlog.md) 本実装時）
2. CartStack の `cartAlertTopic.addSubscription(new SnsSubscription(props.platformStack.alertTopic))` を追加
3. Cart 側 Slack Webhook サブスクリプションを削除、PlatformStack 側に移管
4. backlog エントリは削除せず「ステータス: 採用済み（YYYY-MM-DD）」を末尾追記

---

## 6. CloudWatch Alarms 5 系統（Q6=A' SNS 連携）

[functional-design.md §3.3](../functional-design/functional-design.md#33-cloudwatch-alarms5-巡目追加issue-z) の Alarm 1〜5 すべての SNS Action を `cartAlertTopic` に変更。

```typescript
// 既存の CDK 定義の addAlarmAction を全 5 Alarm で更新
new cloudwatch.Alarm(this, 'NotificationDelayAlarm', { /* ... */ })
  .addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

// （他 4 Alarm も同様）
```

| Alarm | メトリクス | 閾値 | 通知先 |
|---|---|---|---|
| Alarm 1: DLQ depth | `aws/sqs:ApproximateNumberOfMessagesVisible`（NotificationDispatcherDlq）| > 1 / 5min | cartAlertTopic → Slack |
| Alarm 2: Notification 遅延 | `cart.notification.delay_seconds` p99 | > 60s / 5min | 同上 |
| Alarm 3: Scheduler create_failed | `cart.scheduler.create_failed` | > 5 / 5min | 同上 |
| Alarm 4: Lambda Error | `aws/lambda:Errors`（6 Lambda 個別） | > 3 / 5min | 同上 |
| Alarm 5: retry_failed（NFR Q4=A'） | `cart.scheduler.retry_failed` | > 5 / 15min | 同上 |

---

## 7. cdk-nag suppressions 完全版

```typescript
// infra/lib/cart-stack.ts
import { NagSuppressions } from 'cdk-nag';

NagSuppressions.addResourceSuppressions(
  this.notificationDispatcherFunction,
  [{
    id: 'AwsSolutions-IAM5',
    reason: 'mobiletargeting:SendMessages の Resource は EUM Endpoint ID で動的決定、IAM Resource を事前特定不可',
    appliesTo: ['Resource::arn:aws:mobiletargeting:*:*:apps/*'],
  }],
  true,
);

NagSuppressions.addResourceSuppressions(
  this.cartAttackSchedulerRetryFunction,
  [{
    id: 'AwsSolutions-IAM5',
    reason: 'CloudWatch EMF metric の PutMetricData は wildcard Resource 必須（AWS 標準）',
    appliesTo: ['Resource::*', 'Action::cloudwatch:PutMetricData'],
  }],
  true,
);

NagSuppressions.addResourceSuppressions(
  notificationDispatcherDlq,
  [{
    id: 'AwsSolutions-SQS3',
    reason: 'PlatformStack の KMS CMEK で暗号化済み、別 DLQ は不要',
  }],
);

NagSuppressions.addResourceSuppressions(
  this.cartIntakeFunction,
  [{
    id: 'AwsSolutions-IAM5',
    reason: 'scheduler:CreateSchedule は Schedule 名 prefix `cart-*` で範囲限定済み（FD §3.2 整合）',
    appliesTo: ['Resource::arn:aws:scheduler:*:*:schedule/default/cart-*'],
  }],
);
```

**cdk-nag pass 期待**: 上記 suppression で全 cdk-nag check が green。Snapshot TDD（[functional-design.md §0.1](../functional-design/functional-design.md)）で固定。

---

## 8. タグ戦略（Q7=A 必須 4 タグ）

```typescript
// infra/lib/cart-stack.ts のコンストラクタ末尾
Tags.of(this).add('Environment', props.envName);
Tags.of(this).add('Unit', 'cart');
Tags.of(this).add('Owner', 'member-d');
Tags.of(this).add('CostCenter', 'yudane-hackathon-2026');
```

| タグ | 用途 | 値の例 |
|---|---|---|
| `Environment` | 環境別コスト追跡 | `dev` / `prd` |
| `Unit` | Unit 別コスト追跡 | `cart` |
| `Owner` | 責任者特定（オンコール対応） | `member-d` |
| `CostCenter` | ハッカソン全体クレジット消費把握 | `yudane-hackathon-2026` |

> **AWS Cost Explorer 連携**: `Environment=prd AND Unit=cart` で本 Unit の prd コストを月次追跡可能。

---

## 9. SSM Parameter 一覧（Cross-Stack Output）

| Parameter Path | 値 | 参照先 |
|---|---|---|
| `/yudane/{env}/cart/cart-watch-items-table-arn` | DDB ARN | Unit-3 Debate（cart-attack 経由のセッション履歴記録の参照）/ Unit-8 Report（北極星指標集計）|
| `/yudane/{env}/cart/notification-logs-table-arn` | DDB ARN | Unit-8 Report（通知 tap 率集計）|
| `/yudane/{env}/cart/eum-application-id` | EUM App ID | 他 Unit が Push 配信する場合（Unit-6 Calendar / Unit-8 Report 経由）|
| `/yudane/{env}/cart/alert-topic-arn` | SNS Topic ARN | 将来 PlatformStack `alertTopic` 統合時に参照 |

---

## 10. 物理マッピング表（論理 → AWS service → 環境別差異）

[logical-components.md](../nfr-design/logical-components.md) の論理コンポーネントを物理に展開。

| 論理コンポーネント | AWS service | dev 設定 | prd 設定 |
|---|---|---|---|
| M-05 CartInterceptScreen | Expo App / RN | EAS Build dev profile | EAS Build production profile |
| M-08 ShareExtensionNativeModule | iOS Share Extension（Swift）| dev provisioning profile | App Store Distribution profile |
| M-09 PushNotificationHandler | expo-notifications + EUM SDK | APNs Sandbox + FCM dev token | APNs Production + FCM prod token |
| B-04 CartIntakeHandler | Lambda Python 3.13 ARM64 | 512MB / SnapStart ON / Reserved 共有 100 | 同左 |
| B-04 CartDismissHandler | Lambda Python 3.13 ARM64 | 256MB / SnapStart ON / 共有 100 | 同左 |
| B-04 CartListHandler | Lambda Python 3.13 ARM64 | 256MB / 共有 100 | 同左 |
| B-04 PushTokenRegister | Lambda Python 3.13 ARM64 | 256MB / 共有 100 | 同左 |
| B-05 CartAttackScheduler | （ライブラリ、B-04 内同期）| — | — |
| B-05 cart_attack_scheduler_retry | Lambda Python 3.13 ARM64 + EventBridge Scheduler rate(15min) | 512MB / Reserved 10 | 同左 |
| B-06 NotificationDispatcher | Lambda Python 3.13 ARM64 | 512MB / SnapStart ON / Reserved 50 / DLQ | 同左 |
| CartWatchItems | DynamoDB On-Demand | KMS CMEK / TTL / PITR off / RemovalPolicy DESTROY | KMS CMEK / TTL / PITR on / RemovalPolicy RETAIN / DeletionProtection on |
| NotificationLogs | DynamoDB On-Demand | 同上 | 同上 |
| EUM Application | Pinpoint App + APNs/FCM Channel | APNs Sandbox cert | APNs Production cert（B-504 完了後）|
| Schedule（攻撃ジョブ）| EventBridge Scheduler One-time | default Group | default Group |
| Schedule（retry）| EventBridge Scheduler rate(15min)| default Group | default Group |
| Cart Alert Topic | SNS Topic + KMS | dev Slack Webhook（`#yudane-dev`）| prd Slack Webhook（`#yudane-emergency`）|
| Slack Bridge Lambda | Lambda Python 3.13 | 128MB | 同左 |
| Notification DLQ | SQS Standard + KMS | retentionPeriod 14 日 | 同左 |
| API Gateway 統合 | API Gateway REST（Unit-1 owner）| — | — |

---

## 11. 容量・上限のサニティチェック

| リソース | AWS 公式上限 | 本 Unit MVP 想定 | 本 Unit 本番化想定 | 余裕度 |
|---|---|---|---|---|
| EventBridge Scheduler | 100 万 Schedule / アカウント | 数百件同時 | 75K 件同時保持 | 13× 余裕 |
| Lambda 同時実行 | 1000 / アカウント（標準）| 50 同時 | 160 同時 | 6× 余裕 |
| DDB On-Demand | リージョンごと AccountLimit | 数千 RCU/WCU | 165 万 WCU/月 + 1500 万 RCU/月 | 十分余裕 |
| End User Messaging Push | 100 万通知/月（無料枠）| 数百通知 | 225 万通知（超過分 $2.5） | 月内 |
| SNS Topic | 10 万 Topic / アカウント | 1 Topic | 1 Topic | ∞× 余裕 |

---

## 12. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: Cross-Stack 依存（Q1）/ デプロイ順序 / sandbox 戦略（Q9）で Unit-5 と他 Unit の責任分界が物理レベルで明示、IAM 30 statement で最小権限化 |
| 創造性とテーマ適合性 | 維持: テーマ依存度は低いステージだが、3 段追撃の物理基盤を堅実に整備 |
| ドキュメント品質 | **強化**: 物理マッピング表 + IAM 詳細 + 容量サニティ + 名前空間移行リスク注記で、評価者が本 Stack の運用を 1 文書で追跡可能 |
| AI-DLC プロセス（予選評価軸） | **強化**: Plan v3 Q1〜Q10 確定 → 物理マッピングまでの一気通貫展開、再検証ログ（v1 → v2 → v3）で改善履歴を可視化 |
