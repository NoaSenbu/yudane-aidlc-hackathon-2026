# Unit-3 Debate — Tech Stack Decisions

> Unit-3 Debate で実体化する技術選定の確定と根拠。tech.md / Unit-1 の決定を踏襲しつつ、AgentCore Runtime + Memory + Bedrock Haiku 4.5 + Strands Agent の Unit-3 固有スタックを確定する。
>
> 参照: [nfr-requirements.md](./nfr-requirements.md) / [Functional Design](../functional-design/) / [Unit-1 tech-stack-decisions.md](../../unit-1-platform/nfr-requirements/tech-stack-decisions.md) / [要件書 §7](../../../inception/requirements/requirements.md) / [tech.md](../../../../.kiro/steering/tech.md)
>
> 確定方針（[plan v3.3](../functional-design/functional-design-plan.md#6-decision-recordv33-確定2026-05-29)）: Q1=C / Q3=A / Q4=A+SSM / Q5=A / Q6=A / Q7=A / Q11=A+graceful shutdown 80s / Q12=D 多層 / Q13=D+S3 / Q15=A / Q16=B / Q17=B live+canary

---

## 0. 前提

技術スタックの大枠は [要件書 §7](../../../inception/requirements/requirements.md) と Unit-1 で確定済み。本書は **Unit-3 が実際に導入する AgentCore + Strands Agent + Bedrock の具体ライブラリとバージョン方針** を確定する。

Unit-1 から継承する横断スタック（モノレポ / Mobile RN / Backend Python 3.13 / Pydantic v2 / Lambda Powertools / boto3 / Hypothesis / fast-check 等）は本書では繰り返さない。

---

## 1. AgentCore（Unit-3 固有のメインスタック）

| 項目 | 決定 | バージョン方針 | 根拠 |
|---|---|---|---|
| Runtime | Amazon Bedrock AgentCore Runtime | Tokyo apne1 GA | plan v3 リージョン可用性確認 |
| Memory | Amazon Bedrock AgentCore Memory | apne1 GA | Q1=C / Q10=B / Q16=B |
| Identity | AgentCore Cognito Authorizer 直接設定 | — | Q5=A、Unit-1 既存 Cognito User Pool 再利用 |
| CDK ライブラリ | `aws-cdk-lib/aws-bedrockagentcore` | aws-cdk-lib v2 系最新（L2 安定）| plan v3 CDK 適性確認 |
| 互換性ノート | apne1 で Runtime / Memory / Gateway / Identity 全機能 GA、Direct Code Deploy（S3 zip、ECR 不要、2025-11 GA）| — | 採用判断時 Web 検索確認 |

### 1.1 Direct Code Deploy 設定方針

```typescript
// infra/lib/debate-stack.ts
import { aws_bedrockagentcore as agentcore } from 'aws-cdk-lib';

const debateRuntime = new agentcore.Runtime(this, 'DebateRuntime', {
  runtimeName: `yudane-debate-${envName}`,
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
  // ...
});
```

- ECR 不要、S3 zip での deploy（コスト削減 + シンプル）
- requirements.txt の依存を Lambda レイヤではなく runtime artifact に同梱（Strands SDK は依存が比較的軽量）

### 1.2 RuntimeEndpoint 設定（Q17=B + v3.3 M-5）

各 Stack（debate-dev / debate-staging / debate-prd）内に `live` + `canary` の 2 endpoint:

```typescript
const liveEndpoint = new agentcore.RuntimeEndpoint(this, 'DebateRuntimeLive', {
  runtime: debateRuntime,
  name: 'live',
});
const canaryEndpoint = new agentcore.RuntimeEndpoint(this, 'DebateRuntimeCanary', {
  runtime: debateRuntime,
  name: 'canary',
});
```

### 1.3 Memory 設定（Q1=C / Q13=D+S3 / Q16=B）

```typescript
const debateMemory = new agentcore.Memory(this, 'DebateMemory', {
  memoryName: `yudane_debate_${envName}_memory`,  // a-zA-Z0-9_ のみ、ハイフン不可
  expirationDuration: cdk.Duration.days(90),       // events + strategy records 共通
  kmsKey: platformKmsKey,                          // Unit-1 KMS 再利用
  memoryStrategies: [
    agentcore.MemoryStrategyBase.userPreference({
      name: 'debate_outcomes',
      namespaces: ['/user/debate/{actorId}/'],
    }),
    agentcore.MemoryStrategyBase.semantic({
      name: 'stress_signals',
      namespaces: ['/user/stress/{actorId}/'],
    }),
    // P1 で追加
    agentcore.MemoryStrategyBase.custom({
      name: 'm1_m2_axis_extractor',
      namespaces: ['/user/m1m2/{actorId}/'],
      configuration: { /* Haiku 4.5 ベースの抽出プロンプト */ },
    }),
  ],
  streamDeliveryResources: {
    s3: {
      bucket: memoryExportBucket,
      prefix: 'events/{year}/{month}/{day}/{hour}/',
      kmsKey: platformKmsKey,
    },
  },
});
```

---

## 2. Strands Agent SDK（Unit-3 固有）

| 項目 | 決定 | バージョン方針 | 根拠 |
|---|---|---|---|
| Strands Agents Python SDK | `strands-agents` | 最新安定（2026-05 時点で 1.x 系）| Q3=A streaming、Q15=A `agentcore dev` 公式サポート |
| 開発サーバー | `agentcore dev`（uvicorn ベース）| AgentCore CLI 同梱 | Q15=A、Mock 構築工数 0 |
| Mobile 側クライアント | `@aws-sdk/client-bedrock-agentcore` | npm 最新 | Mobile からの InvokeAgentRuntime 呼び出し |
| Strands 互換性 | Bedrock Haiku 4.5 / Sonnet 4.6 サポート確認 | — | Q4=A+SSM 切替対応 |

### 2.1 backend/src/debate/requirements.txt

```
bedrock-agentcore>=1.0.0
strands-agents>=1.0.0
boto3>=1.35.0
pydantic>=2.5.0
aws-lambda-powertools>=2.30.0   # B-12 互換
```

### 2.2 Mobile npm 依存（追加分）

```jsonc
{
  "dependencies": {
    "@aws-sdk/client-bedrock-agentcore": "^3.x",
    "event-source-parser": "^3.x"  // Strands streaming chunk のパース
  }
}
```

`@aws-sdk/client-bedrock-agentcore` は Cognito User Pool JWT を `Authorization` ヘッダで AgentCore Runtime に送信する（AgentCore Cognito Authorizer が JWT を検証）。Mobile 側は Amplify Auth から `accessToken` を取得して SDK に渡す。Cognito Identity Pool は採用しない（v3.3 NM-1 修正、AgentCore は User Pool JWT 直接受領）。

---

## 3. Bedrock モデル戦略（Q4=A+SSM、v3.3 で P0 化）

| 項目 | 決定 | 根拠 |
|---|---|---|
| MVP 既定モデル | `anthropic.claude-haiku-4-5` | parallel-dev-prerequisites C-2 確定、apne1 native |
| 切替方法 | SSM Parameter `/yudane/<env>/debate/model-id` | Q4=A+SSM、Stack 再デプロイ不要 |
| 切替候補（決勝後）| `anthropic.claude-sonnet-4-6`（Global CRIS 経由）| B-002 / B-305 backlog、要件未達時に検討 |
| IAM 先行付与 | Haiku 4.5 + Sonnet 4.6 の 2 ARN ワイルドカード | v3.3 M-4、Sonnet 切替時の AccessDenied 防止 |
| Guardrails | Bedrock Guardrails（DENIED_TOPICS = NG-1〜8、streaming 対応版）| Q12=D 多層モデレーション 第 2 層 |
| Embeddings | Titan Embeddings V2（必要な場合のみ）| custom Strategy が内部で利用、Unit-3 直接利用なし |

### 3.1 Bedrock Guardrails 構成（v3.3 確定）

```typescript
const guardrail = new bedrock.CfnGuardrail(this, 'DebateGuardrail', {
  name: `yudane-debate-${envName}-guardrail`,
  description: 'NG-1〜8 検出、M-2 軸の NG-6 滑落防止',
  topicPolicyConfig: {
    topicsConfig: [
      { name: 'illegal-activity', type: 'DENY', /* NG-1 */ },
      { name: 'health-harm', type: 'DENY', /* NG-2 */ },
      { name: 'discrimination', type: 'DENY', /* NG-3 */ },
      { name: 'minor-targeting', type: 'DENY', /* NG-4 */ },
      { name: 'mental-health', type: 'DENY', /* NG-5 */ },
      { name: 'threat-or-guilt-coercion', type: 'DENY', /* NG-6 最重要 */ },
      { name: 'personal-data-misuse', type: 'DENY', /* NG-7 */ },
      { name: 'associates-violation', type: 'DENY', /* NG-8 */ },
    ],
  },
  contentPolicyConfig: { /* HATE / VIOLENCE / SEXUAL / INSULTS = HIGH */ },
  // streaming 対応
});
```

---

## 4. Cooldown DDB（唯一の自前テーブル、Q2=C）

| 項目 | 決定 | 根拠 |
|---|---|---|
| テーブル名 | `yudane-debate-<env>-cooldowns` | shared-infrastructure.md §2 命名規約 |
| キー設計 | PK: `USER#{actor_id}` / SK: `COOLDOWN#current` | 1 ユーザー 1 レコード、TTL 30 日 |
| 属性命名 | camelCase（`consecutiveRefuses` / `cooldownUntil` / `lastRefuseAt`、v3.3 C3-2）| Pydantic v2 alias で snake_case ↔ camelCase 変換 |
| 課金モード | On-Demand（PAY_PER_REQUEST）| 予測しにくいトラフィックパターン、ハッカソン規模 |
| KMS 暗号化 | Unit-1 KMS Key | SECURITY-01 |
| PITR | 有効 | データ保護 |
| TTL 属性 | `ttl`（UNIX timestamp、30 日後に自動削除）| データ最小化 |

---

## 5. S3 Memory Export（Q13=D+S3）

| 項目 | 決定 | 根拠 |
|---|---|---|
| Bucket 名 | `yudane-debate-<env>-memory-export` | 命名規約 |
| Lifecycle | Standard → IA (30d) → Glacier Instant Retrieval (90d) → 削除 (365d) | Year 1 退化レポート用 |
| KMS 暗号化 | Unit-1 KMS Key | SECURITY-01 |
| Athena 連携 | Glue Crawler 日次、Athena view `debate_outcomes_v1` | Unit-8 から参照 |
| パブリック遮断 | BlockPublicAccess 全有効 | SECURITY-09 |
| Versioning | 有効（誤削除保護）| データ保全 |

---

## 6. SSM Parameter Store（Unit-3 出力 8 個、v3.3 C-5 + NC2-2 で kill-switch 追加）

| Parameter | 用途 | 出力タイミング |
|---|---|---|
| `/yudane/<env>/debate/runtime-arn` | Mobile アプリのビルド時に SSM CLI 経由で取得し `EXPO_PUBLIC_DEBATE_RUNTIME_ARN` として埋め込み（4IDC-1 修正、Cognito Identity Pool 不採用のため Mobile は SSM API を直接呼べない）| P0 |
| `/yudane/<env>/debate/memory-id` | Memory ID（他 Unit 参照可能性）| P0 |
| `/yudane/<env>/debate/runtime-endpoint-live-arn` | Mobile アプリのビルド時に SSM CLI 経由で取得し `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` として埋め込み | P0 |
| `/yudane/<env>/debate/runtime-endpoint-canary-arn` | 同上、canary build のみ `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_CANARY_ARN` として埋め込み | P1 |
| `/yudane/<env>/debate/model-id` | Strands Agent 起動時取得（Q4=A+SSM）| P0 |
| `/yudane/<env>/debate/memory-export-bucket-arn` | Unit-8 が Year 1 退化レポートで参照 | P1 |
| `/yudane/<env>/debate/cooldowns-table-arn` | Unit-7 が cooldown 解除 PATCH で参照 | P0 |
| `/yudane/<env>/debate/kill-switch` | DDB 障害連続 5 分以上で全ユーザー論破停止（NFR-AVAIL-DEBATE-04 / v3.3 NC2-2 修正）。値: `'enabled'` / `'disabled'`、既定 `'disabled'` | P0 |

参照規約: 他 Stack から `ssm.StringParameter.valueForStringParameter()` で読み取り（Stack 跨ぎ）。kill-switch の値変更は Lambda 起動時取得ではなくリアルタイム読み取り（毎セッション開始時に SSM GetParameter）で反映。

---

## 7. テスト・観測スタック（Unit-3 固有追加）

### 7.1 PBT / 統合テスト

| ツール | 用途 |
|---|---|
| Hypothesis（既存）| `compose_debate_prompt` / `increment_refuse_count` / `estimate_stress_level` の property |
| fast-check（既存）| Mobile `event-parser.ts` / `agentcore-client.ts` の property |
| boto3 stubber | DDB / Memory / Bedrock の AWS SDK モック |
| moto（任意）| boto3 stubber より広範な統合テストが必要な場合 |
| msw（既存）| Mobile 側 `@aws-sdk/client-bedrock-agentcore` のモック |

### 7.2 観測（Unit-1 から継承 + Unit-3 拡張）

| ツール | 用途 |
|---|---|
| AWS Lambda Powertools（既存）| 構造化ログ + EMF メトリクス + X-Ray |
| AgentCore Runtime 標準 OTEL | 分散トレース（Strands → Bedrock → Memory）|
| CloudWatch Dashboard | NFR-OBS-DEBATE-11 の 4 ウィジェット |
| CloudWatch Alarms | NFR-SEC-DEBATE-08 の 4 種 |

---

## 8. v3 で採用しなかった技術と理由

| 技術 | 採用候補だった理由 | 不採用理由 |
|---|---|---|
| 自前 Lambda + Lambda Streaming（v2 案） | main マージ後の整合 | AgentCore Runtime で代替（v2 → v3）、自前 SSE 設計工数 0、サーバー権威タイマー / streaming maintenance コスト 0 |
| Provisioned Throughput | Bedrock Throttling 完全防止 | コスト高（月額数百ドル）、ハッカソン規模では On-Demand + Mobile 1 回リトライで十分 |
| LocalStack（AgentCore mock）| 完全ローカル開発 | LocalStack の AgentCore 対応不確定、`agentcore dev` + dev 環境 Bedrock で十分（Q15=A）|
| API Gateway + Lambda Authorizer | Unit-1 既存基盤との整合 | AgentCore Runtime が Cognito Authorizer 直接対応（Q5=A）、API Gateway 経由は不要 |
| VPC 内 Lambda | SECURITY-07 ENI 経由 | AgentCore Runtime は AWS マネージドコンテナ、Public Network で十分（Q6=A）。ENI コールドスタートリスクなし |
| OpenAPI 経由（debate.yaml）| Mobile / Backend 契約定義 | AgentCore Runtime 直接呼び出しのため不要、`shared/agentcore-contracts/debate.ts` で TypeScript 型のみ共有 |
| Step Functions | 90 秒タイマー / クールダウン制御 | parallel-dev-prerequisites で除外確定、AgentCore Runtime lifecycleConfiguration + DDB Cooldowns で十分 |

---

## 9. ロックファイル管理（Unit-3 固有）

| ファイル | コミット必須 | 備考 |
|---|---|---|
| `backend/src/debate/poetry.lock` | ✅ | Strands SDK + bedrock-agentcore |
| `mobile/package-lock.json`（Unit-1 既存）| ✅ | `@aws-sdk/client-bedrock-agentcore` + `event-source-parser` 追加 |
| `infra/package-lock.json`（Unit-1 既存）| ✅ | `aws-cdk-lib` バージョン固定（AgentCore L2 安定後） |

---

## 10. 採用済みスタック一覧（Unit-3 として確定）

| カテゴリ | 採用 | バージョン |
|---|---|---|
| AI Runtime | AgentCore Runtime（Direct Code Deploy）| apne1 GA |
| AI Memory | AgentCore Memory（組み込み 2 + custom 1 Strategy）| apne1 GA |
| AI Agent SDK | Strands Agents Python SDK | 1.x |
| LLM | Bedrock Haiku 4.5（既定）| `anthropic.claude-haiku-4-5` |
| LLM 切替候補 | Bedrock Sonnet 4.6（B-305 backlog）| `anthropic.claude-sonnet-4-6` |
| LLM Guardrails | Bedrock Guardrails（streaming 対応）| 8 DENIED_TOPICS |
| Mobile SDK | `@aws-sdk/client-bedrock-agentcore` + `event-source-parser` | 最新 |
| Cooldown DDB | `yudane-debate-<env>-cooldowns`（On-Demand）| — |
| Memory Export | S3 + Athena + Glue Crawler | Standard → IA → Glacier → 365d 削除 |
| 認証認可 | AgentCore Cognito Authorizer | Unit-1 User Pool 再利用 |
| 観測 | Lambda Powertools + AgentCore OTEL | EMF + X-Ray |
| ローカル開発 | `agentcore dev` + dev 環境 Bedrock + dev Memory | hot reload |
| PBT | Hypothesis + fast-check + boto3 stubber | Coverage 85% 目標 |

> **Unit-3 で新たに導入する依存ライブラリは AgentCore + Strands SDK + `@aws-sdk/client-bedrock-agentcore` + `event-source-parser` の 4 つのみ**。それ以外は Unit-1 の既存スタックを継承して整合性を保つ。
