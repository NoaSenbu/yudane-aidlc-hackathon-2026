# Unit-3 Debate — Functional Design Part 1 Planning（v3.4）

> Construction Phase の Per-Unit Loop。Unit-3 Debate は **YUDANE のコア UC である UC-01 論破チャット** を担う。M-1（判断力の弱体化）と M-2（購買快楽のストレス解消剤化）を **同じセッションで併走** させるダメ化メカニズムの主戦場。
>
> **本ドキュメントは v3.4（2026-05-29）。コピートーンを Unit-3 のみ「論理優位ディベート系（敬語ベース、論理で黙らせるスタイル）」に局所オーバーライド + NFR Requirements の kill-switch 追加対応版**。設計判断の本質は v3.3 から変更なし、トーン局所変更 + NFR 強化のみ。
>
> **改訂履歴**:
>
> * v1（2026-05-28）: develop 系 Q1〜Q10 前提、自前 Lambda + DDB 案
>
> * v2（2026-05-29）: main マージ後の Unit-1 main 正本に整合（VPC 内 Lambda + Lambda Streaming）
>
> * v3（2026-05-29）: AgentCore 全面採用（Tokyo apne1 GA + `aws-cdk-lib/aws-bedrockagentcore` L2 安定確認後）。Q1 / Q3 / Q5 / Q6 / Q8 / Q10 / Q11 / Q13 / Q15 を AgentCore 採用版に書き直し、Unit-2 への申し送り 2 件を削除（Q8 / Q10 は Memory が代替）、Q16 / Q17 を新設
>
> * v3.1（2026-05-29、提案のみ、不採用）: L1 機能面の穴 3 件（Q11 / Q13 / Q12）のみ修正する +1d 案。ユーザー指示で C 全採用 = v3.2 に進んだため未採用
>
> * v3.2（2026-05-29）: 「機能面 L1 / アーキテクチャ面 L2 / 保守運用面 L3」の 3 層整理に基づく **通常運用版全採用 = オプション C**。Q1 = C（custom Strategy）/ Q4 = A + SSM 切替 / Q10 = B（custom Strategy 連動）/ Q11 = A + Strands graceful shutdown 80s / Q12 = D + 多層 / Q13 = D + S3 export / Q14 = A（PBT 全面）/ Q16 = B（custom Strategy）/ Q17 = B（dev / staging / prd 3 endpoint）に変更
>
> * **v3.3（本版、2026-05-29）**: v3.2 のセルフレビュー結果を反映。**Critical 6 件**（C-1 Q4 SSM の P0/P1 分類矛盾 / C-2 Memory expirationDuration の 7 日 vs 90 日混乱 / C-3 5/30 マイルストーン矛盾 / C-4 §1.4 Infra 層表が v3 のまま / C-5 出力 SSM 不整合 / C-6 DAG 論理矛盾）と **Major 6 件**（M-1 §4 評価軸 v3 のまま / M-2 Q12 選択肢 D 再定義 / M-3 Q1/Q10 段階実装方針 / M-4 IAM ハードコード問題 / M-5 RuntimeEndpoint qualifier 命名 / M-6 Unit-2 申し送り表記）を一括修正
>
> 参照（Inception）: [unit-of-work.md Unit-3](../../../inception/application-design/unit-of-work.md#unit-3-debate-論破チャット-uc-01) / [components.md B-02](../../../inception/application-design/components.md) / [services.md SVC-01](../../../inception/application-design/services.md#svc-01-debate-orchestration-service) / [stories.md US-01-01〜05](../../../inception/user-stories/stories.md) / [requirements.md FR-DEBATE-01〜09](../../../inception/requirements/requirements.md)
>
> 参照（Unit-1 正本、main 由来）: [Unit-1 functional-design](../../unit-1-platform/functional-design/) / [nfr-design](../../unit-1-platform/nfr-design/) / [infrastructure-design](../../unit-1-platform/infrastructure-design/) / [shared-infrastructure.md](../../shared-infrastructure.md)
>
> 参照（AgentCore CDK）: [aws-cdk-lib.aws\_bedrockagentcore README](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_bedrockagentcore-readme.html)（L2 安定、Tokyo apne1 GA 確認済み 2026-05-29）
>
> 参照（ステアリング）: [AGENTS.md](../../../../.kiro/steering/AGENTS.md) / [api-contracts.md](../../../../.kiro/steering/api-contracts.md) / [tech-cdk.md](../../../../.kiro/steering/tech-cdk.md) / [tech-python.md](../../../../.kiro/steering/tech-python.md)

***

## 0. ステージ判定

| 項目                     | 判定                                                                                                                                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Functional Design 実行判定 | **EXECUTE（深め）** — Unit-3 は M-1 + M-2 併走プロンプト合成 / Bedrock SSE ストリーミング / 90 秒タイマー / クールダウン / 個別最適化学習 / 肯定フィードバック発火など、ビジネスロジックの複雑度が 8 Units 中で最も高い                                                                     |
| 深さレベル                  | **Comprehensive** — UC-01 はテーマ「人をダメにする」の中核機能                                                                                                                                                                        |
| Part 1 の目的             | 設計判断ポイントを `[Answer]:` タグで投げ、確定内容を Part 2 で具体仕様書に展開                                                                                                                                                                  |
| Part 2 の目的             | 確定後に Mobile（M-04 DebateScreen）/ Backend（B-02 = AgentCore Runtime + Memory）/ プロンプト合成 / 個別最適化戦略 / Hypothesis PBT 戦略を明文化                                                                                               |
| Unit-1 との関係            | Unit-1 main 正本（Cognito User Pool / KMS / VPC / Lambda Layer / SSM）を SSM 経由で参照し、AgentCore Runtime と Memory が連携する。Unit-1 の API Gateway / Lambda Authorizer / DomainError 体系は **Unit-3 では使わない**（AgentCore Runtime が代替） |

***

## 1. Unit-3 のスコープ再確認（v3.3 = AgentCore 採用版、セルフレビュー修正反映）

### 1.1 Mobile 層（`mobile/src/features/debate/`）

| ID   | コンポーネント        | 主な責務                                                                                                                        |
| ---- | -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| M-04 | `DebateScreen` | 論破チャット UI / タイピング演出 / 90 秒カウントダウン / 事実-心理 2 軸ラベル / Amazon 遷移確認オーバーレイ / 遷移後の **肯定フィードバックトースト**（FR-DEBATE-09 / M-2 ドーパミン回路強化） |

依存（Unit-1 main 由来）:

* M-12 ApiClient（REST 用、他 Unit で使う）— **Unit-3 では使わない**

* M-13 Telemetry（`debate.session_started` / `debate.token_streamed` / `debate.refused` / `debate.agreed` / `debate.session_complete{reason}` / `debate.cooldown_triggered` / `debate.affirmation_shown` / `debate.moderation_blocked` / `debate.graceful_shutdown_initiated` / `debate.stress_estimated` を追記。タイムアウトは `debate.session_complete reason='graceful_timeout' | 'hard_timeout'` に統合、v3.3 修正）

* M-01 AppShell の Deep Link ルーティング（`yudane://debate/{sessionId}`）

依存（Unit-3 新規追加、AgentCore SDK 経由）:

* **`@aws-sdk/client-bedrock-agentcore`**（npm）の `InvokeAgentRuntimeCommand` を呼ぶ薄いラッパー `mobile/src/features/debate/agentcore-client.ts` を新設

* AsyncIterable<Uint8Array> として SSE ストリームを受信、`event-source-parser` 等で 4 種イベント（token / turn\_complete / session\_complete / error）に変換して UI に流す

### 1.2 Backend 層（**AgentCore Runtime にホストされる Strands Agent**）

| ID   | コンポーネント            | 主な責務                                                                                                                                                                             |
| ---- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B-02 | `DebateLlmService` | **AgentCore Runtime にデプロイされる Strands Agent**。論破プロンプト合成（M-1 事実 + 心理 2 軸 + M-2 ストレス × ご褒美軸の併走）/ Bedrock Claude Haiku 4.5 ストリーミング / **AgentCore Memory から個別最適化情報を取得** / 肯定フィードバック生成 |

**Backend の構造**:

```
backend/src/debate/
├── main.py                  # BedrockAgentCoreApp + @app.entrypoint
├── prompts/
│   ├── base.py              # System ブロック
│   ├── m1_fact_axis.py      # 事実軸テンプレート
│   ├── m1_psychology_axis.py # 心理軸テンプレート
│   ├── m2_reward_axis.py    # ストレス × ご褒美軸（FR-DEBATE-09）
│   ├── affirmation.py       # 肯定フィードバック生成
│   └── compose.py           # 4 要素を合成する公開関数
├── memory_hooks.py          # MemoryHook（Strands hooks）で個別最適化を自動注入
├── stress.py                # ストレスレベル推定（Memory から取得 + ヒューリスティック）
└── requirements.txt         # bedrock-agentcore + strands-agents + boto3
```

依存（Unit-1 main 由来、SSM 経由で参照）:

* B-12 AuditLogger（Lambda Layer）— AgentCore Runtime にも適用可能、利用継続

* DomainError 体系 — エラー伝播のため import 利用

* Cognito User Pool ID（`/yudane/<env>/platform/userpool-id`）— AgentCore Runtime の Cognito Authorizer で再利用

* KMS Key ARN（`/yudane/<env>/platform/kms-key-arn`）— AgentCore Memory の暗号化に再利用

依存（他 Unit、Mock 先行で Unit-3 単独着手可能）:

* B-13 AmazonTransitionRecorder（Unit-4 Reel owner、論破成功時に呼び出し）

* B-10 AssociatesLinkGenerator（Unit-4 Reel owner、Special Link 生成）

* B-07 CalendarPredictionService（Unit-6 Calendar owner、予定カテゴリ context）— Mock 先行

* B-11 CreatorsApiClient（Unit-5 Cart owner、商品メタ）— Mock 先行可

### 1.3 Shared 層への寄与

* `shared/schema/paths/debate.yaml`（main 由来の骨格）→ **削除候補**。AgentCore Runtime を直接呼ぶため OpenAPI 不要。Mobile 用に「`bedrock-agentcore:InvokeAgentRuntime` の呼び出し仕様」を `shared/agentcore-contracts/` 等の別パッケージで定義する案を Q17 で議論

* `shared/telemetry-contracts/`: イベントカタログに Unit-3 イベントを追記（変更なし）

### 1.4 Infra 層（`infra/lib/debate-stack.ts`、新規作成、v3.3 確定）

| 項目                | 内容                                                                                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Stack 名           | `debate-<env>-stack`（[shared-infrastructure.md §2 命名規約](../../shared-infrastructure.md)）                                                               |
| AgentCore Runtime | `agentcore.Runtime`（L2 安定、`aws-cdk-lib/aws-bedrockagentcore`）/ Direct Code Deploy（S3 zip、ECR 不要）/ Cognito Authorizer / Public Network / `lifecycleConfiguration: { idleTimeoutSeconds: 120, maxLifetimeSeconds: 120 }` + **Strands Agent 内 graceful shutdown 80s フック**（v3.2 Q11） |
| AgentCore Memory  | `agentcore.Memory`（L2 安定）/ **`expirationDuration: 90 日` 単一値**（events + strategy records 共通の生存期間、v3.3 C-2 修正）/ userPreference + semantic + **custom Strategy `m1_m2_axis_extractor`**（v3.2 Q1=C / Q16=B）/ **`streamDeliveryResources` で S3 並行書き出し**（v3.2 Q13）/ Unit-1 KMS 再利用 |
| RuntimeEndpoint   | **dev / staging / prd Stack それぞれに `live` + `canary` の 2 endpoint**（v3.3 M-5 修正、Q17 = B）。Mobile は `qualifier: 'live'` を既定使用、決勝直前のカナリアリリースで `qualifier: 'canary'` 切替テスト |
| S3 (Memory Export) | `yudane-debate-<env>-memory-export` bucket（KMS 暗号化、Lifecycle Standard → IA (30d) → Glacier (90d) → 削除 (365d)、Athena/Glue 連携、v3.2 Q13） |
| DDB (Cooldowns)   | `yudane-debate-<env>-cooldowns`（KMS + TTL 30 日 + PITR、v3.2 Q2 唯一の自前テーブル） |
| Bedrock Guardrails | DENIED_TOPICS = NG-1〜NG-8、streaming 対応版（v3.2 Q12）、Strands `bedrock_kwargs.guardrailIdentifier` 経由 |
| IAM               | **`runtime.grantInvokeBedrockModel` でワイルドカード**（v3.3 M-4 修正）: `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-haiku-4-5` + `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-6`（Q4 SSM 切替で Sonnet 4.6 に切り替えた際も AccessDenied を発生させない、Sonnet 4.6 自体の利用は B-305 backlog だが IAM だけ先行付与）+ Memory R/W + DDB R/W + S3 PutObject + SSM GetParameter |
| 共有 SSM 参照         | `/yudane/<env>/platform/{userpool-id, userpool-client-id, kms-key-arn, alerts-topic-arn, auditlogger-layer-arn}`                                       |
| 出力 SSM            | **`/yudane/<env>/debate/{runtime-arn, memory-id, runtime-endpoint-live-arn, runtime-endpoint-canary-arn, model-id, memory-export-bucket-arn, cooldowns-table-arn, kill-switch}`**（v3.3 C-5 + NC2-2 修正、8 個に拡張） |
| Observability     | AgentCore 標準の CloudWatch Logs + OTEL（OpenTelemetry）/ B-12.metric の EMF メトリクス（命名 `debate.<domain>.<metric>`）                                            |

### 1.5 v2 → v3.3 で消えるもの（重要）

> 表中「v2 で必要だった項目」は v2 = main マージ後の自前 Lambda + DDB + Lambda Streaming 案。v3 で AgentCore マネージドリソースに置換、v3.3 で記述の正確化を実施。

| v2 で必要だった項目                                  | v3 / v3.3 での扱い                                                                            | 削減効果                            |
| -------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------- |
| `DebateSessions` テーブル（Q1 v2）                    | **削除**（AgentCore Memory が代替）                                                       | DDB 1 テーブル + IAM 削減             |
| `DebateMessages` テーブル（Q1 / Q13 v2）               | **削除**（AgentCore Memory STM 部分が代替、`expirationDuration: 90 日` の events として生存）                       | DDB 1 テーブル削減                    |
| `DebateOutcomes` テーブル（Q10 / Q13 v2）              | **削除**（AgentCore Memory userPreference + custom Strategy が代替）                               | DDB 1 テーブル削減、Unit-2 申し送り消滅      |
| `DebateCooldowns` テーブル（Q2）                   | **保持**（クールダウン判定は短時間 state、Memory には不向き）                                            | DDB 1 テーブルのみ残る                  |
| `UserActivitySummary` テーブル（Q8 v2、Unit-2 への申し送り） | **削除**（AgentCore Memory semantic Strategy が代替）                                     | Unit-2 申し送り消滅                   |
| API Gateway REST + Lambda Authorizer（Q5 v2）     | **削除**（AgentCore Runtime が直接 Cognito JWT 検証）                                       | Unit-1 の `paths/debate.yaml` 削除 |
| Lambda Response Streaming（Q6 v2 = Lambda Streaming 案）                | **削除**（AgentCore Runtime の `yield` が標準対応）                                          | 自前 SSE プロトコル設計 0                |
| 自前 SSE フレーム設計（Q3 v2）                            | **保留**（Strands streaming が標準フォーマット、Mobile の event parser だけ実装）                     | 設計工数大幅削減                        |
| 90 秒 Lambda timeout 設定（Q11 v2 = Lambda timeout 案）                  | **AgentCore Runtime `lifecycleConfiguration` + Strands graceful shutdown 80s で代替**（v3.3 M-1/L-1 修正反映） | サーバー権威タイマー maintenance 工数 0     |
| Bedrock Mock Lambda（Q15 v2）                     | **`agentcore dev` ローカル開発サーバー で代替**（公式推奨）                                       | Mock 構築工数 0                     |

***

## 2. 設計判断ポイント（Part 1 の質問）

各設問は推奨案 + 根拠付きの選択肢で構成。`[Answer]:` タグに回答してください。

***

### Q1. セッション状態管理（v3: AgentCore Memory に全面移譲）

**v3 改訂内容**: v2 の `DebateSessions` / `DebateMessages` 自前 DDB テーブル設計を破棄、AgentCore Memory で代替。

**背景**: AgentCore Memory は STM（Short-Term Memory、`create_event` で会話ターン保存）+ LTM（Long-Term Memory、ストラテジーで自動抽出）の二層構造。論破セッションのターン履歴は STM に、個別最適化用の軸 / 翻意ターン数 / 成否は LTM の `userPreference` Strategy に保存される。

**Memory のリソース構造**:

* 1 ユーザー = `actor_id`（Cognito sub）

* 1 論破セッション = `session_id`（ULID）

* ターン保存 = `memory_client.create_event(messages=[(user_input, "USER"), (ai_response, "ASSISTANT")])`

* 直近ターン取得 = `memory_client.get_last_k_turns(actor_id, session_id, k=3)`

* 個別最適化情報取得 = `memory_client.retrieve_memories(namespace=f"/user/debate/{actor_id}/", query="論破で翻意した軸", top_k=5)`

**選択肢**:

* **A. AgentCore Memory STM のみ採用**（短期会話履歴のみ）— LTM ストラテジーなし、個別最適化は別途実装。最小構成、ただし FR-DEBATE-04 / US-01-04 の個別最適化に弱い

* **B. AgentCore Memory STM + 組み込み Strategy（userPreference + semantic）** — 2 種ストラテジーで個別最適化を自動化。**Q8 / Q10 がこれで完全置換**。組み込みストラテジーは推奨案

* **C. AgentCore Memory STM + custom Strategy**（M-1 / M-2 メカニズム特化のカスタムプロンプト）— Haiku 4.5 ベースのカスタム抽出 / 統合プロンプトで論破成功パターンを抽出。最強の個別最適化、追加実装 0.5 日

* **D. AgentCore Memory 不採用、自前 DDB**（v2 案）— v3 で破棄

**推奨**: **B**。理由 — (1) 組み込みストラテジー 2 種で FR-DEBATE-04 / US-01-04 / FR-DEBATE-09 の要件を満たせる、(2) custom Strategy（C）は決勝向け強化として backlog 化可能、(3) 工数最小、(4) Unit-2 / Unit-7 への申し送り Q8 / Q10 が消える。

\[Answer]:**C（v3.2 通常運用版全採用）** — MVP から custom Strategy を採用。M-1 / M-2 メカニズム特化のカスタム抽出プロンプト（Haiku 4.5 ベース）で論破成功パターンを正確に分類。組み込み 2 種 + custom 1 種の 3 ストラテジー構成（`userPreferenceMemoryStrategy(name="debate_outcomes")` + `semanticMemoryStrategy(name="stress_signals")` + `customMemoryStrategy(name="m1_m2_axis_extractor")`）。追加 +0.5d。Q10 = B / Q16 = B と整合。ハッカソン創造性軸「ダメ化メカニズム特化 AI」をアピール材料化。

**段階実装方針（v3.3 M-3 修正）**: P0 = 組み込み 2 種（userPreference + semantic）のみで動作 / P1 = custom Strategy 追加。詳細は [task-breakdown.md §2 Q1 行](./task-breakdown.md#2-優先度マトリクスq--phase--person--effort) を参照

***

### Q2. 連続拒否カウンタの増減ロジック（v3: 唯一の自前 DDB テーブル）

**v3 改訂内容**: v2 の方針を維持。AgentCore Memory はクールダウン状態のような短時間 / 高頻度更新の state には不向きなので、`yudane-debate-<env>-cooldowns` テーブルを唯一の自前 DDB として残す。

**Unit-3 で新設するテーブル**: `yudane-debate-<env>-cooldowns`

| 属性                   | 型      | 説明                         |
| -------------------- | ------ | -------------------------- |
| `PK`                 | String | `USER#{userId}`            |
| `SK`                 | String | `COOLDOWN#current`         |
| `consecutiveRefuses` | Number | 連続拒否回数                     |
| `lastRefuseAt`       | String | 最終拒否時刻（ISO 8601）           |
| `cooldownUntil`      | String | クールダウン解除時刻（ISO 8601、3 時間後） |
| `ttl`                | Number | UNIX timestamp（30 日後で自動削除） |

**選択肢**:

* **A. session 単位でカウント**（同一 session 内のみ）— 不採用候補

* **B. ユーザー横断、24h 経過で 0 リセット**

* **C. ユーザー横断、`cooldownUntil`** **期限切れで 0 リセット（3h 自然解除）** — v2 推奨案を継承

**推奨**: **C**。理由 — (1) 3 時間クールダウンは M-2 ドーパミン回路を完全に冷却するには長すぎず離脱を防ぐ絶妙なライン、(2) US-01-05 AC-1「**当日**は論破モード停止」は AC-4「ユーザー手動解除」の存在で 3h でも要件を満たせる、(3) Unit-7 への申し送り（Q9）と整合。

\[Answer]:C

***

### Q3. ストリーミング配信（v3: AgentCore Runtime + Strands streaming）

**v3 改訂内容**: v2 の自前 SSE プロトコル設計（YUDANE 独自 4 種イベント）を破棄。AgentCore Runtime の `yield` で Strands Agent の標準ストリームをそのまま配信。

**Strands Agent の streaming 標準フォーマット**:

```python
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
agent = Agent(model="anthropic.claude-haiku-4-5", tools=[...], callback_handler=None)

@app.entrypoint
async def debate_handler(payload, context):
    user_message = payload.get("user_input")
    asin = payload.get("asin")
    stress_level = payload.get("stress_level")  # クライアントから渡す or Memory から取得
    
    # M-1 + M-2 併走プロンプト合成
    composed_prompt = compose_debate_prompt(user_message, asin, stress_level, ...)
    
    # Strands streaming（イベント形式は Strands SDK 標準）
    async for event in agent.stream_async(composed_prompt):
        yield event  # Mobile に AsyncIterable<Uint8Array> として配信
```

**Mobile 側の受信**:

```typescript
// mobile/src/features/debate/agentcore-client.ts
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';

const client = new BedrockAgentCoreClient({ region: 'ap-northeast-1' });
const response = await client.send(new InvokeAgentRuntimeCommand({
  agentRuntimeArn,
  payload: new TextEncoder().encode(JSON.stringify({ user_input, asin, stress_level })),
  runtimeSessionId: `${sessionId}_${actorId}`,  // 26 + 1 + 36 = 63 文字、33-256 を満たす（v3.3 M6-1）
  qualifier: 'live',  // RuntimeEndpoint name
}));
// response.response は AsyncIterable<Uint8Array>、event-source-parser でパース
```

**選択肢**:

* **A. Strands Agent のイベント形式をそのまま転送**（推奨）— `agent.stream_async` の出力をそのまま `yield`、Mobile 側でパース。Strands 標準形式は OpenAI Chat Completion 風 + tool\_use イベント

* **B. Lambda 内で Strands イベントを YUDANE 独自 4 種イベントに変換**（v2 案）— 抽象化レイヤを挟む。Mobile 側のクライアント実装が単純化、ただし Lambda 内変換コードが追加 + Strands 仕様変更追従コスト

* **C. NDJSON / WebSocket** — 不採用候補

**推奨**: **A**。理由 — (1) Strands streaming は標準的な OpenAI 互換 chunk 形式 + tool\_use 拡張、Mobile 側のパースは `event-source-parser` などの OSS で対応可、(2) AgentCore Runtime の `yield` の意図は Strands streaming をそのまま流すこと、抽象化は Strands SDK 側で責任分担、(3) M-1/M-2 軸の判別は Mobile 側で `delta` のテキスト中の `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` マーカー or Strands tool\_use で実装。詳細は Part 2 で確定。

\[Answer]:A

***

### Q4. Bedrock モデル選択（変更なし、Haiku 4.5 単独）

**選択肢**:

* **A. Haiku 4.5 単独** — parallel-dev-prerequisites C-2 確定

* B. Haiku + 同期 Sonnet 4.6

* C. Haiku + 事前 cache Sonnet 4.6

**推奨**: **A**（変更なし）。Strands Agent の `model="anthropic.claude-haiku-4-5"` で指定。

\[Answer]:**A + SSM 切替（v3.2 通常運用版、v3.3 で P0 採用）** — `model_id` を SSM Parameter `/yudane/<env>/debate/model-id` から読み込む形に変更。MVP 既定値は `anthropic.claude-haiku-4-5`。決勝後の Sonnet 4.6 切替 / モデル aliasing / ロールバックが Stack 再デプロイなしで実現可能。追加 +0.2d。Strands Agent 初期化時に `boto3.client('ssm').get_parameter()` で取得（Lambda 起動時 1 回のみ、Runtime のコールドスタート影響軽微）。

**段階実装方針（v3.3 C-1 修正）**: SSM 切替の仕組み自体は **P0 で採用**（Phase 1 T1.1 の SSM Parameter 作成 + T1.2 の main.py SSM 取得を含める）。Phase 5 の T5.1 は廃止（v3.3 で P0 に組み込んだため）。詳細は [task-breakdown.md §2 Q4 行](./task-breakdown.md#2-優先度マトリクスq--phase--person--effort) を参照。

**IAM 整合性（v3.3 M-4 修正）**: SSM 値で Sonnet 4.6 に切り替えた瞬間に Bedrock AccessDenied を発生させないよう、Stack 合成時に **Haiku 4.5 + Sonnet 4.6 の 2 ARN を IAM ポリシーに先行付与**（§1.4 IAM 行と整合）

***

### Q5. クライアント認証（v3: AgentCore Runtime の Cognito Authorizer）

**v3 改訂内容**: v2 の「Unit-1 platform-stack の API Gateway REST + Lambda Authorizer」を Unit-3 では使わない。AgentCore Runtime に Cognito Authorizer を直接設定。

**`agentcore.RuntimeAuthorizerConfiguration.cognito()`** **の設定**:

```typescript
// infra/lib/debate-stack.ts
import { aws_bedrockagentcore as agentcore } from 'aws-cdk-lib';
import { aws_ssm as ssm } from 'aws-cdk-lib';

const userPoolId = ssm.StringParameter.valueForStringParameter(
  this, '/yudane/dev/platform/userpool-id'  // Unit-1 platform-stack の出力
);
const userPoolClientId = ssm.StringParameter.valueForStringParameter(
  this, '/yudane/dev/platform/userpool-client-id'
);

const debateRuntime = new agentcore.Runtime(this, 'DebateRuntime', {
  // ...
  authorizerConfiguration: agentcore.RuntimeAuthorizerConfiguration.cognito({
    userPoolId,
    clientIds: [userPoolClientId],
    // 追加: discoveryUrl は Cognito 標準で自動解決
  }),
});
```

**選択肢**:

* **A. Cognito Authorizer**（推奨）— Unit-1 既存の Cognito User Pool を SSM 経由で再利用。最も Unit-1 整合

* **B. JWT Authorizer**（カスタム JWT、Cognito 以外）— 不要

* **C. IAM Authentication**（モバイルから IAM 認証）— Cognito Identity Pool 経由になり追加複雑度

* **D. OAuth Authorizer** — 不要

**推奨**: **A**。理由 — (1) Unit-1 既存資産を 100% 再利用、(2) 他 Unit（Unit-2 / 4 / 5）が同じ Cognito を使うため整合性最強、(3) `actor_id = JWT.sub` が AgentCore Memory にそのまま流せる。

\[Answer]:A

***

### Q6. Network Configuration（v3: Public Network、VPC 不要）

**v3 改訂内容**: v2 の VPC 内 Lambda 配置を破棄。AgentCore Runtime は Public Network モードで動作させ、Bedrock 呼び出しは AWS 内部経路で完結（VPC Endpoint 不要）。

**`agentcore.RuntimeNetworkConfiguration`** **の選択肢**:

```typescript
// 選択肢 A（推奨）
networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork()

// 選択肢 B
networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingVpc({
  vpc: platformVpc,           // Unit-1 platform-stack VPC を SSM 経由で参照
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  securityGroups: [lambdaSg],
})
```

**選択肢**:

* **A. Public Network**（推奨）— AgentCore Runtime デフォルト、Bedrock InvokeModel は AWS 内部経路、VPC 不要、Cognito Authorizer で十分なセキュリティ

* **B. VPC（Unit-1 platform-stack VPC を再利用）** — DynamoDB（Cooldowns）アクセスに VPC Gateway Endpoint 経由を強制したい場合。ただし AgentCore Memory は AWS マネージド、VPC Endpoint 不要

**推奨**: **A**。理由 — (1) AgentCore Runtime のコンテナは AWS マネージドで隔離、Public Network = インターネット直結ではなく Cognito Authorizer 必須の認証経路、(2) Bedrock / DynamoDB へは AWS 内部経路、(3) Memory は API GW 経由でアクセス、VPC Endpoint 不要、(4) コールドスタート ENI リスクゼロ、(5) 開発者の VPC 設定 / SG 管理コスト 0。

\[Answer]:**A** — Public Network 採用。VPC 配置の追加複雑度は不要

***

### Q7. プロンプト合成のテンプレート管理（変更なし）

**選択肢**:

* **A. Python コード内に文字列定数として埋め込み +** **`backend/src/debate/prompts/`** **配下で構造化**

* B. SSM Parameter Store

* C. Shared パッケージ化

* D. DynamoDB `PromptTemplates`

* E. ハイブリッド

**推奨**: **A**（v2 から維持）。理由 — Strands Agent の `system_prompt` パラメータに渡す形式で、`compose_debate_prompt()` 関数が呼び出し時に動的合成。

\[Answer]:**A** — `backend/src/debate/prompts/` 配下の Python モジュールで構造化（`base.py` / `m1_fact_axis.py` / `m1_psychology_axis.py` / `m2_reward_axis.py` / `affirmation.py` / `compose.py`）

***

### Q8. ストレスレベル推定（v3: AgentCore Memory semantic Strategy で自動）

**v3 改訂内容**: v2 の「Unit-2 の `UserActivitySummary` テーブル + B-08 集計」を破棄。AgentCore Memory の `semantic` Strategy が会話履歴 + Telemetry イベントから自動抽出。

**動作の概要**:

1. Telemetry（`debate.session_started`, `cart.intercept_received`, `auth.signin_late_night` 等）と論破会話を **同じ Memory リソース** に保存
2. `semanticMemoryStrategy` の namespace `/user/stress-signals/{actor_id}/` で「直近の活動パターン」を自動抽出
3. 論破セッション開始時に `memory_client.retrieve_memories(namespace=..., query="ユーザーの最近のストレス兆候", top_k=3)` で取得
4. 取得結果から Strands Agent 内のヒューリスティック関数で `stress_level: low | mid | high` に変換

**選択肢**:

* **A. Memory semantic Strategy のみ**（推奨）— LLM ベースの自動抽出に全面依存。設定 0.5 日、運用コスト 0

* **B. Memory + 軽量ヒューリスティック併用** — Memory が抽出した signals + Lambda 内のシンプルなルール（深夜帯 = +1, 連続論破拒否 = +1）で `stress_level` 算出

* **C. Memory 不採用、Unit-2 への申し送り**（v2 案、破棄）

**推奨**: **B**。理由 — (1) 純粋な Memory 依存（A）は初期データが少ない Day 1 では精度低、(2) 軽量ヒューリスティックで Day 1 から動作、Memory が学習進むと精度向上、(3) Strands Agent 内の Python 関数で完結、追加 Lambda 不要、(4) **Unit-2 への申し送り消滅**。

\[Answer]:**B** — Memory semantic Strategy + 軽量ヒューリスティック併用。Day 1 はヒューリスティック支配、Memory 学習進行で精度向上

***

### Q9. クールダウン解除フロー（変更なし、Unit-7 申し送り）

**選択肢**:

* A. `forceUnlock` フラグ

* B. 専用 release エンドポイント

* C. DELETE + If-Match

* **D. Unit-7 Safeguard** **`PATCH /v1/safeguard`** **で** **`cooldownReleased`** **/** **`releaseReason`**（v2 推奨を継承）

**推奨**: **D**。Unit-7 への申し送り内容は v2 から変更なし。ただし v3 では Unit-3 から Unit-7 を呼ぶ経路は Mobile が直接 Unit-7 の API Gateway にアクセス（Unit-3 AgentCore Runtime → Unit-7 ではない）。

\[Answer]:**D** — Unit-7 Safeguard `PATCH /v1/safeguard` で `cooldownReleased` / `releaseReason` を扱う。Mobile が直接呼ぶ。Unit-7 への申し送り維持（task-breakdown.md にも記載）

***

### Q10. 個別最適化学習（v3: AgentCore Memory userPreference Strategy で自動）

**v3 改訂内容**: v2 の「`yudane-debate-<env>-outcomes` DDB + Unit-2 B-08 集約」を破棄。AgentCore Memory の `userPreference` Strategy が会話から自動抽出。

**動作の概要**:

1. 論破ターンごとに `memory_client.create_event(messages=[(user_input, "USER"), (ai_response, "ASSISTANT")], metadata={"axis": "fact", "outcome": "agreed", "turn": 3})` で保存
2. `userPreferenceMemoryStrategy` の namespace `/user/debate/{actor_id}/` で「論破で翻意した軸 / ターン数 / 商品カテゴリの好み」を自動抽出
3. 論破セッション開始時に `memory_client.retrieve_memories(namespace=..., query="このユーザーが論破で翻意した軸の傾向", top_k=5)` で取得
4. プロンプト合成時に Strands Agent の `system_prompt` に組み込み

**選択肢**:

* **A. Memory userPreference Strategy のみ**（推奨）— 完全自動、設定 0.5 日

* **B. Memory + custom Strategy**（M-1/M-2 特化）— Haiku 4.5 ベースのカスタム抽出プロンプトで論破ロジック特化の精度向上、追加実装 0.5 日

* **C. Memory 不採用、自前 DDB**（v2 案、破棄）

**推奨**: **A → 決勝前に B 検証**。理由 — (1) 組み込み Strategy で MVP は十分、(2) custom Strategy は backlog B-303 で決勝前評価、(3) **Unit-2 への申し送り消滅**。

\[Answer]:**B（v3.2 通常運用版全採用）** — MVP から `userPreferenceMemoryStrategy` + custom Strategy（Haiku 4.5 ベース）併用。論破ロジック特化の精度向上を狙う。Q1 = C / Q16 = B と整合。追加 +0.5d。

**段階実装方針（v3.3 M-3 修正）**: P0 = `userPreferenceMemoryStrategy` のみ動作 / P1 = custom Strategy 連動追加。詳細は [task-breakdown.md §2 Q10 行](./task-breakdown.md#2-優先度マトリクスq--phase--person--effort) を参照

***

### Q11. 90 秒タイマー（v3: AgentCore Runtime lifecycleConfiguration）

**v3 改訂内容**: v2 の「Lambda timeout 120s + サーバー側 endsAt 計算」を AgentCore Runtime の `lifecycleConfiguration` に置換。

**`lifecycleConfiguration`** **の設定**:

```typescript
lifecycleConfiguration: {
  idleTimeoutSeconds: 120,    // 論破は連続会話なので idle = 90s + バッファ 30s
  maxLifetimeSeconds: 120,    // 強制終了も 120s
}
```

**選択肢**:

* **A. AgentCore Runtime lifecycleConfiguration 単独**（推奨）— サーバー側強制終了、サーバー権威、Mobile は `endsAt = sessionStartedAt + 90s` で UI タイマー表示

* B. クライアント単独タイマー — 改竄リスク

* C. WebSocket Heartbeat — 過剰

**推奨**: **A**。理由 — (1) AgentCore Runtime の microVM が 120s で自動停止、Mobile はそれ以降の `InvokeAgentRuntime` を 410 Gone で受け取る、(2) `endsAt` は Mobile が `sessionStartedAt + 90s` で計算（NTP 同期前提）、(3) 90s 経過後の Bedrock 呼び出しは Strands Agent 内部で `if elapsed > 90: stop` チェック追加でも可、(4) Lambda timeout 設定 / `DebateSessions.endsAt` テーブル設計の工数 0。

\[Answer]:**A + Strands graceful shutdown 80s（v3.2 通常運用版、L1 機能面修正）** — Strands Agent 内に `if elapsed > 80: stop_streaming_with_summary()` フックを追加し、残り 10 秒で「ここまでの論破サマリ」を生成して綺麗にクローズ。論破文の途中切断（M-1 体験を阻害する重大不具合）を防止。`lifecycleConfiguration.idleTimeoutSeconds: 120` / `maxLifetimeSeconds: 120` は維持し、サーバー権威タイマー機能はそのまま。追加 +0.3d

***

### Q12. 出力モデレーション（v3.3 で選択肢 D を「多層防御」に再定義）

**選択肢**:

* A. プロンプトガードレールのみ

* B. プロンプト + Guardrails 後処理

* **C. プロンプト + Bedrock Guardrails streaming 対応**（v2 推奨を継承）

* **D. 多層防御: プロンプト + Bedrock Guardrails streaming + 正規表現検査**（v3.3 で再定義、3 層で NG-1〜8 検出）

**推奨**: **C**。Strands Agent の Bedrock model 呼び出しに Guardrails を関連付ける（`agent = Agent(model=..., bedrock_kwargs={"guardrailIdentifier": guardrailId, "guardrailVersion": "DRAFT"})`）。

\[Answer]:**D（v3.2 通常運用版全採用、v3.3 で選択肢 D を多層防御に再定義）** — プロンプトガードレール + Bedrock Guardrails streaming 対応 + 出力後正規表現検査の **3 層多層防御**。NG-1〜NG-8（特に NG-6 脅迫・罪悪感強要）の検出を 3 層で担保。streaming chunk ごとに正規表現マッチング（M-2 を NG-6 に滑らせない安全装置）。Bedrock Guardrails の `outputAssessments` も併用。Strands Agent の `callback_handler` で各 chunk を後処理。追加 +0.5d

***

### Q13. 論破メッセージ・履歴の永続期間（v3: AgentCore Memory `expirationDuration`、v3.3 で正確化）

**v3 改訂内容**: v2 の「DDB TTL 規約」を AgentCore Memory の `expirationDuration` に置換。

**v3.3 重要修正**: AgentCore Memory の `expirationDuration` は **events（STM 相当）と strategy records（LTM 相当）両方に共通で適用される単一値**（7-365 日の範囲内）。STM だけ 7 日 / LTM だけ 90 日のように **別々に設定することはできない**。v3 で記載していた「STM 7 日 / LTM 90 日」は AgentCore Memory の仕様と乖離していたため、v3.3 で **expirationDuration: 90 日 単一値 + S3 export Lifecycle で 365 日保全** に修正。

**TTL マトリクス（v3.3 確定）**:

| データ               | 保管先                                      | 保持期間                                                                          | 設定方法                                       |
| ----------------- | ---------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------ |
| 生 token テキスト（events） | AgentCore Memory                     | **90 日**（`expirationDuration` 単一値）                                            | `expirationDuration: cdk.Duration.days(90)` |
| 個別最適化メタ（userPreference 抽出 records）      | AgentCore Memory userPreference Strategy | **90 日**（同上、events と同じ生存期間）                                                   | Strategy 設定（events に従う）                                |
| ストレス信号メタ（semantic 抽出 records）     | AgentCore Memory semantic Strategy       | 90 日（同上）                                                                          | 同上                                         |
| M-1/M-2 軸抽出メタ（custom 抽出 records）  | AgentCore Memory custom Strategy   | 90 日（同上）                                                                       | Strategy 設定                                |
| **90 日超のデータ保全**（S3 export） | S3 `yudane-debate-<env>-memory-export`     | **365 日**（Lifecycle: Standard → IA (30d) → Glacier (90d) → 削除 (365d)）         | S3 Lifecycle Rule + Memory `streamDeliveryResources` |
| クールダウン状態          | DDB `yudane-debate-<env>-cooldowns`      | **30 日**（TTL 属性）                                                              | DDB 規約                                     |

**選択肢**:

* A. 永久保存

* B. 30 日（一律）

* C. 7 日 + 集約永続

* **D. ハイブリッド: Memory expirationDuration 90 日 + S3 export Lifecycle で 365 日保全 + 嗜好ベクトル次元 永続**（v2 推奨を v3.3 で正確化）

**推奨**: **D の v3.3 版**。AgentCore Memory の `expirationDuration` は 90 日（PII 最小化）、これを超える Year 1 退化レポート用データは S3 export で 365 日保全。STM / LTM 別期間の概念は AgentCore Memory には存在しない。

**FR-AUTH-06 アカウント削除時**: AgentCore Memory `delete_memory` は memory\_id 単位の削除のみ、ユーザー単位の削除は `delete_all_long_term_memories_in_namespace(namespace=f"/user/.../{actor_id}/")` で対応。Unit-7 のアカウント削除バッチに追加申し送り（軽微）。**v3.3 追加**: S3 export 側も `s3://yudane-debate-<env>-memory-export/<actorId>/` の prefix 削除をアカウント削除バッチに含める。

\[Answer]:**D + Memory `streamDeliveryResources` + S3 export（v3.2 通常運用版、L1 機能面修正、v3.3 で expirationDuration 単一値に正確化）** — Memory `expirationDuration: 90 日` 単一値で events + strategy records 全て同じ生存期間。これを超える長期データは Memory に S3 並行書き出しで保全し、UC-06 逆家計簿 / UC-07 ダメ化ポートフォリオ / Unit-8 Dame Report が必要とする 90 日超の論破履歴を S3 で保全。S3 Lifecycle で Standard → IA (30d) → Glacier (90d) → 削除 (365d)、Unit-1 KMS 暗号化、Athena からクエリ可能。Year 1 退化アーク（M-3 到達証拠）の可視化が成立。追加 +0.5d

***

### Q14. PBT 戦略（v3: 範囲縮小、AgentCore Memory との統合点に重点）

**v3 改訂内容**: v2 の重点 5 関数のうち、AgentCore Memory に置換された 2 つを除外し、新たな統合点に振り直し。

**v3 重点 PBT プロパティ**:

| 関数                                                                  | プロパティ                                                                             | カテゴリ   | v2 → v3 変更             |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------ | ---------------------- |
| `estimate_stress_level()`                                           | 任意の Memory retrieval 結果 + 軽量ヒューリスティック信号で戻り値が `low/mid/high` の 3 種に必ず収まる           | PBT-07 | 維持                     |
| `increment_refuse_count()`                                          | consecutiveRefuses が 3 に達した瞬間 cooldownUntil が必ず +3h で設定される（DDB 唯一の自前実装）           | PBT-03 | 維持                     |
| `compose_prompt()`                                                  | stress\_level=mid/high なら **必ず** ご褒美軸トークンが含まれる（FR-DEBATE-09 不変条件）                 | PBT-03 | 維持                     |
| ~~`decide_outcome()`~~ → **`memory_event_round_trip()`**            | `create_event` → `get_last_k_turns` で同一データが取得可能                                   | PBT-02 | **新規**（Memory 統合検証）    |
| ~~`sse_frame_round_trip()`~~ → **`agentcore_payload_round_trip()`** | `InvokeAgentRuntimeCommand.payload` の serialize → Strands Agent 内 deserialize で一致 | PBT-02 | **新規**（AgentCore 統合検証） |

**選択肢**:

* A. PBT 全面（+ 2-3 日）

* **B. PBT 重点 5 関数（v3 改訂版、推奨）**

* C. PBT 軽量

* D. PBT 無し

**推奨**: **B（v3 改訂版）**。Hypothesis + AgentCore Memory client mock（boto3 stubber）で AgentCore 統合点を property 化。

\[Answer]:**A（v3.2 通常運用版全採用）** — PBT 全面適用（+2-3 日）。重点 5 関数に加え、`prompts/compose.py` 全体（M-1 + M-2 軸併走の不変条件）/ `memory_hooks.py`（Strands hooks の統合点）/ `stress.py`（ヒューリスティック関数）/ Mobile `event-parser.ts`（Strands streaming 標準形式パース）/ `agentcore-client.ts`（payload round-trip）にも property を拡張。PBT-01〜10 の Coverage を 70% → 85% に引き上げ。Hypothesis（Python）+ fast-check（TypeScript）併用。追加 +1-2d

***

### Q15. Mock 戦略（v3: `agentcore dev` ローカル開発）

**v3 改訂内容**: v2 の「Bedrock Mock Lambda + Prism」を `agentcore dev` 公式ローカル開発サーバーに置換。

**動作**:

```bash
# backend/src/debate/ で
agentcore dev --port 8080
# ↓
# uvicorn が backend/src/debate/main.py の BedrockAgentCoreApp を hot reload で起動
# Bedrock 呼び出しは local AWS credential 経由で dev リージョン（apne1）へ
# Memory は dev 環境の AgentCore Memory リソースに直接保存（local mock 不要）

# 別ターミナルで Mobile から呼ぶ:
agentcore invoke --dev '{"user_input": "...", "asin": "B0...", "stress_level": "mid"}'
```

**選択肢**:

* **A.** **`agentcore dev`** **公式ローカル開発サーバー + dev 環境 Bedrock + dev 環境 Memory**（推奨）

* B. 完全 Mock（Bedrock Mock + Memory Local Stack）— LocalStack の AgentCore 対応が不確定、過剰

* C. Stage 1 から実 Bedrock + 実 Memory（dev 環境）— A と実質同じ

**推奨**: **A**。理由 — (1) `agentcore dev` は公式の hot reload 開発サーバー、(2) Bedrock dev 課金は Haiku 4.5 で 1 セッション $0.001 程度、$10/日予算で十分、(3) Memory も dev 環境に直接書き込む設計で local mock 不要、(4) Member B が Day 1 から実環境動作確認、Mock 構築工数 0。

\[Answer]:**A** — `agentcore dev` 公式ローカル開発サーバー + dev 環境 Bedrock + dev 環境 Memory。Bedrock 課金は $10/日上限で Cost Anomaly Detection 設定（Unit-1 既存）

***

### Q16. AgentCore Memory ストラテジー設計（v3 新設）

**背景**: Memory の `userPreference` + `semantic` 組み込みストラテジーで MVP は十分（Q1 = B 推奨）。ただし、決勝向けに **M-1 / M-2 メカニズム特化のカスタム抽出プロンプト** で精度向上の余地あり。

**選択肢**:

* **A. MVP は組み込みストラテジー 2 種、決勝向けに custom Strategy 評価**（推奨）

  * `userPreferenceMemoryStrategy(name="debate_outcomes", namespaces=["/user/debate/{actorId}/"])`

  * `semanticMemoryStrategy(name="stress_signals", namespaces=["/user/stress/{actorId}/"])`

  * custom Strategy は backlog B-303 で決勝前再評価

* B. MVP から custom Strategy 採用 — 0.5-1 日追加実装、Haiku 4.5 ベースのカスタム抽出プロンプトで M-1 / M-2 軸を正確に分類

* C. summary Strategy も追加 — 論破セッション全体の要約が Year 1 退化の可視化（Unit-8 Dame Report）に有用、ただし現時点では Unit-3 単独では不要

**推奨**: **A**。理由 — (1) MVP の予選 5/30 までに動作確認、(2) custom Strategy は決勝向けの「ダメ化メカニズム特化 AI」アピール材料として残す、(3) 工数最小。

**ストラテジー設定（A 採用時）**:

```typescript
const debateMemory = new agentcore.Memory(this, 'DebateMemory', {
  memoryName: `yudane_debate_${envName}_memory`,
  expirationDuration: cdk.Duration.days(90),  // STM 90日（Q13 と整合）
  // 注: memoryName の規則は a-zA-Z0-9_、ハイフン不可。Unit-3 owner のリソース命名は調整が必要
  kmsKey,
  memoryStrategies: [
    agentcore.MemoryStrategyBase.userPreference({
      name: 'debate_outcomes',
      namespaces: ['/user/debate/{actorId}/'],
    }),
    agentcore.MemoryStrategyBase.semantic({
      name: 'stress_signals',
      namespaces: ['/user/stress/{actorId}/'],
    }),
  ],
});
```

\[Answer]:**B（v3.2 通常運用版全採用）** — MVP から custom Strategy 採用。Q1 = C / Q10 = B と整合。`m1_m2_axis_extractor` という custom Strategy を新設し、Haiku 4.5 ベースのカスタム抽出プロンプトで論破ターン履歴から「翻意した軸（fact / psychology / reward）/ ターン数 / ストレスレベル / 商品カテゴリ」を構造化抽出。`semantic` + `userPreference` + `custom` の 3 ストラテジー構成。Memory `streamDeliveryResources` 設定（Q13 D 採用と整合）で全ストラテジーの抽出結果を S3 にも並行書き出し。追加 +0.5d。

**段階実装方針（v3.3 M-3 修正）**: P0 = 組み込み 2 種（userPreference + semantic）のみ deploy / P1 = custom Strategy `m1_m2_axis_extractor` 追加 deploy + プロンプト合成連動。詳細は [task-breakdown.md §2 Q16 行](./task-breakdown.md#2-優先度マトリクスq--phase--person--effort) を参照

***

### Q17. RuntimeEndpoint 環境戦略（v3 新設）

**背景**: AgentCore Runtime には DEFAULT endpoint が自動生成され、最新版を指す。追加で `RuntimeEndpoint` を作成すると、特定バージョンに固定された endpoint を持てる（dev / staging / prd 戦略）。

**選択肢**:

* **A. DEFAULT endpoint のみ**（推奨、MVP）— Runtime version up は DEFAULT が自動追従、Mobile は最新版を常に使う。dev / prd の分離は **Stack 単位**（`debate-dev-stack` と `debate-prd-stack`）で実現

* B. dev / staging / prd の 3 endpoint — 同一 Runtime に 3 endpoint を作成、Stack 1 つで完結。決勝前のカナリアリリース等に有用

* C. 個人 sandbox endpoint — Member B 個人の検証用。`debate-dev-b-stack` の Runtime 単独で十分（C-4 = C 個人 sandbox suffix と整合）

**推奨**: **A**。理由 — (1) Stack 単位の分離は Unit-1 命名規約 `<unit>-<env>-stack` と整合、(2) MVP に staging endpoint は過剰、決勝前に B 検討で OK、(3) RuntimeEndpoint は別途料金が発生する可能性（要確認）、(4) Mobile 側は Runtime ARN を SSM `/yudane/<env>/debate/runtime-arn` から取得（**4IDC-1 修正により実装は EAS Build 時の `EXPO_PUBLIC_*` 環境変数注入に変更、SSM 値そのものは正本として維持**）、env ごとに切替。

**SSM 出力の構造（A 採用時）**:

```typescript
new ssm.StringParameter(this, 'RuntimeArn', {
  parameterName: `/yudane/${envName}/debate/runtime-arn`,
  stringValue: debateRuntime.runtimeArn,
});
new ssm.StringParameter(this, 'MemoryId', {
  parameterName: `/yudane/${envName}/debate/memory-id`,
  stringValue: debateMemory.memoryId,
});
```

\[Answer]:**B（v3.2 通常運用版全採用、v3.3 で qualifier 命名統一、4IDC-1 修正で Mobile 取得経路変更）** — Stack 単位で env 分離（`debate-dev-stack` / `debate-staging-stack` / `debate-prd-stack`）し、各 Stack 内に **`live` + `canary` の 2 RuntimeEndpoint** を作成。SSM `/yudane/<env>/debate/runtime-endpoint-live-arn` / `runtime-endpoint-canary-arn` は **正本として出力**、Mobile は **EAS Build 時に Expo `app.config.js` 経由で SSM CLI から値を取得して `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` / `_CANARY_ARN` として埋め込み**（Cognito Identity Pool 不採用のため Mobile から SSM API 直接呼び出し不可、4IDC-1 修正）。決勝直前のカナリアリリース時は canary build を OTA Update で 5% 配信。staging Stack で A/B テスト用プロンプト切替テストを実施可能。RuntimeEndpoint の追加料金（推定 $0/endpoint、要確認）は B-307 backlog で Auto-Pause 検討。追加 +0.5d。決勝デモ時は prd Stack の live endpoint を使用

***

## 3. 回答後のアクション（Part 2 Generation で実施）

全 Q1〜Q17 の `[Answer]:` は v3.2 で **オプション C（通常運用版全採用）** で確定済み。実装タスク分解と P0 / P1 / P2 優先度は [task-breakdown.md](./task-breakdown.md) を参照。次のステップは以下の順序で実行する。

1. **回答内容の解析**

   * 矛盾・曖昧さがあれば追加質問

2. **Part 2 Generation: Functional Design ドキュメント生成**（Unit-1 main の構成に整合）

   * `aidlc-docs/construction/unit-3-debate/functional-design/business-logic-model.md` — ALG-DEBATE-START / ALG-STREAM（AgentCore Runtime 内部）/ ALG-COOLDOWN（DDB 唯一の自前ロジック）/ ALG-PROMPT（M-1/M-2 併走合成）/ ALG-MEMORY（Memory 連携）/ ALG-AFFIRMATION のアルゴリズム一覧

   * `aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md` — 論破ルール（DEBATE-01〜N）+ プロンプト合成ルール（PROMPT-01〜N）+ クールダウンルール（COOLDOWN-01〜N）+ Memory 連携ルール（MEMORY-01〜N）+ 出力モデレーションルール（MOD-01〜N）+ 設定値カタログ

   * `aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md` — DebateSession（メモリ上の dataclass、永続化なし）/ DebateOutcome（AgentCore Memory metadata）/ Cooldown（DDB エンティティ、唯一）/ StressSignals（dataclass）/ AgentCorePayload（InvokeAgentRuntime の payload 型）の Pydantic + TypeScript 型 + Mermaid クラス図

   * `aidlc-docs/construction/unit-3-debate/functional-design/strands-agent-design.md` — Strands Agent の構造（system\_prompt / hooks / model）+ MemoryHook の実装方針 + プロンプト合成関数 + 90s タイマー実装（Strands 内部 + Runtime lifecycle 二段）

   * `aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md` — M-1 + M-2 併走プロンプト合成テンプレート、Q7 確定の `backend/src/debate/prompts/` 構造、Memory retrieval 結果の組み込み方

   * `aidlc-docs/construction/unit-3-debate/functional-design/sequence-diagrams.md` — Mermaid sequence: 論破セッション開始（Mobile → AgentCore Runtime → Bedrock + Memory）/ ストリーミング配信 / 拒否ループ + Cooldown DDB 更新 / 90 秒タイムアウト（Runtime lifecycle）/ Amazon 遷移 → 肯定フィードバック / 個別最適化学習（Memory userPreference 自動抽出）

3. **`infra/lib/debate-stack.ts`** **の Code Generation 計画（v3.3 で C2-1 / C2-2 修正反映）**

   * Unit-1 platform-stack の SSM 参照（`userpool-id` / `userpool-client-id` / `kms-key-arn` / `alerts-topic-arn` / `auditlogger-layer-arn`）

   * `agentcore.Runtime`（Python 3.13 + Strands、Direct Code Deploy + `lifecycleConfiguration: { idleTimeoutSeconds: 120, maxLifetimeSeconds: 120 }` + **Strands Agent 内 graceful shutdown 80s フック**、v3.2 Q11）+ **dev / staging / prd の各 Stack 内 `live` + `canary` の 2 RuntimeEndpoint**（v3.3 M-5、Q17 = B + qualifier 統一）

   * `agentcore.Memory`（**`expirationDuration: 90 日` 単一値**、events + strategy records 共通の生存期間、v3.3 C-2）+ userPreference + semantic + **custom Strategy `m1_m2_axis_extractor`**（v3.2 Q1=C / Q16=B）+ **`streamDeliveryResources` で S3 並行書き出し**（v3.2 Q13）

   * S3 bucket（`yudane-debate-<env>-memory-export`、Lifecycle Standard → IA → Glacier → 365d delete、KMS 暗号化、Athena/Glue 連携）

   * DDB `yudane-debate-<env>-cooldowns`（Q2 唯一の自前テーブル）

   * Bedrock InvokeModelWithResponseStream 権限自動付与（v3.3 M-4 = **Haiku 4.5 + Sonnet 4.6 の 2 ARN ワイルドカード**で先行付与、Q4 SSM 切替時の AccessDenied を防止）

   * **多層 Bedrock Guardrails**（streaming 対応版、v3.2 Q12 = D）

   * **SSM `/yudane/<env>/debate/model-id` Parameter**（既定 `anthropic.claude-haiku-4-5`、v3.2 Q4 = A + SSM 切替、v3.3 で P0 化）

   * Output SSM（**`/yudane/<env>/debate/{runtime-arn, memory-id, runtime-endpoint-live-arn, runtime-endpoint-canary-arn, model-id, memory-export-bucket-arn, cooldowns-table-arn, kill-switch}`**、v3.3 C-5 + NC2-2 修正で 8 個に拡張、§1.4 と整合）

   * cdk-nag AwsSolutionsChecks 適用

4. **`shared/schema/paths/debate.yaml`** **の処理**

   * **削除候補**: AgentCore Runtime 直接呼び出しのため OpenAPI 不要

   * **残置案**: Mobile からの呼び出し仕様を `shared/agentcore-contracts/debate.ts` 等に定義（TypeScript 型）

   * Part 2 で確定

5. **Unit-2 / Unit-7 / Unit-1 / Unit-8 への申し送り PR 作成計画（v3.3 で更新）**

   * **Unit-2 への申し送り（v3 で消滅、v3.2 / v3.3 でも変更なし、v3.3 M-6 修正）**:

     * ~~Q8:~~ ~~`UserActivitySummary`~~ ~~テーブル新設~~ → **消滅**（AgentCore Memory semantic Strategy で代替）

     * ~~Q10: B-08 が~~ ~~`DebateOutcomes`~~ ~~を集約~~ → **消滅**（AgentCore Memory userPreference + custom Strategy で代替）

     * **v3.2 / v3.3 で再追加なし** — Unit-3 から Unit-2 への新規申し送り項目は発生しない

   * **Unit-7 への申し送り（v3.2 維持 + 拡充）**:

     * Q9 = D → `paths/safeguard.yaml` の `PATCH /v1/safeguard` リクエストボディに `cooldownReleased` / `releaseReason` を追加

     * 監査ログ（解除理由）の B-12 経由ログ出力の責務

     * **追加（v3）**: アカウント削除（FR-AUTH-06）バッチに `bedrock-agentcore.delete_event` / `delete_memory_record` 経由のユーザーデータ削除を追加（Q13 の整合性）

     * **追加（v3.2）**: Memory `streamDeliveryResources` の S3 export データもアカウント削除時に対象化（S3 prefix `/<actorId>/` の prefix 削除バッチ）

   * **Unit-8 への申し送り（v3.2 新設）**:

     * **追加（v3.2 Q13）**: Year 1 退化レポート（UC-06 / UC-07）のデータソースとして `s3://yudane-debate-<env>-memory-export/<actorId>/...` の Athena クエリ経路を組み込む

     * Glue Crawler スケジュール（日次）/ Athena view 定義（`debate_outcomes_v1`）/ Unit-8 が参照する dataset 一覧をドキュメント化

   * **Unit-1 への申し送り（v3.2 で軽微な追加）**:

     * **追加（v3）**: `userpool-client-id` の SSM Parameter（`/yudane/<env>/platform/userpool-client-id`）が main の platform-stack.ts に既出力済みかを確認（既出力: 確認済み）。出力済みなら追加不要

     * **追加（v3）**: `tech-cdk.md §4` に「**§4.2 AgentCore Runtime / Memory の標準採用**」セクション追加（Unit-3 が初の採用、後続 Unit が再利用しやすくする）

     * **追加（v3.2）**: tech-cdk.md §4.2 に **`agentcore.Memory` の `streamDeliveryResources` 設定パターン**（S3 + Athena 連携）も標準採用パターンとして記載

     * **追加（v3.2）**: `doc/backlog.md` に backlog エントリ追記（B-303 は MVP 採用に格上げ済、新規 B-304/B-305/B-306/B-307 を追加。詳細は [task-breakdown.md §6 リスクと緩和策](./task-breakdown.md#6-リスクと緩和策) と [Decision Record §6.4](#64-backlog-追加項目v32-で確定) 参照）

6. **Mobile 実装計画（v3.3 で qualifier 命名統一）**

   * `mobile/src/features/debate/agentcore-client.ts` 新設（`@aws-sdk/client-bedrock-agentcore` ラッパー）

   * `mobile/src/features/debate/event-parser.ts` 新設（Strands streaming 標準形式 → UI イベント変換）

   * `mobile/src/features/debate/M-04-DebateScreen.tsx` 実装（Outside-In TDD）

   * **追加（v3.3 M-5 修正、4IDC-1 修正）**: env 分離は Stack 単位（`debate-dev-stack` / `debate-staging-stack` / `debate-prd-stack`）。各 Stack 内に `live` + `canary` の 2 RuntimeEndpoint を作成。SSM `/yudane/<env>/debate/runtime-endpoint-live-arn` / `runtime-endpoint-canary-arn` は **正本として出力**、Mobile は **EAS Build 時に Expo `app.config.js` 経由で SSM CLI から値を取得して `EXPO_PUBLIC_*` 環境変数として埋め込み**、ランタイムでは `process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` から参照。通常 `qualifier: 'live'`、決勝直前のカナリアリリース時は canary build（`EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_CANARY_ARN` 埋め込み）を OTA Update で配信。dev / prd の Stack で `live` qualifier を共通使用しても、Stack 単位で Runtime ARN が異なるため env 混線は発生しない

   * M-12 ApiClient は他 Unit 用に維持、Unit-3 では使わない

7. **Part 2 完了後の承認ゲート → NFR Requirements ステージへ移行**

***

## 4. ハッカソン書類審査・予選評価軸へのインパクト（v3.3 統合版）

| 評価軸                | v3.3 確定での貢献                                                                                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ビジネス意図の明確さ         | **強化**: M-1 + M-2 併走 / 肯定フィードバック発火 / 個別最適化学習を **AgentCore Memory userPreference + semantic + custom Strategy（M-1/M-2 軸特化）** で実装。M-3 到達証拠の保全（Q13 D + S3 export）で「Year 1 退化アーク」を **機能要件として実装可能**                       |
| Unit 分解の適切さ        | **大幅強化**: Unit-2 への申し送り 2 件消滅、Unit-3 が AgentCore で完全自己完結。Unit-1 main 正本との整合は SSM 経由で 95%+。task-breakdown.md の **P0 / P1 / P2 三段階優先度** で 4 名チームのリソース配分を最適化                                                            |
| 創造性とテーマ適合性         | **大幅強化（v3.3 の最大の利点）**: 「ダメ化メカニズムの個別最適化を AgentCore Memory の **custom Strategy（M-1/M-2 軸特化抽出）** で実装、論破ストリーミングを Runtime で完全マネージド配信、ダメ化を Strands Agent + **多層 Bedrock Guardrails（v3.2 Q12 D）+ 正規表現 3 層** で倫理担保、PBT 全面（Q14 A）で M-1 + M-2 併走を不変条件として保証」は AI-DLC プロセス工夫 + 創造性 + AWS 最新技術活用の三冠 |
| ドキュメント品質           | **強化**: v1 → v2 → v3 → v3.2 → v3.3 の 5 改訂を Decision Record として残す、L1 / L2 / L3 整理は他 Unit の参考になる。Critical 6 + Major 6 のセルフレビュー修正履歴も documented                                                                                                      |
| AI-DLC プロセス（予選評価軸） | **大幅強化**: Inception → Construction で AgentCore 採用判断 → リージョン可用性 + CDK 適性調査 → MVP / 通常運用 3 層整理 → 全採用 → セルフレビューの意思決定プロセスが **5 改訂で documented decision として** 評価員に対して説得力ある証跡 |
| 決勝デモ完成度            | **強化**: Year 1 退化レポート（M-3）が **データパイプラインで成立**、決勝時には Day 1 〜 Day 30 のリアルデータでデモ可能。staging endpoint カナリアリリース対応で決勝直前の安全なデプロイを実現                                                                                                              |

***

## 5. 改訂履歴

| 版          | 日付             | 変更概要                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1（初版）     | 2026-05-28     | develop 系の Q1〜Q10 前提で Q1〜Q15 を提示。Unit-1 develop 系の DebateRateLimits / SnapStart / VPC 外配置を前提                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| v2         | 2026-05-29     | main マージ後の Unit-1 main 正本に整合。Q5（API GW 確定済み前提化）/ Q6（VPC 内 + Lambda Streaming に変更、SnapStart は backlog B-202 で決勝前再評価）/ Q15（Prism 既存活用で簡素化）/ 申し送りテーブル名を Unit-1 命名規約に整合化                                                                                                                                                                                                                                                                                                                                                                                 |
| **v3（v3.0）** | **2026-05-29** | **AgentCore Runtime + Memory + Identity による全面マネージド化**。Tokyo apne1 で全機能 GA + `aws-cdk-lib/aws-bedrockagentcore` L2 安定確認後の意思決定。Q1（Memory STM + 組み込み Strategy）/ Q3（Strands streaming 標準）/ Q5（Cognito Authorizer）/ Q6（Public Network、VPC 不要）/ Q8（Memory semantic + ヒューリスティック）/ Q10（Memory userPreference）/ Q11（lifecycleConfiguration）/ Q13（Memory expirationDuration）/ Q15（`agentcore dev`）に書き直し。Q16（ストラテジー設計）/ Q17（RuntimeEndpoint 環境戦略）を新設。Unit-2 への申し送り 2 件削除、Unit-7 への申し送りに Memory データ削除を追加、Unit-1 への申し送りに tech-cdk.md §4.2 + backlog B-303/304 を追加 |
| **v3.2** | **2026-05-29** | **「機能面 L1 / アーキテクチャ面 L2 / 保守運用面 L3」の 3 層整理に基づく通常運用版全採用 = オプション C**。L1 機能面の穴（Q11 論破文中断 / Q13 Year 1 退化レポートのデータ消失）を MVP の段階で潰す。**変更: Q1 = B → C** / **Q4 = A → A + SSM 切替** / **Q10 = A → B** / **Q11 = A → A + Strands graceful shutdown 80s** / **Q12 = C → D** / **Q13 = D → D + Memory `streamDeliveryResources` + S3 export** / **Q14 = B → A（PBT 全面）** / **Q16 = A → B** / **Q17 = A → B**。追加工数 +4 日（5-6d → 9-10d）。実装タスク分解と P0 / P1 / P2 優先度付けは [task-breakdown.md](./task-breakdown.md) に切り出し |
| **v3.3** | **2026-05-29** | **v3.2 のセルフレビューで検出した Critical 6 件 + Major 6 件の矛盾を一括修正**。C-1（Q4 SSM の P0/P1 分類矛盾）/ C-2（Memory expirationDuration 7 日 vs 90 日混乱、単一値 90 日 + S3 export 365 日に正確化）/ C-3（5/30 マイルストーン矛盾、4 段階に整理）/ C-4（§1.4 Infra 層表 v3 のまま、v3.3 統合版に書き換え）/ C-5（出力 SSM 不整合、7 個に統一）/ C-6（task-breakdown DAG 論理矛盾）/ M-1（§4 評価軸 v3 のまま、§6.3 と重複）/ M-2（Q12 選択肢 D 再定義「多層防御」）/ M-3（Q1/Q10/Q16 段階実装方針を plan 本文に明示）/ M-4（IAM ハードコード問題、Haiku + Sonnet 2 ARN ワイルドカード化）/ M-5（RuntimeEndpoint qualifier 命名統一 `live`+`canary`）/ M-6（Unit-2 申し送り表記正確化）。設計判断自体に変更なし、ドキュメント整合性のみ向上 |
| **v3.4（本版）** | **2026-05-29** | **コピートーン局所オーバーライド + NFR Requirements / NC2 セルフレビュー反映**。Unit-3 のみ FR-DEBATE-08 友達系トーン → **論理優位ディベート系（敬語ベース、論理で黙らせるスタイル）** に再定義（要件書 FR-DEBATE-08 に Unit-3 オーバーライド注記追加）。「〜じゃないですか？」「結局〜」「論理的に考えて」「データあるんですか？」型を採用、M-1 効果最大化。Unit-4/5/6/7/8 は本則（友達系）維持。NFR Requirements の C2-2 fail-open + kill switch 追加で SSM 出力を 7 個 → 8 個に拡張（kill-switch 追加）。設計判断の本質は変更なし、トーン局所変更 + NFR 強化のみ |


***

## 6. Decision Record（v3.3 確定、2026-05-29）

オプション C（通常運用版全採用）採用後の Q1〜Q17 確定回答を一覧化。実装の優先度付け（P0 / P1 / P2）は [task-breakdown.md](./task-breakdown.md) を参照。**v3.3 でセルフレビュー修正後の最終版**。

### 6.1 Q1〜Q17 確定一覧（v3.3 修正反映）

| Q   | テーマ                        | 確定回答（v3.3） | v3 → v3.3 差分                  | L1 機能面影響 | 追加工数      | P0/P1 配分（v3.3） |
| --- | -------------------------- | ----------- | ----------------------------- | -------- | --------- | --------------- |
| Q1  | セッション状態管理                  | **C**       | B → C（MVP から custom Strategy）| 中        | +0.5d     | P0 = 組み込み 2 種 / P1 = custom 追加 |
| Q2  | 連続拒否カウンタ                   | **C**       | 変更なし                          | -        | -         | P0 のみ |
| Q3  | ストリーミング配信                  | **A**       | 変更なし                          | -        | -         | P0 のみ |
| Q4  | Bedrock モデル                | **A + SSM** | A → A + SSM 切替（v3.3 で P0 化）   | △ 間接     | +0.2d     | **P0**（v3.3 修正） |
| Q5  | クライアント認証                   | **A**       | 変更なし                          | -        | -         | P0 のみ |
| Q6  | Network Configuration      | **A**       | 変更なし                          | -        | -         | P0 のみ |
| Q7  | プロンプトテンプレート管理              | **A**       | 変更なし                          | -        | -         | P0 のみ |
| Q8  | ストレスレベル推定                  | **B**       | 変更なし                          | -        | -         | P0 のみ |
| Q9  | クールダウン解除                   | **D**       | 変更なし（Unit-7 申し送り維持）           | -        | -         | P0 のみ |
| Q10 | 個別最適化学習                    | **B**       | A → B（custom Strategy 連動）     | -        | +0.5d     | P0 = userPreference のみ / P1 = custom 連動 |
| Q11 | 90 秒タイマー                   | **A + GS**  | A → A + Strands graceful shutdown 80s | ◎ 直接 | +0.3d     | P0 = lifecycle のみ / P1 = graceful shutdown |
| Q12 | 出力モデレーション                  | **D**       | C → D（多層 Guardrails、v3.3 で D 再定義）| ○ 安全装置強化 | +0.5d  | P0 = プロンプト層 / P1 = Bedrock GR + 正規表現 |
| Q13 | 永続期間                       | **D + S3**  | D → D + S3（v3.3 で expirationDuration 単一値に正確化） | ◎ 直接 | +0.5d     | P0 = expirationDuration 90d / P1 = S3 export |
| Q14 | PBT 戦略                     | **A**       | B → A（PBT 全面）                 | ○ 品質向上   | +1〜2d     | P0 = 重点 5 関数 / P1 = 統合点 5 + Coverage 85% |
| Q15 | Mock 戦略                    | **A**       | 変更なし                          | -        | -         | P0 のみ |
| Q16 | Memory ストラテジー設計            | **B**       | A → B（custom Strategy 採用）     | ○ 創造性軸   | +0.5d     | P0 = 組み込み 2 種 / P1 = custom 追加 |
| Q17 | RuntimeEndpoint 環境戦略       | **B**       | A → B（live + canary、v3.3 で qualifier 命名統一）| ○ カナリア可 | +0.5d | P0 = live のみ / P1 = canary 追加 |

**追加工数合計**: +4.0〜5.0d（v3 の 5〜6d → v3.3 の 9〜11d）。

**P0 / P1 工数配分**: P0 = 6.2d（v3.2 の 6.0d + Q4 SSM 0.2d を P0 化）/ P1 = 4.6d（v3.2 の 4.8d − Q4 SSM 0.2d を P0 移動）/ 合計は変わらず 10.8d

### 6.2 L1 機能面の穴を塞いだ修正の詳細

| 修正 ID | 内容                                | M-1/M-2/M-3 への影響                                    | UC への影響                |
| ----- | --------------------------------- | -------------------------------------------------- | ---------------------- |
| Q11   | Strands graceful shutdown 80s     | M-1 体験の品質保証（論破文の途中切断防止）                          | UC-01 論破チャットの完成度        |
| Q13   | Memory streamDeliveryResources + S3 | **M-3 到達証拠の保全**（90 日 → 365 日のデータパイプライン）           | UC-06 逆家計簿 / UC-07 ダメ化ポートフォリオ |
| Q12   | Bedrock Guardrails + 多層検査         | NG-6 脅迫・罪悪感強要への滑落防止（M-2 を倫理ラインに留める安全装置）           | UC-01 全般               |
| Q14   | PBT 全面                            | プロンプト合成の不変条件保証（M-1 + M-2 併走の必ず両軸を含む property） | UC-01 品質ゲート            |

### 6.3 v3.2 → v3.3 で実施したセルフレビュー修正サマリ

評価軸への影響は §4 を参照。本セクションは **v3.2 → v3.3 で何を直したか** のレビュー記録に特化。

| 区分 | ID | 内容 | 修正範囲 |
|---|---|---|---|
| Critical | C-1 | Q4 SSM 切替の P0/P1 分類矛盾を解消 | Q4 答え + Decision Record §6.1 + task-breakdown §2 / §3 |
| Critical | C-2 | Memory `expirationDuration` の 7 日 vs 90 日混乱を解消、単一値 90 日 + S3 export 365 日に統一 | §1.4 / §1.5 / Q13 / Decision Record |
| Critical | C-3 | 5/30 マイルストーン矛盾を解消、暫定デモ 5/30 → P0 完了 6/6 → 決勝 Readiness 6/15 → 決勝デモ 6/26 の 4 段階に整理 | task-breakdown §1 マイルストーン表 |
| Critical | C-4 | §1.4 Infra 層表が v3 のままだったのを v3.3 に統合更新（Strands GS / S3 export / live+canary / model-id SSM / IAM ワイルドカード） | §1.4 |
| Critical | C-5 | 出力 SSM の不整合を解消、§1.4 / §3 #3 / Q17 で 7 個に統一 | §1.4 / §3 #3 / Q17 |
| Critical | C-6 | task-breakdown §5 依存 DAG の論理矛盾を解消（P1 タスクは P1_Done より前） | task-breakdown §5 |
| Major | M-1 | §4 評価軸が v3 のまま + §6.3 重複の解消、§4 を v3.3 統合版に書き換え、§6.3 をレビュー記録に簡略化 | §4 / §6.3 |
| Major | M-2 | Q12 選択肢 D を「プロンプト + 正規表現」から「**多層防御**: プロンプト + Bedrock GR + 正規表現」に再定義、回答との整合化 | Q12 |
| Major | M-3 | Q1 / Q10 / Q16 の段階実装方針（P0 = 組み込み Strategy / P1 = custom 追加）を plan 本文に明示 | Q1 / Q10 / Q16 |
| Major | M-4 | §1.4 IAM ハードコード問題を解消、Haiku 4.5 + Sonnet 4.6 の 2 ARN ワイルドカード化（Q4 SSM 切替時の AccessDenied 防止） | §1.4 / Q4 |
| Major | M-5 | RuntimeEndpoint qualifier 命名規則を `live` + `canary` に統一、Stack 単位 env 分離 + 各 Stack 内 2 endpoint の設計を明確化 | §1.4 / §3 #6 / Q17 |
| Major | M-6 | Unit-2 申し送りの表記を「v3 で大幅縮小」→「v3 で消滅、v3.2 / v3.3 でも変更なし」に正確化 | §3 #5 |

### 6.4 Backlog 追加項目（v3.2 で確定）

[doc/backlog.md](../../../../doc/backlog.md) に以下を追記する（task-breakdown.md の P2 と整合）:

| ID    | 項目名                              | 出典       | 後付けトリガー                       | 優先度 |
| ----- | -------------------------------- | -------- | ----------------------------- | --- |
| B-303 | AgentCore Memory custom Strategy | v3 Q16 → v3.2 で MVP 採用に格上げ | （v3.2 で MVP 採用済、backlog から削除予定） | -   |
| B-304 | AgentCore Online Evaluation       | v3 Q16   | 決勝後の運用評価                      | 中   |
| B-305 | Sonnet 4.6 切替（プロンプト合成側）          | v3.2 Q4  | 決勝後にユーザー数 1000 超 + Haiku 制約検出 | 中   |
| B-306 | Memory custom Strategy のプロンプト改善版  | v3.2 Q16 | 決勝後の論破成功率分析                  | 中   |
| B-307 | RuntimeEndpoint Auto-Pause 設定    | v3.2 Q17 | dev/staging endpoint 月額 $X 超え | 低   |
