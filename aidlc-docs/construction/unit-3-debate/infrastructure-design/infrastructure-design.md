# Unit-3 Debate — Infrastructure Design

> Unit-3 Debate（`debate-stack`）の AWS インフラ設計。NFR Design の論理コンポーネント / 設計パターンを実 AWS サービスへマッピング。
>
> 参照: [logical-components.md](../nfr-design/logical-components.md) / [nfr-design-patterns.md](../nfr-design/nfr-design-patterns.md) / [tech-stack-decisions.md](../nfr-requirements/tech-stack-decisions.md) / [Unit-1 infrastructure-design.md](../../unit-1-platform/infrastructure-design/infrastructure-design.md) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md)
>
> 確定方針（Functional Design v3.4 の Q1〜Q17 + NFR Design 採用パターン）: AgentCore Runtime + Memory（apne1 GA）+ Bedrock Haiku 4.5（SSM 切替）+ Bedrock Guardrails 8 トピック + Cooldowns DDB + S3 Memory Export + Athena/Glue + Cognito Authorizer 直接設定 + Public Network + RuntimeEndpoint live + canary
>
> リージョン: `ap-northeast-1`

---

## 0. サマリ

`debate-stack` は Unit-1 `platform-stack` を継承し、AgentCore Runtime + Memory + Bedrock + Cooldowns DDB + S3 Memory Export を構成する。**Unit-1 と異なり API Gateway / Lambda Authorizer / VPC は使わない**（AgentCore Runtime が Mobile から直接 InvokeAgentRuntime で呼ばれ、Cognito Authorizer を直接設定、Public Network 配置）。

| カテゴリ | AWS サービス | 確定根拠 |
|---|---|---|
| Agent Runtime | Amazon Bedrock AgentCore Runtime（Direct Code Deploy）| Q1=C / Q15=A |
| Agent 認証 | AgentCore Cognito Authorizer（Unit-1 User Pool 再利用）| Q5=A / SECURITY-08 |
| Agent ネットワーク | Public Network（VPC 配置なし）| Q6=A / NFR-SEC-DEBATE-11 |
| Agent エンドポイント | RuntimeEndpoint × 2（live + canary）| Q17=B / NFR-AVAIL-DEBATE-06 |
| Agent Memory | AgentCore Memory（組み込み 2 + custom 1、custom は P1 で追加）| Q1=C / Q10=B / Q16=B |
| LLM | Bedrock Haiku 4.5（SSM 切替、IAM は Sonnet 4.6 先行付与）| Q4=A+SSM / NFR-SEC-DEBATE-07 |
| LLM ガードレール | Bedrock Guardrails（DENIED_TOPICS = NG-1〜8、streaming 対応）| Q12=D 第 2 層 / NFR-ETHICS-DEBATE-04 |
| データ（自前）| DynamoDB Cooldowns（On-Demand + KMS + PITR + TTL）| Q2=C / NFR-AVAIL-DEBATE-04 |
| データ（保全）| S3 Memory Export + Lifecycle 365 日 + Athena view + Glue Crawler | Q13=D / NFR-COST-DEBATE-04/05 |
| 観測 | CloudWatch Logs / Metrics / Alarms + X-Ray + SNS（Unit-1 alerts-topic 再利用）| NFR-OBS-DEBATE-01〜12 |
| セキュリティ | Unit-1 KMS 再利用 + IAM 個別ロール 2 種（Runtime / Memory Export）| SECURITY-01/06 |
| 設定 | SSM Parameter Store 8 個（runtime-arn / memory-id / endpoint-live-arn / endpoint-canary-arn / model-id / memory-export-bucket-arn / cooldowns-table-arn / kill-switch）| Q4=A+SSM / SSM-01 |

---

## 1. AgentCore Runtime（Q1=C / Q5=A / Q6=A / Q15=A、PAT-D-PERF-01/02 / SEC-01）

### 1.1 リソース定義

```typescript
// infra/lib/debate-stack.ts（CDK Snapshot TDD で先に test 作成）
import { aws_bedrockagentcore as agentcore } from 'aws-cdk-lib';

const debateRuntime = new agentcore.Runtime(this, 'DebateRuntime', {
  runtimeName: `yudane-debate-${envName}`,
  description: 'YUDANE Unit-3 Debate Strands Agent runtime',

  // Direct Code Deploy（S3 zip、ECR 不要、2025-11 GA）
  artifact: agentcore.RuntimeArtifact.fromAsset(
    path.join(__dirname, '../../backend/src/debate'),
    {
      bundling: {
        image: cdk.DockerImage.fromRegistry('public.ecr.aws/sam/build-python3.13:latest'),
        command: [
          'bash', '-c',
          'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output',
        ],
      },
    },
  ),

  // 認証認可（Q5=A、Unit-1 Cognito User Pool 再利用）
  authorizerConfiguration: agentcore.RuntimeAuthorizerConfiguration.cognito({
    userPoolId,           // CDK synth 時に SSM `/yudane/<env>/platform/userpool-id` を `valueForStringParameter` で解決
    clientIds: [userPoolClientId],  // 同じく synth 時 SSM 解決
  }),

  // ネットワーク（Q6=A、Public Network、ENI コールドスタート回避）
  // Unit-1 platform-stack の `lambda-sg-id` は参照しない（VPC 内配置をしないため、SECURITY-07 の例外）
  networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),

  // タイマー二段の物理層（PAT-D-PERF-02、business-rules カタログ §12）
  lifecycleConfiguration: {
    idleTimeoutSeconds: 120,    // Strands Agent 90s 厳守の保険として +30s バッファ
    maxLifetimeSeconds: 120,    // microVM 強制終了（Strands Agent 既に session_complete yield 済の最終 fail-safe）
  },

  environment: {
    ENV_NAME: envName,
    DEBATE_MEMORY_ID: debateMemory.memoryId,
    BEDROCK_GUARDRAIL_ID: debateGuardrail.attrGuardrailId,
    COOLDOWNS_TABLE_NAME: cooldownsTable.tableName,
  },
});
```

### 1.2 タイマー対応マトリクス（PAT-D-PERF-02、リテラルは business-rules §12 を正本とする）

| 経過時間 | 主体 | 動作 |
|---|---|---|
| 0 〜 `DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS`（80s）| Strands Agent | 通常 streaming |
| 80 〜 `DEBATE_MAX_DURATION_SECONDS`（90s）| Strands Agent | graceful shutdown 起動、サマリ生成 + 綺麗な session_complete |
| 90s | Strands Agent | hard cutoff（保険、graceful 失敗時）= session_complete reason='hard_timeout' を yield |
| `RUNTIME_IDLE_TIMEOUT_SECONDS` / `RUNTIME_MAX_LIFETIME_SECONDS`（120s）| AgentCore Runtime（マネージド層）| microVM 強制停止（Strands Agent 既に session_complete yield 済の保険、Mobile が接続を継続している場合 410 Gone）|

> **注**: `RUNTIME_IDLE_TIMEOUT_SECONDS` と `RUNTIME_MAX_LIFETIME_SECONDS` は AgentCore Runtime プラットフォーム側の最終 fail-safe であり、Strands Agent コードがこれを待つことはない（90s 時点で session_complete を yield してリターンする）。120s は Strands Agent が応答しない場合の microVM 強制停止までの猶予を与える設計。

### 1.3 IAM Role（Runtime 実行ロール、最小権限 PAT-D-SEC-03）

```
allow:
  - bedrock:InvokeModelWithResponseStream / InvokeModel
    on:
      - arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-haiku-4-5
      - arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-6  # 先行付与（B-305 切替時の AccessDenied 防止）
  - bedrock-agentcore:CreateEvent / GetLastKTurns / RetrieveMemories
    on:
      - <DebateMemory ARN>/namespace/user/debate/*
      - <DebateMemory ARN>/namespace/user/stress/*
      - <DebateMemory ARN>/namespace/user/m1m2/*  # P1
    # 注: actor_id 単位の分離は IAM では不可能（単一 Runtime IAM Role が全ユーザーの Memory にアクセス）。
    #     実際の actor_id 単位分離は、Strands Agent コード内の f-string で
    #     `f'/user/.../{actor_id}/'` を必ず付与し、CI Lint で `{actor_id}` を抜いた汎用 namespace を fail させる
    #     （PAT-D-SEC-02 / NFR-SEC-DEBATE-04 と整合）
  # 注: bedrock-agentcore:DeleteAllLongTermMemoriesInNamespace は Unit-7 削除バッチ Lambda の IAM Role に付与（business-rules MEMORY-08 / NFR-SEC-DEBATE-05）。Unit-3 Runtime には付与しない（最小権限）
  - dynamodb:GetItem / UpdateItem
    on:
      - <CooldownsTable ARN>
  - kms:Decrypt / GenerateDataKey
    on:
      - <Unit-1 KMS Key ARN>
  - ssm:GetParameter
    on:
      - /yudane/<env>/debate/model-id
      - /yudane/<env>/debate/kill-switch
      - /yudane/<env>/platform/userpool-id
      - /yudane/<env>/platform/userpool-client-id
  - logs:CreateLogStream / PutLogEvents
    on: <CloudWatch Log Group>
  - cloudwatch:PutMetricData  # EMF（PAT-D-OBS-02）
    on: yudane.debate ネームスペース
  - xray:PutTraceSegments / PutTelemetryRecords  # X-Ray（NFR-OBS-DEBATE-10）
```

cdk-nag `AwsSolutionsChecks` の `aws-solutions-iam5` Suppression は Bedrock 2 ARN ワイルドカードのみ許可（理由: model-id 切替時の AccessDenied 防止）。

### 1.4 RuntimeEndpoint（Q17=B、PAT-D-OBS-03）

```typescript
const liveEndpoint = new agentcore.RuntimeEndpoint(this, 'DebateRuntimeLive', {
  runtime: debateRuntime,
  name: 'live',
});
const canaryEndpoint = new agentcore.RuntimeEndpoint(this, 'DebateRuntimeCanary', {
  runtime: debateRuntime,
  name: 'canary',
});  // P1 で追加（task-breakdown Phase 5）
```

| Endpoint | 用途 | Mobile qualifier | デプロイ Phase |
|---|---|---|---|
| `live` | 通常運用 | `'live'` | P0（Phase 1） |
| `canary` | 6/25 staging で 30 分カナリア / プロンプト A/B | `'canary'` | P1（Phase 5） |

dev / staging endpoint の Auto-Pause は **B-307 backlog**（決勝後にコスト最適化）。

---

## 2. AgentCore Memory（Q1=C / Q10=B / Q16=B / Q13=D）

### 2.1 Memory リソース定義

```typescript
const debateMemory = new agentcore.Memory(this, 'DebateMemory', {
  memoryName: `yudane_debate_${envName}_memory`,  // a-zA-Z0-9_ のみ、ハイフン不可
  description: 'YUDANE Unit-3 Debate Memory: events + 3 strategies',

  // 90 日生存（events + strategy records 共通、business-rules MEMORY-02）
  expirationDuration: cdk.Duration.days(90),

  // Unit-1 KMS 再利用（SECURITY-01）
  kmsKey: platformKmsKey,

  memoryStrategies: [
    // === P0 組み込み 2 種（Phase 1 で deploy、task-breakdown T1.1）===
    agentcore.MemoryStrategyBase.userPreference({
      name: 'debate_outcomes',
      namespaces: ['/user/debate/{actorId}/'],
    }),
    agentcore.MemoryStrategyBase.semantic({
      name: 'stress_signals',
      namespaces: ['/user/stress/{actorId}/'],
    }),
    // === P1 custom Strategy（Phase 4 T4.2 で `addStrategy` または再 deploy で追加、Q16=B）===
    // 注: P0 デプロイ時点ではこの 1 行をコメントアウト、Phase 4 で有効化する。
    //     migration 検証は task-breakdown.md リスク表「AgentCore Memory addStrategy migration」項を参照
    agentcore.MemoryStrategyBase.custom({
      name: 'm1_m2_axis_extractor',
      namespaces: ['/user/m1m2/{actorId}/'],
      configuration: {
        // backend/src/debate/prompts/m1_m2_axis_extractor.py の M1_M2_EXTRACTION_PROMPT を参照
        modelId: ssm.StringParameter.valueForStringParameter(
          this, `/yudane/${envName}/debate/model-id`),
      },
    }),
  ],

  // Q13=D: S3 並行書き出し（90 日超のデータも 365 日保全）
  streamDeliveryResources: {
    s3: {
      bucket: memoryExportBucket,
      prefix: 'events/{year}/{month}/{day}/{hour}/',
      kmsKey: platformKmsKey,
    },
  },
});
```

### 2.2 Strategy Phase 計画（PAT-D-PERF-03、MEMORY-09 で top_k <= 5）

| Phase | Strategy | namespace | top_k | task-breakdown |
|---|---|---|---|---|
| **P0** | userPreference `debate_outcomes` | `/user/debate/{actorId}/` | 5 | Phase 2 T2.3 |
| **P0** | semantic `stress_signals` | `/user/stress/{actorId}/` | 3 | Phase 2 T2.3 |
| **P1** | custom `m1_m2_axis_extractor` | `/user/m1m2/{actorId}/` | 3 | Phase 4 T4.1〜4.3 |

### 2.3 namespace 分離（PAT-D-SEC-02、NFR-SEC-DEBATE-04）

全 namespace に `{actorId}` を含める。コードレベルで `f'/user/.../{actor_id}/'` の f-string 生成を CI Lint で強制（`{actor_id}` を抜いた汎用 namespace は fail）。横断 retrieval 禁止。

---

## 3. Bedrock Guardrails（Q12=D 第 2 層、NFR-ETHICS-DEBATE-04）

### 3.1 リソース定義

```typescript
const debateGuardrail = new bedrock.CfnGuardrail(this, 'DebateGuardrail', {
  name: `yudane-debate-${envName}-guardrail`,
  description: 'YUDANE Unit-3 NG-1〜8 検出、特に NG-6 滑落防止',

  topicPolicyConfig: {
    topicsConfig: [
      { name: 'illegal-activity',         type: 'DENY', /* NG-1 */ },
      { name: 'health-harm',              type: 'DENY', /* NG-2 */ },
      { name: 'discrimination',           type: 'DENY', /* NG-3 */ },
      { name: 'minor-targeting',          type: 'DENY', /* NG-4 */ },
      { name: 'mental-health',            type: 'DENY', /* NG-5 */ },
      { name: 'threat-or-guilt-coercion', type: 'DENY', /* NG-6 最重要 */ },
      { name: 'personal-data-misuse',     type: 'DENY', /* NG-7 */ },
      { name: 'associates-violation',     type: 'DENY', /* NG-8 */ },
    ],
  },
  contentPolicyConfig: {
    filtersConfig: [
      { type: 'HATE',     inputStrength: 'HIGH', outputStrength: 'HIGH' },
      { type: 'VIOLENCE', inputStrength: 'HIGH', outputStrength: 'HIGH' },
      { type: 'SEXUAL',   inputStrength: 'HIGH', outputStrength: 'HIGH' },
      { type: 'INSULTS',  inputStrength: 'HIGH', outputStrength: 'HIGH' },
    ],
  },
  blockedInputMessaging: '入力に NG-1〜8 該当の表現が含まれます',
  blockedOutputsMessaging: 'AI が言葉を選び直しています',
});
```

### 3.2 streaming 連携

Strands Agent の `bedrock_kwargs.guardrailIdentifier` で関連付け。Bedrock 側で `outputAssessments.BLOCKED` を受信した chunk を Strands Agent が `guardrail_blocked` event に変換、`main.py` が `moderation_blocked` event に再ラップして Mobile に yield（PAT-D-RESIL-03）。詳細は [tech-stack-decisions.md §3.1 Bedrock Guardrails 構成](../nfr-requirements/tech-stack-decisions.md) を参照。

---

## 4. データストア

### 4.1 DynamoDB `yudane-debate-<env>-cooldowns`（Q2=C、Unit-3 唯一の自前テーブル）

```typescript
const cooldownsTable = new dynamodb.Table(this, 'CooldownsTable', {
  tableName: `yudane-debate-${envName}-cooldowns`,
  partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
  sortKey:      { name: 'SK', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,    // On-Demand（予測しにくい論破トラフィック）
  encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
  encryptionKey: platformKmsKey,                         // Unit-1 KMS 再利用
  pointInTimeRecovery: true,                             // PITR
  timeToLiveAttribute: 'ttl',                            // 30 日後自動削除
  removalPolicy: envName === 'prd' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
});
```

| キー | 値の例 | 意味 |
|---|---|---|
| PK | `USER#<actorId>` | Cognito JWT.sub |
| SK | `COOLDOWN#current` | 1 ユーザー 1 レコード |

### 4.2 属性スキーマ（業務側は camelCase、Pydantic alias で snake_case 変換）

| 属性 | 型 | 説明 |
|---|---|---|
| `consecutiveRefuses` | Number | 連続拒否カウント（0〜∞、3 到達でクールダウン発動） |
| `cooldownUntil` | String (ISO 8601) | クールダウン解除時刻（active 時のみ存在） |
| `lastRefuseAt` | String (ISO 8601) | 最後の拒否時刻 |
| `ttl` | Number | UNIX timestamp（30 日後、DDB 自動削除） |

### 4.3 S3 Memory Export Bucket（Q13=D、NFR-COST-DEBATE-04/05）

```typescript
const memoryExportBucket = new s3.Bucket(this, 'MemoryExportBucket', {
  bucketName: `yudane-debate-${envName}-memory-export`,
  encryption: s3.BucketEncryption.KMS,
  encryptionKey: platformKmsKey,                          // Unit-1 KMS 再利用
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,      // SECURITY-09
  versioned: true,                                         // 誤削除保護
  lifecycleRules: [{
    id: 'memory-export-lifecycle',
    transitions: [
      { storageClass: s3.StorageClass.INFREQUENT_ACCESS,        transitionAfter: cdk.Duration.days(30) },
      { storageClass: s3.StorageClass.GLACIER_INSTANT_RETRIEVAL, transitionAfter: cdk.Duration.days(90) },
    ],
    expiration: cdk.Duration.days(365),                    // Year 1 退化レポート用
  }],
  removalPolicy: envName === 'prd' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
});

// Glue Crawler 日次（NFR-OBS-DEBATE-12）
const memoryExportCrawler = new glue.CfnCrawler(this, 'MemoryExportCrawler', {
  name: `yudane-debate-${envName}-memory-export-crawler`,
  databaseName: glueDatabase.databaseName,
  schedule: { scheduleExpression: 'cron(0 1 * * ? *)' },  // 毎日 01:00 UTC
  targets: { s3Targets: [{ path: `s3://${memoryExportBucket.bucketName}/events/` }] },
  role: glueCrawlerRole.roleArn,
});
```

Athena view `debate_outcomes_v1` は Code Generation Phase 3 で確定（Unit-8 Dame Report 着手時）。

### 4.4 IAM Memory Export Role

Memory が S3 PutObject するためのロール（CDK が `streamDeliveryResources` 設定で自動生成、確認必須）:

```
allow:
  - s3:PutObject
    on: <MemoryExportBucket ARN>/events/*
  - kms:Encrypt / GenerateDataKey
    on: <Unit-1 KMS Key ARN>
```

---

## 5. SSM Parameter Store 出力（8 個、Q4=A+SSM / SSM-01〜05、NC2-2 kill-switch 追加）

| Parameter | 値の例 | 用途 / 参照経路 | Phase |
|---|---|---|---|
| `/yudane/<env>/debate/runtime-arn` | `arn:aws:bedrock-agentcore:apne1:...:runtime/yudane-debate-dev` | Backend Unit / 運用者の参照用（Mobile は環境変数経由）| P0 |
| `/yudane/<env>/debate/memory-id` | `mem-abc123...` | Unit-7 削除バッチが SSM から取得 | P0 |
| `/yudane/<env>/debate/runtime-endpoint-live-arn` | `arn:...:runtime-endpoint/live` | EAS Build 時に Expo `app.config.js` で SSM CLI 経由取得 → `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` として Mobile アプリにビルド埋め込み | P0 |
| `/yudane/<env>/debate/runtime-endpoint-canary-arn` | `arn:...:runtime-endpoint/canary` | 同上、カナリアビルド時のみ参照 | P1 |
| `/yudane/<env>/debate/model-id` | `anthropic.claude-haiku-4-5` | Strands Agent が起動時 1 回 SSM GetParameter | P0 |
| `/yudane/<env>/debate/memory-export-bucket-arn` | `arn:aws:s3:::yudane-debate-dev-memory-export` | Unit-8 Dame Report Stack が SSM から取得 | P1 |
| `/yudane/<env>/debate/cooldowns-table-arn` | `arn:aws:dynamodb:apne1:...:table/yudane-debate-dev-cooldowns` | Unit-7 Safeguard Stack が SSM から取得 | P0 |
| `/yudane/<env>/debate/kill-switch` | `disabled`（既定）/ `enabled` | Strands Agent が毎セッション開始時に SSM GetParameter（リアルタイム反映、緊急停止用）| P0 |

参照規約:
- **Backend / 他 Unit**: `ssm.StringParameter.valueForStringParameter()`（CDK synth 時）または boto3 `ssm.get_parameter()`（ランタイム）で読み取り
- **Mobile**: Cognito Identity Pool 不採用のため SSM 直接読み取り不可。**EAS Build 時に Expo `app.config.js` 経由で SSM 値を環境変数に展開**（`EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` 等）。値変更時は再ビルド + OTA 更新が必要（4IDC-1 修正）
- **kill-switch**: Strands Agent が毎セッション開始時に SSM GetParameter（その他 7 個は Lambda 起動時 1 回取得）

---

## 6. 観測・アラート（NFR-OBS-DEBATE-01〜12 / NFR-SEC-DEBATE-08）

### 6.1 ログ・トレース

- CloudWatch Log Group: `/aws/bedrock-agentcore/yudane-debate-<env>` 自動生成、保持 90 日（SECURITY-14）
- AgentCore Runtime 標準 OTEL：Strands → Bedrock → Memory の分散トレース → CloudWatch X-Ray
- 構造化監査ログは Unit-1 B-12 AuditLogger Lambda Layer 経由（Powertools）

### 6.2 EMF カスタムメトリクス（NFR-OBS-DEBATE-01〜09）

メトリクス命名は Unit-1 NFR-OBS-02 規約 `<unit>.<domain>.<metric>` に従う:

| メトリクス | 次元（高カーディナリティ回避）| 単位 |
|---|---|---|
| `debate.session_started{trigger}` | trigger=reel_skip / cart_intercept / page_dwell | Count |
| `debate.session_complete{reason}` | reason=agreed / refused / graceful_timeout / hard_timeout / error | Count |
| `debate.agreed{axis}` | axis=fact / psychology / reward | Count（北極星指標）|
| `debate.cooldown_triggered_total` | （actor_id を次元に入れない）| Count |
| `debate.stress_estimated{level}` | level=low / mid / high | Count |
| `debate.moderation_blocked{layer}` | layer=prompt / guardrails / regex | Count |
| `debate.bedrock.input_tokens` `debate.bedrock.output_tokens` | model_id | Tokens |
| `debate.graceful_shutdown_initiated` | （次元なし）| Count |

### 6.3 CloudWatch Alarms（NFR-SEC-DEBATE-08 の 4 種 + NC2-2 の 1 種 = 計 5 種、Unit-1 alerts-topic 再利用）

| Alarm | 閾値 | アクション | 出典 |
|---|---|---|---|
| Bedrock 異常コスト | 日次 $30 超 | SNS `yudane-platform-<env>-alerts` | NFR-SEC-DEBATE-08 |
| Bedrock Throttling | 連続 5 件 | 同上 | NFR-SEC-DEBATE-08 |
| Guardrails BLOCKED 率 | 1% 超 | 同上（プロンプト見直しトリガー）| NFR-SEC-DEBATE-08 |
| Memory retrieve 失敗率 | 5% 超 | 同上 | NFR-SEC-DEBATE-08 |
| **DDB Cooldowns 障害** | get_item / update_item 例外 連続 5 分 | 同上（運用者が SSM kill-switch を 'enabled' に切替）| NFR-AVAIL-DEBATE-04（kill-switch 連動）|

### 6.4 CloudWatch Dashboard（NFR-OBS-DEBATE-11）

`yudane-debate-<env>-dashboard` の 4 ウィジェット:
1. 論破成功率（`debate.agreed` / `debate.session_started` の比率）
2. Bedrock コスト（input_tokens × Haiku 単価 + output_tokens × Haiku 単価）
3. Cooldown 発火（`debate.cooldown_triggered_total`）
4. モデレーション ヒット（`debate.moderation_blocked{layer}` 3 層別）

---

## 7. セキュリティ（SECURITY-01/06/07/08/14、NFR-SEC-DEBATE）

| 項目 | 構成 |
|---|---|
| KMS | Unit-1 platform KMS 再利用（DDB Cooldowns / S3 Memory Export / Memory / Logs 暗号化、SECURITY-01）|
| IAM | Lambda 個別ロール、`*` resource/action 禁止（cdk-nag aws-solutions-iam4/5）。Bedrock 2 ARN ワイルドカードは Suppression に理由コメント必須 |
| ネットワーク | Public Network（Q6=A、ENI コールドスタート不要）。Bedrock / DDB / Memory は AWS 内部経路 |
| 認証認可 | Cognito Authorizer（Q5=A、Unit-1 User Pool 再利用）。actor_id = JWT.sub のみ正（PAT-D-SEC-01）|
| Memory PII | event_metadata に PII を含めない（axis / outcome / turn / stress_level / asin のみ、MEMORY-07 / PAT-D-SEC-02）|
| TLS | InvokeAgentRuntime は HTTPS、SDK 標準で TLS 1.2+ |
| プロンプトインジェクション | base block で「ユーザー入力は引用符で囲まれた内容に限定」を明示、Bedrock Guardrails の prompt attack 検出有効化（NFR-SEC-DEBATE-09）|

---

## 8. 論理 → 物理マッピング表（NFR Design logical-components.md と整合）

| LC | 論理コンポーネント | 物理 AWS リソース |
|---|---|---|
| LC-D-01 | Debate Entrypoint Router | AgentCore Runtime + `backend/src/debate/main.py`（Direct Code Deploy）|
| LC-D-02 | Strands Agent Streaming Pipeline | Strands Agent コード + Bedrock Haiku 4.5 InvokeModelWithResponseStream |
| LC-D-03 | Memory Hook Manager | AgentCore Memory `yudane_debate_<env>_memory` + `memory_hooks.py` |
| LC-D-04 | Prompt Composition Engine | Strands Agent コード `prompts/` 6 モジュール（Direct Code Deploy 同梱）|
| LC-D-05 | Stress Estimator | Strands Agent コード `stress.py` |
| LC-D-06 | Cooldown DDB Adapter | DynamoDB `yudane-debate-<env>-cooldowns` + `cooldown.py` |
| LC-D-07 | 3-Layer Moderation Pipeline | base prompt（Direct Code Deploy）+ Bedrock Guardrails `yudane-debate-<env>-guardrail` + `moderation/callback_handler.py` |
| LC-D-08 | Affirmation Generator | Strands Agent コード `prompts/affirmation.py` + Bedrock Haiku 4.5 InvokeModel |
| LC-D-09 | Mobile AgentCore Client | `@aws-sdk/client-bedrock-agentcore` + `mobile/src/features/debate/agentcore-client.ts`（Mobile 配置、AWS リソースなし）|
| LC-D-10 | Mobile Event Parser | `event-source-parser` + `mobile/src/features/debate/event-parser.ts`（Mobile 配置、AWS リソースなし）|
| LC-D-11 | Memory S3 Export Pipeline | AgentCore Memory `streamDeliveryResources` + S3 `yudane-debate-<env>-memory-export` + Glue Crawler + Athena view |
| LC-D-12 | SSM Configuration Loader | SSM Parameter Store 8 個 + `ssm.py`（Strands Agent コード、Direct Code Deploy 同梱）|

> **Mobile 側 LC-D-09 / LC-D-10 は本 Stack でなく Mobile アプリにビルドされる**（インフラ責務外）。Mobile の Cognito Authorizer 連携は Unit-1 platform-stack の SSM `userpool-id` / `userpool-client-id` を経由。

---

## 9. Extension コンプライアンスサマリ（Infrastructure Design 段階）

| Extension | 状態 | 反映 |
|---|---|---|
| SECURITY-01 暗号化 | ✅ | KMS（DDB Cooldowns / S3 Memory Export / Memory / Logs）、TLS 強制 |
| SECURITY-02 ネットワークログ | ✅ | AgentCore Runtime / Bedrock / Memory の CloudWatch ログ集約 |
| SECURITY-04 HTTP ヘッダ | N/A | モバイルのみ、Web UI なし |
| SECURITY-05 入力検証 | ✅ | Pydantic v2 で DebateInvocationPayload 検証、Cognito Authorizer で JWT 検証 |
| SECURITY-06 IAM 最小権限 | ✅ | Lambda 個別ロール、Bedrock 2 ARN ワイルドカードは Suppression + 理由コメント |
| SECURITY-07 ネットワーク | ✅ | Public Network（Q6=A）、AgentCore マネージドコンテナ |
| SECURITY-08 認可 | ✅ | actor_id = JWT.sub のみ正（PAT-D-SEC-01）|
| SECURITY-09 ハードニング | ✅ | S3 BlockPublicAccess 全有効、エラー秘匿（DomainError）|
| SECURITY-11 セキュアデザイン | ✅ | Cooldown rate limit + Safeguard 連携 |
| SECURITY-13 整合性 | ✅ | 監査ログ + 相関 ID 伝搬（Unit-1 B-12 Layer）|
| SECURITY-14 アラート | ✅ | 5 種 Alarm + SNS、ログ 90 日 |
| cdk-nag | ✅ | AwsSolutionsChecks 全適用、Bedrock 2 ARN Suppression のみ理由コメント |
