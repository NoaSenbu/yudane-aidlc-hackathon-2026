# Unit-3 Debate — Code Generation Phase 1 Plan

> **このプランは Unit-3 Phase 1 Code Generation の Single Source of Truth**。Code Generation Part 2 ではこのステップ順に従ってコードを生成し、各ステップ完了時に [x] を付ける。
>
> 参照: [task-breakdown.md Phase 1](../unit-3-debate/functional-design/task-breakdown.md) / [Functional Design](../unit-3-debate/functional-design/) / [NFR Design](../unit-3-debate/nfr-design/) / [Infrastructure Design](../unit-3-debate/infrastructure-design/) / [Unit-1 Code Generation Plan](./unit-1-platform-code-generation-plan.md) / steering（tech-typescript / tech-python / tech-cdk）
>
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / Code Generation Phase 1 Plan
>
> 期間: **2026-05-31〜2026-06-02（3 日）** / 担当: **Member B**

---

## 0. Phase 1 のコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | AgentCore Runtime + Memory + DDB Cooldowns + SSM model_id の **基盤疎通**（最小限の本格実装） |
| 担当 | Member B |
| 依存 | Unit-1 platform-stack（SSM `userpool-id` / `userpool-client-id` / `kms-key-arn` / `alerts-topic-arn` / `auditlogger-layer-arn`）/ Unit-2 Auth & Profile（Cognito User Pool MFA フロー）|
| 完了条件 | Mobile から dev Runtime に Cognito JWT で接続し、token を 1 つでも受信できる。SSM `model-id` 値変更で model_id が反映される（Lambda 再起動）。Snapshot test と Unit test が green |
| プロジェクト種別 | 既存モノレポへの Unit 追加（Unit-1 完了済み）|
| ワークスペースルート | リポジトリ直下 |
| **UI SSOT** | **Direction D「黒服のコンシェルジュ」**（[`aidlc-docs/construction/unit-3-debate/YUDANE Concierge (Direction D) (offline).html`](../unit-3-debate/YUDANE%20Concierge%20%28Direction%20D%29%20%28offline%29.html)、2026-05-30 切替）。**Phase 1 では Mobile UI 画面実装はしない**（agentcore-client + event-parser の通信層のみ）ため、Direction D 切替の実装影響は **Step 7 の `metadata.axis` 型定義 + 軸タグ抽出のみ**。Phase 2 以降の M-04 DebateScreen 実装で Direction D を本格適用する。詳細は [`design-system/direction-d-design-system.md`](../../design-system/direction-d-design-system.md) と [`unit-3-debate/functional-design/frontend-design.md`](../unit-3-debate/functional-design/frontend-design.md) を参照 |

### Phase 1 で生成するコンポーネント

| LC ID | 論理コンポーネント | 配置 | TDD スタイル |
|---|---|---|---|
| LC-D-01 | Debate Entrypoint Router（最小） | `backend/src/debate/main.py` | クラシック TDD |
| LC-D-02 | Strands Agent Streaming Pipeline（最小） | `backend/src/debate/main.py` 内 Strands Agent 初期化 | クラシック TDD |
| LC-D-06 | Cooldown DDB Adapter（最小） | `backend/src/debate/cooldown.py` | クラシック TDD |
| LC-D-12 | SSM Configuration Loader | `backend/src/debate/ssm.py` | クラシック TDD |
| LC-D-09 | Mobile AgentCore Client | `mobile/src/features/debate/agentcore-client.ts` | Outside-In TDD |
| LC-D-10 | Mobile Event Parser（最小 4 種 EventType） | `mobile/src/features/debate/event-parser.ts` | Outside-In TDD |
| Infra | debate-stack（CDK） | `infra/lib/debate-stack.ts` | Snapshot TDD |

### Phase 1 では実装しないもの（Phase 2 以降）

| 領域 | 理由 |
|---|---|
| LC-D-03 Memory Hook Manager | Phase 2 T2.3（プロンプト合成と並走）|
| LC-D-04 Prompt Composition Engine（6 モジュール）| Phase 2 T2.1（プロンプト合成）|
| LC-D-05 Stress Estimator | Phase 2 T2.2（Memory 統合と並走）|
| LC-D-07 3-Layer Moderation Pipeline | 第 1 層プロンプトガードレールは Phase 2、第 2/3 層は Phase 3 |
| LC-D-08 Affirmation Generator | Phase 2 T2.5（Mobile UI と並走）|
| LC-D-11 Memory S3 Export Pipeline | Phase 3 T3.2（streamDeliveryResources + Athena）|
| Mobile M-04 DebateScreen UI | Phase 2 T2.5（プロンプト合成完成後）|

---

## 1. コード生成ステップ（Code Generation Part 2 で順次実行）

> **TDD 規約**: AGENTS.md §12.4 に従い、各 Step は Red（テスト先）→ Green（実装最小）→ Refactor → PBT 補強 の 4 フェーズ順序で生成する。Step 1 は CDK Snapshot TDD、Step 2〜5 はクラシック TDD（Backend）、Step 6〜7 は Outside-In TDD（Mobile）。

### Step 1: Infra / debate-stack scaffold + Snapshot TDD（T1.1）

**目的**: Phase 1 で必要な物理 AWS リソースを CDK で定義、cdk synth が通る状態にする。

- [ ] **Step 1.1（Red）**: `infra/test/debate-stack.test.ts`（vitest CDK assertions）
  - test: `PlatformStack の SSM userpool-id を参照できる`
  - test: `agentcore.Runtime リソースが lifecycleConfiguration: { idleTimeoutSeconds: 120, maxLifetimeSeconds: 120 } で定義される`
  - test: `agentcore.RuntimeEndpoint live が定義される`（P1M-1 修正）
  - test: `agentcore.Memory リソースが expirationDuration: 90 days + userPreference + semantic Strategy で定義される`
  - test: `DynamoDB CooldownsTable が PAY_PER_REQUEST + KMS + PITR + TTL='ttl' で定義される`
  - test: `IAM Role が Bedrock 2 ARN ワイルドカード（Haiku 4.5 + Sonnet 4.6）を持つ`
  - test: `bedrock.CfnGuardrail が NG-1〜8 の 8 DENIED_TOPICS で定義される`（Phase 1 では関連付けせず存在のみ）
  - test: `SSM 8 個（runtime-arn / memory-id / runtime-endpoint-live-arn / model-id / cooldowns-table-arn / kill-switch / + Phase 3 で追加 memory-export-bucket-arn / Phase 5 で追加 runtime-endpoint-canary-arn）のうち Phase 1 で 6 個を出力`

- [ ] **Step 1.2（Green）**: `infra/lib/debate-stack.ts` 新規作成
  - Unit-1 SSM 5 個参照（`userpool-id` / `userpool-client-id` / `kms-key-arn` / `alerts-topic-arn` / `auditlogger-layer-arn`）を `ssm.StringParameter.valueForStringParameter()` で取得
  - **`platformKmsKey = kms.Key.fromKeyArn(this, 'PlatformKey', kmsKeyArn)` で IKey 型に復元**（DDB / S3 / Memory の暗号化キー参照に必要、2P1M-2 修正）
  - **`alertsTopic = sns.Topic.fromTopicArn(this, 'AlertsTopic', alertsTopicArn)` で SNS Topic 型に復元**（Phase 6 Alarm 設定で使用、Phase 1 では Construct 化のみ）
  - **`auditLoggerLayer = lambda.LayerVersion.fromLayerVersionArn(this, 'AuditLoggerLayer', auditLoggerLayerArn)` で復元**（Phase 1 Lambda 統合では未使用、Phase 2 で Strands Agent IAM Role に attach）
  - `agentcore.Runtime`（Direct Code Deploy + Cognito Authorizer + Public Network + lifecycleConfiguration）
  - `agentcore.Memory`（expirationDuration 90d + userPreference + semantic、`kmsKey: platformKmsKey` を渡す、custom は Phase 4 で `addStrategy` または再 deploy で追加するためコメントアウト）
  - `RuntimeEndpoint live` 1 個（canary は Phase 5）
  - `dynamodb.Table CooldownsTable`（On-Demand + `encryptionKey: platformKmsKey` + PITR + TTL `ttl`）
  - `bedrock.CfnGuardrail`（NG-1〜8 DENIED_TOPICS、ただし Phase 1 では `bedrock_kwargs.guardrailIdentifier` 未関連付け、Phase 3 で関連付け）
  - IAM Role + Bedrock 2 ARN ワイルドカード + Memory R/W + DDB R/W + KMS + SSM + CloudWatch + X-Ray
  - SSM Parameter 6 個出力（`/yudane/dev/debate/{runtime-arn, memory-id, runtime-endpoint-live-arn, model-id, cooldowns-table-arn, kill-switch}`）

- [ ] **Step 1.3（Refactor）**: 共通定数（`yudane-debate-${envName}-*` 命名）を Construct 化、cdk-nag Suppression に理由コメント追加

- [ ] **Step 1.4（Snapshot fixture）**: `infra/test/__snapshots__/debate-stack.test.ts.snap` を確定（cdk-nag green を確認後 fixture 化）

- [ ] **Step 1.5**: `infra/bin/app.ts` 更新（`new DebateStack(app, 'DebateDevStack', { envName: 'dev' })` 追加）

**完了条件**: `npx cdk synth DebateDevStack` がエラーなく完了、Snapshot test が green、cdk-nag green。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/debate-stack-summary.md`

---

### Step 2: Backend / SSM Configuration Loader（LC-D-12、T1.2）

**目的**: Strands Agent 起動時に SSM `model-id` を取得、毎セッション開始時に SSM `kill-switch` を取得する純粋な薄ラッパーを実装。

- [ ] **Step 2.1（Red）**: `backend/tests/debate/test_ssm.py`
  - test: `get_model_id('dev') が SSM /yudane/dev/debate/model-id の値を返す`（boto3 stubber でモック）
  - test: `is_kill_switch_enabled('dev') が値 'enabled' で True / 'disabled' で False を返す`
  - test: `is_kill_switch_enabled が SSM 例外時に False を返す`（fail-safe、kill-switch 未設定 = 'disabled' 既定動作）

- [ ] **Step 2.2（Green）**: `backend/src/debate/ssm.py`
  - `get_model_id(env_name: str) -> str`（Lambda 起動時 1 回取得）
  - `is_kill_switch_enabled(env_name: str) -> bool`（毎セッション開始時取得、リアルタイム反映）

- [ ] **Step 2.3（Refactor）**: SSM 例外時の structured logging（B-12 AuditLogger Lambda Layer 経由）追加

**完了条件**: `pytest backend/tests/debate/test_ssm.py` が全 green、Coverage Line 95%+ Branch 90%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/ssm-loader-summary.md`

---

### Step 3: Backend / Domain Models（LC-D-01 / LC-D-06 前提、依存順序のため Step 4 から繰り上げ）

**目的**: Phase 1 で main.py / cooldown.py が使う最小限の Pydantic v2 モデルを実装。Step 4 Cooldown が `CooldownState` / `CooldownDecision` を使うため、Step 3 で先に定義する（2P1M-1 修正）。

- [ ] **Step 3.1（Red）**: `backend/tests/debate/domain/test_payloads.py`
  - test: `DebateInvocationPayload.model_validate(payload) が action='start_session' で正しく検証される`
  - test: `payload に actor_id を入れても無視される`（SECURITY-08）
  - test: `asin が 10 桁英数字大文字以外で ValidationError`
  - test: `user_input が 2000 文字超で ValidationError`

- [ ] **Step 3.2（Green）**: `backend/src/debate/domain/payloads.py`
  - `DebateInvocationPayload`（domain-entities.md §2.1 準拠、`action` / `user_input` / `asin` / `trigger` / `client_session_id?` / `client_signals?` / `outcome?`）
  - `ClientSignals`（domain-entities.md §2.2 準拠）
  - 注: `parse_jwt_actor_id(context)` は Step 5 main.py の責務、本 Step では **モデル定義のみ**

- [ ] **Step 3.3（Green、追加）**: `backend/src/debate/domain/results.py`
  - `CooldownState` / `CooldownDecision`（domain-entities.md §4 準拠、camelCase alias）

- [ ] **Step 3.4（Refactor）**: 全モデルに docstring（日本語）、Pydantic ConfigDict で `populate_by_name=True`

- [ ] **Step 3.5（PBT 補強）**: `backend/tests/debate/domain/property/test_payloads_property.py`
  - PBT-02 Round-trip: `DebateInvocationPayload.model_dump() → model_validate() で同一値`

**完了条件**: `pytest backend/tests/debate/domain/` が全 green、Coverage Line 95%+ Branch 90%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/domain-models-summary.md`

---

### Step 4: Backend / Cooldown DDB Adapter（LC-D-06、T1.2、Step 3 の Domain Model に依存）

**目的**: DDB Cooldowns の CRUD 操作 + 自然解除リセットロジック + 不変条件 PBT-03 を実装。

- [ ] **Step 4.1（Red）**: `backend/tests/debate/test_cooldown.py`
  - test: `check_cooldown(actor_id) が DDB GetItem で空 → CooldownDecision(active=False, consecutive_refuses=0) を返す`
  - test: `check_cooldown が cooldownUntil > now → CooldownDecision(active=True) を返す`
  - test: `check_cooldown が cooldownUntil <= now（自然解除）→ CooldownDecision(active=False, consecutive_refuses=0) を返す`
  - test: `increment_refuse_count が 1〜2 回呼ばれた時に consecutiveRefuses が ADD される`
  - test: `increment_refuse_count が 3 回目で必ず cooldownUntil = now + 3h を SET する`（COOLDOWN-02 / PBT-03 重点）
  - test: `自然解除後の最初の拒否で consecutiveRefuses = 1 にリセットされる`（M3-1 修正）

- [ ] **Step 4.2（Green）**: `backend/src/debate/cooldown.py`
  - `check_cooldown(actor_id, now) -> CooldownDecision`（純関数、DDB read のみ）
  - `increment_refuse_count(actor_id, now) -> CooldownState`（DDB read → 自然解除判定 → DDB UpdateItem with conditional 3-trigger）
  - 属性は **camelCase**（`consecutiveRefuses` / `cooldownUntil` / `lastRefuseAt`）+ Pydantic alias

- [ ] **Step 4.3（Refactor）**: DDB 例外（DDBError）を try/except でキャッチして DomainError に変換、B-12 AuditLogger 経由で構造化ログ出力

- [ ] **Step 4.4（PBT 補強）**: `backend/tests/debate/property/test_cooldown_property.py`
  - PBT-03 Invariant: `任意の actor_id で increment_refuse_count を 3 回呼ぶと必ず cooldownUntil が SET される`（hypothesis + boto3 stubber）
  - PBT-03 Invariant: `自然解除後の拒否で consecutiveRefuses == 1`

**完了条件**: `pytest backend/tests/debate/test_cooldown.py + property/test_cooldown_property.py` が全 green、Coverage Line 95%+ Branch 90%+、PBT-03 がレポートに表示。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/cooldown-summary.md`

---

### Step 5: Backend / Debate Entrypoint Router 最小実装（LC-D-01 + LC-D-02、T1.2）

**目的**: AgentCore Runtime entrypoint で SSM model_id を読み込み、Strands Agent を初期化し、dummy `compose_debate_prompt()` で Bedrock Haiku 4.5 streaming を 1 回呼び出して token を yield する最小実装。actor_id 解決（PAT-D-SEC-01）も本 Step で実装。

- [ ] **Step 5.1（Red）**: `backend/tests/debate/test_main_smoke.py`
  - test: `parse_jwt_actor_id(context) が context.user.sub を返す`（PAT-D-SEC-01 / NFR-SEC-DEBATE-01）
  - test: `parse_jwt_actor_id が context.user 未定義で None を返す`（fail-safe）
  - test: `debate_handler が actor_id 未解決で error event 'auth.unauthenticated' を yield する`
  - test: `debate_handler が payload に actor_id を入れても context 由来の値が使われる`（SECURITY-08 不変条件）
  - test: `payload 検証エラーで error event を yield する`
  - test: `クールダウン中で debate.cooldown_triggered event を yield して Bedrock を呼ばない`（cost-protective、PAT-D-COST-01）

- [ ] **Step 5.2（Green）**: `backend/src/debate/main.py`
  - `BedrockAgentCoreApp` + `@app.entrypoint`
  - `MODEL_ID = get_model_id(env_name=os.environ['ENV_NAME'])`（起動時 1 回）
  - `agent = Agent(model=MODEL_ID, hooks=[], callback_handler=None)`（Phase 1 では hooks / Guardrails 未関連付け、`bedrock_kwargs` は Strands SDK のデフォルト動作に委ねる、空 dict 不要なら省略）
  - `parse_jwt_actor_id(context) -> Optional[str]`（context.user.sub を返す、None で auth.unauthenticated）
  - `debate_handler(payload, context)` の最小実装:
    - actor_id 解決（parse_jwt_actor_id 経由）
    - DebateInvocationPayload 検証
    - `check_cooldown` 判定 → クールダウン中なら `debate.cooldown_triggered` yield
    - dummy `compose_debate_prompt = f"ユーザー入力: {invocation.user_input}\n論破してください"`
    - `agent.stream_async(composed_prompt)` → token chunk を yield
    - 90s タイマーは Phase 1 では実装せず（Phase 3 で graceful shutdown 追加）

- [ ] **Step 5.3（Refactor）**: SSM kill-switch 連携追加（DDB 障害時の fail-open + kill-switch enabled で全停止、PAT-D-COST-04）

- [ ] **Step 5.4（疎通確認）**: `agentcore dev --port 8080` でローカル起動、別ターミナルから `agentcore invoke --dev` でローカル endpoint を叩く（dev / staging / prd デプロイは Step 8 で実施）。`--payload '{"action":"start_session","user_input":"でも欲しい","asin":"B01ABC1234","trigger":"reel_skip"}'` で token 受信を確認

**完了条件**: `pytest backend/tests/debate/test_main_smoke.py` が全 green、`agentcore dev` ローカル疎通成功、Coverage Line 85%+ Branch 80%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/main-handler-summary.md`

---

### Step 6: Mobile / AgentCore Client（LC-D-09、T1.3）

**目的**: Mobile から AgentCore Runtime を呼び出すラッパーを Outside-In TDD で実装。**SSM 直接読みは行わず、EAS Build 時に注入された `EXPO_PUBLIC_*` 環境変数から Runtime ARN を取得**（4IDC-1 修正）。

- [ ] **Step 6.1（Red）**: `mobile/src/features/debate/agentcore-client.test.ts`
  - test: `process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN から ARN を取得する`（vitest の `vi.stubEnv('EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN', 'arn:...')` でモック）
  - test: `Amplify Auth.fetchAuthSession() で actor_id を取得する`（@aws-amplify/auth モック）
  - test: `runtimeSessionId が ${session_id}_${actor_id} の形式（63 文字）`
  - test: `ThrottlingException で 1 回のみリトライ`（PAT-D-COST-02、msw でモック）
  - test: `2 回目失敗で error event を yield`
  - test: `cancel() で AbortController が abort される`

- [ ] **Step 6.2（Green）**: `mobile/src/features/debate/agentcore-client.ts`
  - `DebateAgentCoreClient` クラス
  - `BedrockAgentCoreClient` を `@aws-sdk/client-bedrock-agentcore` から import
  - `invoke(payload, qualifier='live')`: `process.env.EXPO_PUBLIC_*` から ARN 取得 → InvokeAgentRuntimeCommand 発行 → `AsyncIterable<Uint8Array>` を yield
  - 1 回リトライ + AbortController

- [ ] **Step 6.3（Refactor）**: `app.config.js`（Expo）の雛形に `extra` フィールドで EAS Build 時 SSM 取得を定義（`@expo/cli` 経由で `aws ssm get-parameter` を実行する build hook）

- [ ] **Step 6.4（Refactor）**: 環境変数 fallback（dev 時は `process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN || 'arn:aws:bedrock-agentcore:apne1:000000000000:runtime/dummy'`）

**完了条件**: `vitest run mobile/src/features/debate/agentcore-client.test.ts` が全 green、Coverage Line 85%+ Branch 80%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/agentcore-client-summary.md`

---

### Step 7: Mobile / Event Parser（LC-D-10、T1.4）

**目的**: Strands streaming chunk JSON を最小 4 種 EventType（`token` / `turn_complete` / `session_complete` / `error`）に変換するパーサーを Outside-In TDD で実装。

- [ ] **Step 7.1（Red）**: `mobile/src/features/debate/event-parser.test.ts`
  - test: `chunk = '{"type":"token","delta_text":"hello"}' → EventType='token', delta_text='hello'`
  - test: `chunk = '{"type":"turn_complete"}' → EventType='turn_complete'`
  - test: `chunk = '{"type":"session_complete","metadata":{"reason":"agreed"}}' → reason='agreed'`
  - test: `chunk = '{"type":"error","metadata":{"reason":"auth.unauthenticated"}}' → EventType='error'`
  - test: `不正な JSON で error event を yield`（fail-safe）
  - test: 軸タグ抽出 `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` が `metadata.axis` に付与される（PAT-D-OBS-01）

- [ ] **Step 7.2（Green）**: `mobile/src/features/debate/event-parser.ts`
  - `parseEventStream(stream: AsyncIterable<Uint8Array>): AsyncIterable<StrandsStreamEvent>`
  - `event-source-parser` ライブラリで SSE chunk parse
  - JSON parse + EventType 判別
  - `extractAxis(text)` で `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` 抽出

- [ ] **Step 7.3（Refactor）**: `mobile/src/features/debate/types.ts` で `StrandsStreamEvent` / `EventType` を定義（domain-entities §3.1 準拠、Phase 1 では最小 4 種 + 軸タグのみ、Phase 2 で `moderation_blocked` / `graceful_shutdown_initiated` / `summary` / `debate.*` を追加）。`metadata.axis` は `'FACT' | 'PSYCHOLOGY' | 'REWARD' | undefined` 型で、**Direction D の論破画面ラベル「論破 I・データ」/「論破 II・感想」/「論破 III・ご褒美」へ Phase 2 で 1:1 マッピングされる**（[frontend-design.md §2.2](../unit-3-debate/functional-design/frontend-design.md) 参照）

- [ ] **Step 7.4（PBT 補強）**: `mobile/src/features/debate/event-parser.property.test.ts`
  - PBT-02 Round-trip: `任意の Strands chunk JSON → parseEventStream → 元の chunk 形式に再構成可能`（fast-check）

**完了条件**: `vitest run mobile/src/features/debate/event-parser*.test.ts` が全 green、Coverage Line 90%+ Branch 85%+。

**ドキュメント**: `aidlc-docs/construction/unit-3-debate/code/event-parser-summary.md`

---

### Step 8: Phase 1 疎通確認 + ドキュメント仕上げ（T1.5）

**目的**: Mobile から dev Runtime に Cognito JWT で接続し、token を 1 つでも受信できることを実機で確認。

- [ ] **Step 8.1**: `infra/lib/debate-stack.ts` を dev 環境にデプロイ（**ユーザー承認必須**、tech-cdk §9）
  - `npx cdk synth DebateDevStack` → `npx cdk diff` → ユーザー承認 → `npx cdk deploy DebateDevStack`
  - SSM 6 個が dev に出力されることを確認

- [ ] **Step 8.2**: EAS Build dev build 実行
  - `eas build --platform ios --profile development` または `--platform android`
  - `app.config.js` の build hook で SSM CLI 経由 `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` を取得
  - dev build に環境変数として埋め込まれることを確認

- [ ] **Step 8.3**: Member B 個人端末で dev build を起動
  - Cognito User Pool MFA 経由で JWT 取得（Unit-2 完了が前提）
  - `DebateAgentCoreClient.invoke()` で token を 1 つでも受信できることを確認
  - CloudWatch Logs で AgentCore Runtime が起動・Bedrock 呼び出ししていることを確認

- [ ] **Step 8.4（追加）**: SSM `model-id` 値変更で動的反映を確認
  - `aws ssm put-parameter --name /yudane/dev/debate/model-id --value anthropic.claude-haiku-4-5 --overwrite`（同じ値で更新）
  - **AgentCore Runtime のローリング再起動を待ってから新値が読まれることを確認**（Lambda 起動時 1 回取得のため、再起動前は旧値を保持。`aws bedrock-agentcore restart-runtime` または手動 deploy で再起動）

- [ ] **Step 8.5**: Phase 1 完了サマリ作成
  - `aidlc-docs/construction/unit-3-debate/code/phase1-summary.md`
  - 生成ファイル一覧、TDD サイクル実績、Coverage 値、cdk-nag 結果、E2E 疎通結果

- [ ] **Step 8.6**: aidlc-state.md / 本プランのチェックボックス最終更新

**完了条件**: 全 Step が [x] 状態、E2E 疎通成功、Coverage 目標達成、aidlc-state.md / Phase 1 完了マーク。

---

## 2. Phase 1 完了後の主要ファイル一覧

```
infra/
├── bin/app.ts                          # +DebateStack 追加
├── lib/debate-stack.ts                 # 新規（CDK）
└── test/
    ├── debate-stack.test.ts            # 新規（Snapshot TDD）
    └── __snapshots__/
        └── debate-stack.test.ts.snap   # 新規（Snapshot fixture）

backend/
├── src/debate/                         # 新規ディレクトリ
│   ├── __init__.py
│   ├── main.py                         # LC-D-01 Entrypoint
│   ├── ssm.py                          # LC-D-12 SSM Loader
│   ├── cooldown.py                     # LC-D-06 Cooldown DDB Adapter
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── payloads.py                 # DebateInvocationPayload / ClientSignals
│   │   └── results.py                  # CooldownState / CooldownDecision
│   └── requirements.txt                # bedrock-agentcore + strands-agents + boto3 + Pydantic v2 + Lambda Powertools
└── tests/debate/                       # 新規ディレクトリ
    ├── __init__.py
    ├── test_ssm.py
    ├── test_cooldown.py
    ├── test_main_smoke.py
    ├── domain/
    │   ├── __init__.py
    │   └── test_payloads.py
    └── property/                       # PBT
        ├── __init__.py
        ├── test_cooldown_property.py
        └── test_payloads_property.py

mobile/src/features/debate/             # 新規ディレクトリ
├── agentcore-client.ts                 # LC-D-09 Mobile Client
├── agentcore-client.test.ts
├── event-parser.ts                     # LC-D-10 Event Parser
├── event-parser.test.ts
├── event-parser.property.test.ts       # PBT
└── types.ts                            # StrandsStreamEvent / EventType（最小 4 種 + 軸タグ）

mobile/
├── package.json                         # 依存追加: @aws-sdk/client-bedrock-agentcore + event-source-parser + @aws-amplify/auth
└── app.config.js                        # EAS Build 時 SSM CLI 取得 hook（4IDC-1 修正）

aidlc-docs/construction/unit-3-debate/code/  # 新規ディレクトリ
├── debate-stack-summary.md
├── ssm-loader-summary.md
├── cooldown-summary.md
├── domain-models-summary.md
├── main-handler-summary.md
├── agentcore-client-summary.md
├── event-parser-summary.md
└── phase1-summary.md
```

---

## 3. ストーリートレーサビリティ

Phase 1 は基盤疎通のため主担当ストーリーなし。ただし以下を **Phase 2 以降の前提** として提供:
- AgentCore Runtime + Memory + DDB Cooldowns + SSM model_id → US-DEBATE-01〜09 全体の API 契約土台
- Mobile AgentCore Client + Event Parser → US-DEBATE-01（論破セッション開始）+ US-DEBATE-04（軸別翻意計測）の横断インフラ
- Cooldown DDB Adapter → US-DEBATE-05（連続拒否クールダウン）+ US-SAFE-04（手動解除）の判定基盤

---

## 4. 依存・インターフェース

### 上流依存
- **Unit-1 platform-stack**: SSM 5 個（`/yudane/dev/platform/{userpool-id, userpool-client-id, kms-key-arn, alerts-topic-arn, auditlogger-layer-arn}`）/ KMS Key / SNS Topic / Lambda Layer
- **Unit-2 Auth & Profile**: Cognito User Pool MFA フロー（Step 8.3 の Mobile 疎通確認の前提）

### 下流提供（Phase 2 以降の Step が利用）
- SSM 6 個（Phase 1 で出力）
- DDB Cooldowns Table（Phase 2 で `increment_refuse_count` を Strands Agent ハンドラから呼び出し）
- AgentCore Memory（Phase 2 で MemoryHook を追加、Phase 4 で custom Strategy 追加）
- AgentCore Runtime + RuntimeEndpoint live（Phase 2 で main.py 拡張、Phase 5 で canary 追加）

---

## 5. 完了基準（Phase 1 全体）

- [ ] Step 1〜8 すべて [x]
- [ ] cdk-nag green（debate-dev-stack）
- [ ] Backend Coverage: Line 90%+ / Branch 85%+（重点 4 ファイル）/ Unit-3 全体 Line 85%+ / Branch 80%+
- [ ] Mobile Coverage: Line 85%+ / Branch 80%+（agentcore-client + event-parser）
- [ ] PBT-02 / PBT-03 が green、shrinking + seed ログ確認
- [ ] dev 環境デプロイ済み、E2E 疎通成功（Mobile → Runtime → token 受信）
- [ ] SSM `model-id` 値変更で動的反映確認
- [ ] 生成ドキュメント 8 件が `aidlc-docs/construction/unit-3-debate/code/` に揃う
- [ ] aidlc-state.md Phase 1 完了マーク

---

## 6. スコープ外（Phase 2 以降）

| Phase | 内容 |
|---|---|
| Phase 2（6/3〜6/6）| プロンプト合成 6 モジュール / Memory Hook / Stress Estimator / Mobile DebateScreen / Affirmation Generator / Telemetry 10 イベント / E2E-01 |
| Phase 3（6/7〜6/9）| Strands graceful shutdown 80s / Memory streamDeliveryResources + S3 export / Bedrock Guardrails 多層モデレーション完成 |
| Phase 4（6/10〜6/13）| custom Strategy m1_m2_axis_extractor / PBT 全面適用（NFR-PBT-DEBATE-01〜10） |
| Phase 5（6/13）| RuntimeEndpoint canary 追加（dev / staging / prd） |
| Phase 6（6/16〜6/26）| 統合テスト + cdk-nag green 確認 + 性能テスト + 決勝前カナリアリリース + リハーサル |

---

## 7. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| AgentCore Runtime CDK L2 が apne1 で安定していない | 高（Step 1 ブロッカー）| Step 1.2 開始時に `aws-cdk-lib/aws-bedrockagentcore` のバージョン確認 + L1（CfnRuntime）でフォールバック準備 |
| Bedrock Haiku 4.5 のモデルアクセス申請が承認されていない | 高 | Step 8 開始前に dev アカウントで Bedrock コンソールから Haiku 4.5 + Sonnet 4.6（先行）+ Titan Embeddings V2 をリクエスト、Member A が並行確認 |
| EAS Build の `app.config.js` で SSM CLI 経由取得が想定通り動作しない | 中（Step 6.3 / 8.2）| dev では `.env.local` ファイルでフォールバック（`EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN=arn:...`）を許容、staging / prd で SSM CLI 経由を必須化（Phase 5 で確定） |
| Cognito User Pool が Unit-2 でまだ MFA 設定されていない | 中（Step 8.3）| Step 8.3 のみ Unit-2 完成（Phase 2 並列着手見込み）後に検証へ延期可。代わりに dev 環境で Cognito User Pool に対して `aws-amplify` の SignUp + ConfirmSignIn の手動フローで先行検証（Phase 1 完了は Step 8.1〜8.2 で可）|
| ローカル `agentcore dev` から dev Bedrock 呼び出しのコストが想定外 | 低 | $10/日上限を Cost Anomaly Detection（Unit-1 既存）で監視、Step 5.4 の疎通確認は `agentcore invoke` 1〜2 回のみで切り上げる |
| `pip install bedrock-agentcore strands-agents` が requirements.txt 解決に時間がかかる | 中（Step 1.2 bundling）| `pip install --no-deps` で開始、依存解決エラーは個別追加で対応 |

---

## 8. ハッカソン評価軸へのインパクト

| 評価軸 | 本 Phase 1 Plan による貢献 |
|---|---|
| ビジネス意図の明確さ | Phase 1〜6 の段階実装で M-1 / M-2 / M-3 の到達順序を可視化、Phase 1 は「論破できる土台」を確立 |
| Unit 分解の適切さ | Step 1〜8 を TDD サイクル（Red → Green → Refactor → PBT）で構造化、Member B 単独完遂可能 |
| 創造性とテーマ適合性 | AgentCore Runtime + Memory + Strands Agent の組み合わせ自体がハッカソン「ダメ化メカニズム特化 AI」の構造的基盤 |
| ドキュメント品質 | Phase 1 完了時に code summary 8 件、TDD サイクルログ、E2E 疎通結果、Coverage レポート全て traceable |
| AI-DLC プロセス（予選評価軸） | Code Generation の TDD 順序を Plan に明記（Snapshot → クラシック → Outside-In）、AI が Plan に従って実装する証跡 |
| 決勝デモ完成度 | Phase 1 完了後に Phase 2〜6 の前提が整い、6/26 決勝デモまでの 25 日間を計画的に進行可能 |
