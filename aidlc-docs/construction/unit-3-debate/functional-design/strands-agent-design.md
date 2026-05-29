# Unit-3 Debate — Strands Agent Design

> AgentCore Runtime にホストされる Strands Agent の構造・hooks・モデル設定・タイマー実装を確定。
>
> 参照: [business-logic-model.md](./business-logic-model.md) / [business-rules.md](./business-rules.md) / [domain-entities.md](./domain-entities.md) / [prompt-composition.md](./prompt-composition.md)
>
> 確定方針: Q1=C / Q4=A+SSM / Q5=A / Q6=A / Q7=A / Q11=A+graceful shutdown 80s / Q12=D 多層 / Q15=A `agentcore dev` / Q16=B / Q17=B live+canary

## Overview

Unit-3 Debate の Backend は AgentCore Runtime にデプロイされる Strands Agent として実装される。本書は Strands Agent の構造（モジュール分割 / hooks / model / callback_handler）、AgentCore Runtime ライフサイクル、タイマー二段構造、ローカル開発手順を確定する。設計判断は v3.3 Decision Record に基づく。

## Architecture

論破ロジックは AgentCore Runtime（マネージドコンテナ）+ AgentCore Memory（自動抽出ストラテジー）+ Bedrock Haiku 4.5（ストリーミング）+ Bedrock Guardrails（出力モデレーション）の 4 サービス連携で実現。Mobile から `InvokeAgentRuntime` で直接呼び出し、API Gateway / 自前 Lambda は経由しない。

## Components and Interfaces

```
backend/src/debate/
├── main.py                       # BedrockAgentCoreApp + @app.entrypoint
├── prompts/
│   ├── __init__.py
│   ├── base.py                   # System block + NG-1〜8 ガードレール指示
│   ├── m1_fact_axis.py           # 事実軸テンプレート（時給換算 / 在庫希少性 / 予定整合）
│   ├── m1_psychology_axis.py     # 心理軸テンプレート（個別最適化、preferred_axis 反映）
│   ├── m2_reward_axis.py         # ストレス × ご褒美軸（FR-DEBATE-09、stress_level=mid/high で発火）
│   ├── affirmation.py            # 肯定フィードバック生成
│   └── compose.py                # ALG-PROMPT 公開関数
├── memory_hooks.py               # Strands hooks（on_session_start / on_turn_complete）
├── stress.py                     # ALG-STRESS（estimate_stress_level）
├── cooldown.py                   # ALG-COOLDOWN-CHECK / ALG-COOLDOWN-INC（DDB 操作）
├── moderation/
│   ├── __init__.py
│   ├── ng_patterns.py            # NG-6 正規表現パターン
│   └── callback_handler.py       # Strands callback_handler、第 3 層モデレーション
├── domain/
│   ├── __init__.py
│   ├── payloads.py               # DebateInvocationPayload 等の Pydantic v2
│   ├── memory_metadata.py        # AgentCoreMemoryEventMetadata
│   └── results.py                # CooldownDecision / ComposedPrompt 等
├── ssm.py                        # SSM model_id 取得（Q4=A+SSM）
└── requirements.txt              # bedrock-agentcore + strands-agents + boto3
```

---

## Data Models

ドメインエンティティ・DTO の詳細は [domain-entities.md](./domain-entities.md) を参照。本書では Strands Agent 内で使う runtime models と Memory metadata の構造のみ抜粋する。

| データ | 所在 | 永続化 |
|---|---|---|
| `DebateInvocationPayload` | `domain/payloads.py` | — |
| `AgentCoreMemoryEventMetadata` | `domain/memory_metadata.py` | AgentCore Memory |
| `CooldownState` | `domain/results.py` | DDB Cooldowns |
| `ComposedPrompt` | `domain/results.py` | — |
| `MemoryContext` | `domain/results.py` | — |

## Correctness Properties

PBT-03 / PBT-07 / PBT-08 の重点 property は [prompt-composition.md §9](./prompt-composition.md#9-テスト戦略pbt-重点) と [business-logic-model.md アルゴリズム一覧](./business-logic-model.md#アルゴリズム一覧と検証方針サマリ) を参照。

### Property 1: M-2 reward axis 必須含有（PBT-03）

**Validates: Requirements 5.1**

`stress_level in {'mid', 'high'}` のとき `compose_debate_prompt(...)` の出力 `composed.text` に必ず `[REWARD]` セクションマーカーが含まれる（FR-DEBATE-09 不変条件）。

### Property 2: stress_level 戻り値の集合性（PBT-07）

**Validates: Requirements 5.1**

`estimate_stress_level(actor_id, now, signals)` の戻り値は任意の入力に対し必ず `'low' | 'mid' | 'high'` のいずれか。Memory retrieve が失敗・空でも例外を上げず既定のスコア計算で動作する。

### Property 3: Cooldown 3 回到達トリガー（PBT-03）

**Validates: Requirements 5.1**

`increment_refuse_count(actor_id, now)` が `consecutiveRefuses == 3` に達した瞬間に必ず `cooldownUntil = now + 3h` が DDB に SET される（DDB 属性は camelCase、Python 戻り値は snake_case で alias 変換、v3.3 C3-2）。同一 `actor_id` で 4 回目以降の呼び出しでも `cooldownUntil` は更新されない（active 中は新規セッションが Bedrock に到達しない）。自然解除（`cooldownUntil <= now`）後の最初の拒否では `consecutiveRefuses` を 1 にリセット（v3.3 M3-1）。

### Property 4: Memory event round-trip（PBT-02）

**Validates: Requirements 5.1**

`memory_client.create_event(actor_id, session_id, messages, metadata)` 直後に同一 `session_id` で `get_last_k_turns(k=N)` を呼ぶと、保存した `messages` が最新 N 件以内に含まれる。`metadata` の serialize → deserialize で同一値（PII 含まない構造のため非可逆性を持たない）。

### Property 5: AgentCore Payload round-trip（PBT-02）

**Validates: Requirements 5.1**

Mobile 側 `agentcore-client.ts` が `InvokeAgentRuntimeCommand.payload` に詰める JSON を Strands Agent 内で `DebateInvocationPayload` として deserialize した結果が、Mobile 側のオリジナル値と一致する（型不変条件）。

## Error Handling

エラー区分 / DomainError 体系は Unit-1 main 由来の [common/exceptions/domain_error.py](../../unit-1-platform/code/) を再利用。AgentCore Runtime 直接呼び出しのため API Gateway 経由のエラー変換は不要、Strands Agent 内で error event を yield する形で Mobile に伝達する（[domain-entities.md §3.1 EventType](./domain-entities.md#31-strandsstreameventstrands-agent-の標準-streaming-形式q3a)）。

## Testing Strategy

- ユニット: Strands Agent モジュール単位（`stress.py` / `cooldown.py` / `prompts/compose.py`）にクラシック TDD
- 統合: `agentcore dev` で dev 環境 Bedrock + dev Memory に対して E2E
- PBT: Hypothesis（Python）+ fast-check（TypeScript）で重点 5 関数 + 統合点 5（[functional-design-plan.md Q14](./functional-design-plan.md)）
- カバレッジ目標: Line 80%+ / Branch 70%+（Coverage 85% を Unit-3 では目標）

---

## 1. main.py の実装方針（Q3 / Q5 / Q11 / Q12 / Q15 反映、v3.3 C3-1 / C3-3 修正）

> ファイル構造は §Components and Interfaces 参照。本セクションでは entrypoint `debate_handler` の実装方針を確定する。`action` フィールドで「論破セッション開始」と「肯定フィードバック生成」の 2 系統を分岐させる（domain-entities §2.1 / business-logic-model ALG-DEBATE-START、v3.3 C3-3 修正）。

```python
"""Unit-3 Debate AgentCore Runtime entrypoint."""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from typing import AsyncIterator

from .domain.payloads import DebateInvocationPayload, parse_jwt_actor_id
from .memory_hooks import DebateMemoryHook
from .moderation.callback_handler import build_callback_handler
from .stress import estimate_stress_level
from .cooldown import check_cooldown, increment_refuse_count
from .prompts.compose import compose_debate_prompt
from .prompts.affirmation import generate_affirmation
from .ssm import get_model_id

app = BedrockAgentCoreApp()

# 起動時 1 回だけ SSM から model_id 取得（v3.2 Q4=A+SSM、v3.3 P0 化）
MODEL_ID = get_model_id(env_name=os.environ['ENV_NAME'])

agent = Agent(
    model=MODEL_ID,
    hooks=[DebateMemoryHook()],
    callback_handler=build_callback_handler(),  # Q12 第 3 層モデレーション
    bedrock_kwargs={
        "guardrailIdentifier": GUARDRAIL_ID,    # Q12 第 2 層
        "guardrailVersion": "DRAFT",
    },
)


@app.entrypoint
async def debate_handler(payload: dict, context) -> AsyncIterator[dict]:
    # 1. 認証コンテキスト解決（Q5 Cognito Authorizer）
    actor_id = parse_jwt_actor_id(context)
    if not actor_id:
        yield {"type": "error", "metadata": {"reason": "auth.unauthenticated"}}
        return

    # 2. payload 検証
    invocation = DebateInvocationPayload.model_validate(payload)

    # 3. action 分岐（v3.3 C3-3 修正）
    if invocation.action == 'request_affirmation':
        affirmation = await generate_affirmation(
            actor_id=actor_id,
            asin=invocation.asin,
            client_signals=invocation.client_signals,
            outcome=invocation.outcome,
        )
        if affirmation:
            yield {
                "type": "debate.affirmation_shown",
                "metadata": {"text": affirmation.text, "style": affirmation.style},
            }
        return

    # === 以下、action='start_session' の通常フロー ===

    # 4. クールダウン判定
    cd = check_cooldown(actor_id, now=utcnow())
    if cd.active:
        yield {
            "type": "debate.cooldown_triggered",
            "metadata": {"cooldown_until": cd.cooldown_until.isoformat()},
        }
        return

    # 5. ストレスレベル推定
    stress_level = estimate_stress_level(actor_id, utcnow(), invocation.client_signals)

    # 6. プロンプト合成（Memory retrieve は MemoryHook が自動実行）
    composed = compose_debate_prompt(
        user_input=invocation.user_input,
        asin=invocation.asin,
        stress_level=stress_level,
        memory_context=await build_memory_context_via_hook(actor_id),
    )

    # 7. Strands streaming + graceful shutdown 80s（v3.2 Q11、L1 機能面修正）
    started_at = utcnow()
    async for event in agent.stream_async(composed.text):
        elapsed = (utcnow() - started_at).total_seconds()

        if elapsed >= DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS:
            yield {"type": "graceful_shutdown_initiated", "metadata": {"elapsed": elapsed}}
            summary = await agent.invoke_async(
                "ここまでの論破サマリを 1〜2 文で生成。トーンは論理優位ディベート系（敬語、〜じゃないですか / 結局 / 論理的に / データあるんですか？）、未確定の論破軸を含めない",
                timeout_sec=DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS,
            )
            yield {"type": "summary", "metadata": {"summary_text": summary}}
            yield {"type": "session_complete", "metadata": {"reason": "graceful_timeout"}}
            return

        yield event   # Strands 標準 streaming chunk をそのまま転送（Q3=A）

    # 8. 終了処理（outcome は MemoryHook on_turn_complete で記録済み）
    yield {"type": "session_complete", "metadata": {"reason": "agent_completed"}}
```

### 設計判断（Q3 / Q11 / Q12）

- **Q3=A**: Strands streaming chunk をそのまま `yield`、独自 4 種イベントへの変換は行わない。Mobile 側 `event-parser.ts` で軸判別・UI 反映
- **Q11 + Strands graceful shutdown 80s**: 80s 経過時にサマリ生成 + 綺麗な session_complete を yield。論破文の途中切断（M-1 体験を阻害する重大不具合）を防止
- **Q12 多層**: 第 1 層 = `composed.text` 内の NG-1〜8 ディレクティブ / 第 2 層 = Bedrock Guardrails の `guardrailIdentifier` / 第 3 層 = `callback_handler` の正規表現検査
- **action 分岐（v3.3 C3-3 修正）**: 1 つの entrypoint で「論破セッション開始」と「肯定フィードバック生成」を扱う。Mobile が翻意後に `action='request_affirmation'` で 2 回目の呼び出しを行う

---

## 2. Strands Agent 設定（Q1 / Q4 / Q12 / Q16 反映）

### 2.1 model（Q4=A+SSM、v3.3 P0 化）

```python
# ssm.py
import boto3

ssm_client = boto3.client('ssm')

def get_model_id(env_name: str) -> str:
    """Lambda 起動時 1 回だけ SSM から model_id を取得。"""
    response = ssm_client.get_parameter(
        Name=f"/yudane/{env_name}/debate/model-id",
        WithDecryption=False,
    )
    return response['Parameter']['Value']
```

- 既定値: `anthropic.claude-haiku-4-5`
- 切替: SSM 値変更 + Lambda 再起動で反映（Stack 再デプロイ不要）
- IAM: Haiku 4.5 + Sonnet 4.6 の 2 ARN ワイルドカード（v3.3 M-4、Sonnet 切替時の AccessDenied 防止）

### 2.2 hooks（Q1 / Q10 / Q16 反映）

```python
# memory_hooks.py
from strands.hooks import StrandsHook
from bedrock_agentcore.memory import MemoryClient

class DebateMemoryHook(StrandsHook):
    """Strands hooks で AgentCore Memory との連携を自動化。"""

    def __init__(self):
        self.memory_client = MemoryClient(memory_id=DEBATE_MEMORY_ID)

    async def on_session_start(self, session_state):
        """セッション開始時に MemoryContext を構築して system_prompt に注入。"""
        actor_id = session_state.actor_id
        context = build_memory_context(self.memory_client, actor_id)
        session_state.system_prompt_addendum = render_memory_block(context)

    async def on_turn_complete(self, turn):
        """ターン完了時に Memory に書き込み。"""
        self.memory_client.create_event(
            actor_id=turn.actor_id,
            session_id=turn.session_id,
            messages=[(turn.user_input, "USER"),
                      (turn.assistant_output, "ASSISTANT")],
            event_metadata={
                "axis": turn.detected_axis,
                "outcome": turn.outcome,
                "turn": turn.turn_number,
                "stress_level": turn.stress_level,
                "asin": turn.asin,
            },
        )
```

### 2.3 Memory Strategy 構成（Q1=C / Q10=B / Q16=B、段階実装）

| Phase | Strategy 構成 | namespace |
|---|---|---|
| **P0** | `userPreferenceMemoryStrategy(name="debate_outcomes")` + `semanticMemoryStrategy(name="stress_signals")` | `/user/debate/{actorId}/` + `/user/stress/{actorId}/` |
| **P1** | + `customMemoryStrategy(name="m1_m2_axis_extractor")` | + `/user/m1m2/{actorId}/` |

custom Strategy のカスタム抽出プロンプトは `prompts/m1_m2_axis_extractor.py`（P1 で新設）に配置:

```python
# prompts/m1_m2_axis_extractor.py（P1 で新設）
M1_M2_EXTRACTION_PROMPT = """
あなたは購買心理学の分析者です。以下の論破セッションのターン履歴から、
ユーザーが翻意した「軸」を構造化して抽出してください。

軸の定義:
- fact: 時給換算 / 在庫希少性 / 予定整合 等の論理的説得（M-1 判断力の弱体化）
- psychology: 自己甘やかしの内面化 / 過去の購買パターン肯定（M-1 判断力の弱体化）
- reward: ストレス解消 / ご褒美 / 即時快楽（M-2 購買快楽のストレス解消剤化）

入力: {messages}

出力 JSON:
{
  "axis": "fact" | "psychology" | "reward",
  "outcome": "agreed" | "refused" | "ongoing",
  "trigger_phrase": string,        # 翻意のキーワード
  "stress_level_at_turn": "low" | "mid" | "high",
  "confidence": float              # 0.0〜1.0
}
"""
```

### 2.4 callback_handler（Q12 第 3 層モデレーション）

```python
# moderation/callback_handler.py
import re
from .ng_patterns import NG6_PATTERNS

def build_callback_handler():
    def callback(event):
        if event.type == "token" and event.delta_text:
            for pattern in NG6_PATTERNS:
                if re.search(pattern, event.delta_text):
                    return {
                        "type": "moderation_blocked",
                        "metadata": {
                            "pattern_detected": pattern.pattern,
                            "reason": "ng6_threat_or_guilt"
                        }
                    }
        return event  # passthrough
    return callback
```

### 2.5 bedrock_kwargs（Q12 第 2 層 Bedrock Guardrails）

CDK で作成した Guardrails ID を環境変数経由で受け取り、Strands Agent の Bedrock 呼び出しに関連付ける。

```python
GUARDRAIL_ID = os.environ['BEDROCK_GUARDRAIL_ID']  # CDK output via SSM

agent = Agent(
    model=MODEL_ID,
    bedrock_kwargs={
        "guardrailIdentifier": GUARDRAIL_ID,
        "guardrailVersion": "DRAFT",
    },
)
```

Guardrails の DENIED_TOPICS は CDK で定義（business-rules MOD-03 と整合）:
- NG-1: 違法行為の助長
- NG-2: 健康被害の助長
- NG-3: 差別表現
- NG-4: 未成年への購買誘導
- NG-5: 精神衛生悪化（自殺・うつ等）
- NG-6: 脅迫・罪悪感強要
- NG-7: 個人データ悪用
- NG-8: Associates Operating Agreement 違反

---

## 3. タイマー実装（Q11=A + graceful shutdown 80s、二段構造）

### 3.1 サーバー権威タイマー（AgentCore Runtime lifecycleConfiguration）

CDK 設定:

```typescript
// infra/lib/debate-stack.ts
const debateRuntime = new agentcore.Runtime(this, 'DebateRuntime', {
  // ...
  lifecycleConfiguration: {
    idleTimeoutSeconds: 120,    // 論破は連続会話なので idle = 90s + バッファ 30s
    maxLifetimeSeconds: 120,    // 強制終了も 120s
  },
});
```

- 120s で AgentCore Runtime microVM が **強制停止**
- Mobile はそれ以降の `InvokeAgentRuntime` を 410 Gone で受け取る

### 3.2 アプリケーションタイマー（Strands Agent 内）

```python
DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS = 80
DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS = 10
DEBATE_MAX_DURATION_SECONDS = 90

async for event in agent.stream_async(composed.text):
    elapsed = (utcnow() - started_at).total_seconds()

    if elapsed >= DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS:
        # 80s 経過 → graceful shutdown 開始
        yield event_with_marker('graceful_shutdown_initiated', elapsed=elapsed)

        # 80〜90s でサマリ生成
        summary = await agent.invoke_async(
            "ここまでの論破サマリを 1〜2 文で生成。トーンは論理優位ディベート系（敬語、〜じゃないですか / 結局 / 論理的に / データあるんですか？）、未確定の論破軸を含めない",
            timeout_sec=DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS,
        )
        yield event_with_marker('summary', text=summary)
        yield event_with_marker('session_complete', reason='graceful_timeout')
        return

    if elapsed >= DEBATE_MAX_DURATION_SECONDS:
        # 90s 厳守: graceful shutdown が間に合わなかった保険
        yield event_with_marker('session_complete', reason='hard_timeout')
        return

    yield event
```

### 3.3 タイマー対応マトリクス

| 経過時間 | 状態 | 動作 |
|---|---|---|
| 0〜80s | normal | Strands streaming chunk 通常配信 |
| 80〜90s | graceful shutdown | サマリ生成 + 綺麗な session_complete |
| 90〜120s | hard cutoff | サマリ生成失敗時の保険、即 session_complete |
| 120s〜 | microVM 強制停止 | サーバー権威、Mobile は 410 Gone を受信 |

### 3.4 Mobile 側 endsAt 計算

```typescript
// mobile/src/features/debate/use-debate-session.ts
const endsAt = sessionStartedAt + 90_000;  // ms 単位
const remainingMs = Math.max(0, endsAt - Date.now());
// UI に「残り N 秒」を表示
```

NTP 同期前提だが、サーバー権威タイマー（120s）が最終 fail-safe。

---

## 4. AgentCore Runtime 起動方法（Q15=A + Direct Code Deploy）

### 4.1 ローカル開発（`agentcore dev`）

```bash
# backend/src/debate/ で起動
cd backend/src/debate
agentcore dev --port 8080

# 別ターミナルから疎通確認
agentcore invoke --dev --agent-runtime-arn DEV_ARN \
  --payload '{"user_input":"でも欲しいんだよなあ","asin":"B01ABC1234","trigger":"reel_skip"}'
```

- `agentcore dev` は uvicorn ベースの hot reload 開発サーバー
- Bedrock 呼び出しは local AWS credential 経由で dev リージョン（apne1）へ
- Memory も dev 環境の AgentCore Memory リソースに直接保存（local mock 不要）
- Bedrock dev 課金は Haiku 4.5 で 1 セッション $0.001 程度、$10/日上限を Cost Anomaly Detection で監視（Unit-1 既存）

### 4.2 dev / staging / prd へのデプロイ（Direct Code Deploy）

CDK の `agentcore.Runtime` リソースが S3 zip + ECR 不要の Direct Code Deploy で `backend/src/debate/` を配備:

```typescript
const debateRuntime = new agentcore.Runtime(this, 'DebateRuntime', {
  runtimeName: `yudane-debate-${envName}`,
  artifact: agentcore.RuntimeArtifact.fromAsset(
    path.join(__dirname, '../../backend/src/debate'),
    {
      bundling: { /* requirements.txt インストール */ },
    },
  ),
  authorizerConfiguration: agentcore.RuntimeAuthorizerConfiguration.cognito({
    userPoolId,
    clientIds: [userPoolClientId],
  }),
  networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),
  lifecycleConfiguration: {
    idleTimeoutSeconds: 120,
    maxLifetimeSeconds: 120,
  },
});
```

詳細な CDK 設定は infrastructure-design ステージで確定。

---

## 5. パフォーマンス・コスト設計（NFR Requirements で詳細確定）

| 項目 | 値 | 出典 |
|---|---|---|
| 初回トークン到達 | <= 300ms 目標 | FR-DEBATE-03 |
| 1 セッション平均ターン数 | 5〜8 | requirements.md ユーザー観察 |
| 1 セッション平均トークン消費 | input 2000 + output 800 = 約 2800 tokens | プロンプト設計から推定 |
| 1 セッション平均コスト（Haiku 4.5）| 約 $0.001 | Bedrock 価格表 |
| dev 月額予算 | $10/日 = 約 $300/月 | Cost Anomaly Detection（Unit-1） |
| prd 月額予算（10K DAU 想定）| 約 $3,000/月 | NFR Requirements で確定 |

---

## 6. 設計判断サマリ

| Q | 判断 | strands-agent-design.md での反映 |
|---|---|---|
| Q3 | Strands streaming 標準形式そのまま転送 | §1 main.py で `yield event` 直接、独自変換なし |
| Q4 | A + SSM 切替（P0 化）| §2.1 ssm.py で起動時 SSM 取得、Sonnet 4.6 切替時の IAM 先行付与 |
| Q5 | Cognito Authorizer | §4.2 CDK 設定で `agentcore.RuntimeAuthorizerConfiguration.cognito()` |
| Q7 | プロンプトを `prompts/` 配下で構造化 | §Components and Interfaces のファイル構造、§2.3 で 6 モジュール（base / m1_fact / m1_psychology / m2_reward / affirmation / compose）|
| Q11 | A + Strands graceful shutdown 80s | §3 タイマー二段構造、80s でサマリ生成 + 綺麗な session_complete |
| Q12 | D 多層モデレーション | §2.4 callback_handler 第 3 層 / §2.5 Guardrails 第 2 層 / §1 prompts/base.py 第 1 層 |
| Q15 | `agentcore dev` ローカル開発 | §4.1 ローカル疎通確認手順 |
| Q16 | custom Strategy `m1_m2_axis_extractor` | §2.3 P1 段階実装、抽出プロンプト設計 |
| Q17 | live + canary 2 endpoint | §4.2 CDK で 2 endpoint 作成、Mobile は qualifier 切替 |
| **action 分岐**（v3.3 C3-3） | 1 entrypoint で論破 + 肯定フィードバック | §1 main.py で `if invocation.action == 'request_affirmation'` 分岐 |
