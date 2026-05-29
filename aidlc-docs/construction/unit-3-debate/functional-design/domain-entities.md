# Unit-3 Debate — Domain Entities

> Unit-3 Debate のドメインエンティティ・DTO・型定義を **Pydantic v2（Python）+ TypeScript** の両言語で定義。
>
> 参照: [business-logic-model.md](./business-logic-model.md) / [business-rules.md](./business-rules.md) / [strands-agent-design.md](./strands-agent-design.md)
>
> 永続化方針: AgentCore Memory（Q1=C / Q10=B / Q16=B）+ DDB Cooldowns 唯一（Q2=C）+ S3 Memory Export（Q13 P1）

---

## 1. エンティティ概要図（Mermaid クラス図）

```mermaid
classDiagram
    class DebateInvocationPayload {
        +string user_input
        +string asin
        +DebateTrigger trigger
        +string? client_session_id
    }

    class DebateSession {
        <<dataclass, no persistence>>
        +string session_id
        +string actor_id
        +string asin
        +DateTime started_at
        +DateTime ends_at
        +StressLevel stress_level
        +int turn_count
        +DebateOutcome outcome
    }

    class CooldownState {
        <<DDB Cooldowns table, camelCase>>
        +string PK "USER#{actor_id}"
        +string SK "COOLDOWN#current"
        +int consecutiveRefuses
        +DateTime lastRefuseAt
        +DateTime? cooldownUntil
        +int ttl
    }

    class CooldownDecision {
        <<value object>>
        +bool active
        +DateTime? cooldown_until
        +int consecutive_refuses
    }

    class StressSignals {
        <<dataclass, no persistence>>
        +ClientSignals client_signals
        +list~string~ memory_signals
        +int score
    }

    class MemoryContext {
        <<dataclass, no persistence>>
        +list~OutcomeRecord~ recent_debate_outcomes
        +DebateAxis preferred_axis
        +list~string~ stress_signals
        +list~string~ m1m2_axis_extracted
        +int? hourly_wage_yen
        +CalendarContext calendar_context
        +AffirmationStyle preferred_affirmation_style
    }

    class ComposedPrompt {
        <<value object>>
        +string text
        +list~DebateAxis~ axes
    }

    class StrandsStreamEvent {
        +EventType type
        +string? delta_text
        +dict? metadata
    }

    class AffirmationMessage {
        +string text
        +AffirmationStyle style
    }

    class AgentCoreMemoryEventMetadata {
        <<persisted in Memory>>
        +DebateAxis axis
        +DebateOutcome outcome
        +int turn
        +StressLevel stress_level
        +string asin
    }

    DebateInvocationPayload --> DebateSession : creates
    DebateSession --> StressSignals : computes
    DebateSession --> MemoryContext : reads
    MemoryContext --> ComposedPrompt : feeds
    DebateSession --> StrandsStreamEvent : emits
    DebateSession --> CooldownState : updates_on_refuse
    DebateSession --> AgentCoreMemoryEventMetadata : writes_per_turn
    DebateSession --> AffirmationMessage : on_agreed
    CooldownState --> CooldownDecision : derives
```

---

## 2. 入力 DTO

### 2.1 DebateInvocationPayload

AgentCore Runtime `InvokeAgentRuntimeCommand.payload` で受け取る JSON（Mobile から送信）。1 つの entrypoint で論破ストリーミングと肯定フィードバック生成の両方を扱うため、`action` フィールドで分岐する。

**Python（Pydantic v2）**:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

DebateTrigger = Literal['reel_skip', 'cart_intercept', 'product_dwell']
DebateAction = Literal['start_session', 'request_affirmation']

class DebateInvocationPayload(BaseModel):
    action: DebateAction = 'start_session'  # v3.3 C3-3 修正で追加
    user_input: str = Field(..., min_length=1, max_length=2000)
    asin: str = Field(..., pattern=r'^[A-Z0-9]{10}$')
    trigger: DebateTrigger
    client_session_id: Optional[str] = Field(None, min_length=26, max_length=128)
    client_signals: Optional['ClientSignals'] = None
    # action='request_affirmation' のみで使う
    outcome: Optional[Literal['agreed']] = None  # 翻意した時のみ
```

**TypeScript**:
```typescript
export type DebateTrigger = 'reel_skip' | 'cart_intercept' | 'product_dwell';
export type DebateAction = 'start_session' | 'request_affirmation';

export interface DebateInvocationPayload {
  action: DebateAction;
  user_input: string;
  asin: string;
  trigger: DebateTrigger;
  client_session_id?: string;
  client_signals?: ClientSignals;
  outcome?: 'agreed';  // request_affirmation 時のみ
}
```

#### 不変条件
- `asin` は 10 桁英数字大文字（[business-rules.md ASIN-01](../../unit-1-platform/functional-design/business-rules.md#1-asin-ルールs-01alg-asin)）
- `user_input` は 2000 文字以下（プロンプト爆発防止）
- `actor_id` は payload に含めない（JWT.sub から取得、SECURITY-08）
- `client_session_id` 未指定時は Backend で ULID 生成
- `action='request_affirmation'` のときのみ `outcome='agreed'` が必須（v3.3 C3-3 修正）

### 2.2 ClientSignals

Mobile が送信するストレス推定用の信号（PII 含まない）。

**Python**:
```python
class ClientSignals(BaseModel):
    recent_cart_intercepts: int = Field(0, ge=0, le=100)
    recent_debate_refuses: int = Field(0, ge=0, le=100)
    last_signin_at_late_night: bool = False
    current_hour_jst: int = Field(..., ge=0, le=23)
```

**TypeScript**:
```typescript
export interface ClientSignals {
  recent_cart_intercepts: number;
  recent_debate_refuses: number;
  last_signin_at_late_night: boolean;
  current_hour_jst: number;
}
```

---

## 3. ストリーミング配信

### 3.1 StrandsStreamEvent（Strands Agent の標準 streaming 形式、Q3=A）

Strands Agent が `agent.stream_async()` で yield する chunk。Mobile に AsyncIterable として配信。

**TypeScript（Mobile 側で型定義）**:
```typescript
export type EventType =
  | 'token'                       // delta_text あり
  | 'tool_use'                    // metadata.tool_name あり
  | 'turn_complete'               // 1 ターン完了
  | 'session_complete'            // セッション終了（reason 付き、'agreed' / 'refused' / 'graceful_timeout' / 'hard_timeout' / 'error' / 'cooldown' / 'agent_completed'）
  | 'error'                       // エラー
  | 'moderation_blocked'          // Q12 多層モデレーション ヒット
  | 'graceful_shutdown_initiated' // v3.2 Q11、80s 経過
  | 'summary'                     // graceful shutdown 後のサマリ
  | 'debate.cooldown_triggered'   // クールダウン中
  | 'debate.refused'              // ユーザー拒否
  | 'debate.agreed'               // ユーザー翻意
  | 'debate.affirmation_shown';   // 肯定フィードバック表示（action='request_affirmation' 応答）

export interface StrandsStreamEvent {
  type: EventType;
  delta_text?: string;
  metadata?: {
    tool_name?: string;
    axis?: DebateAxis;
    outcome?: DebateOutcome;
    pattern_detected?: string;  // moderation_blocked 時
    reason?: string;            // session_complete / error 時
    summary_text?: string;      // summary 時
    cooldown_until?: string;    // debate.cooldown_triggered 時、ISO 8601
    text?: string;              // debate.affirmation_shown 時
    style?: AffirmationStyle;   // debate.affirmation_shown 時
  };
}
```

> v3.3 修正: タイムアウトは `session_complete reason='graceful_timeout' | 'hard_timeout'` に統一（旧 `debate.timeout` を削除）。`debate.affirmation_shown` は `action='request_affirmation'` の応答 event として明示。

#### 不変条件
- `type='token'` のときは必ず `delta_text` が存在
- `type='session_complete'` で `reason` が必ず付与（`'agreed'` / `'refused'` / `'graceful_timeout'` / `'hard_timeout'` / `'error'` / `'cooldown'` / `'agent_completed'`、v3.3 修正）
- セクションマーカー `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` は `delta_text` 内のテキストとして含まれる（Mobile 側 event-parser.ts で軸判別）

### 3.2 セクションマーカー仕様

```
[FACT] これってデータあるんですよ。¥18,000 って時給 2,500 円換算で 7 時間 12 分の労働量なんで、要するに 1 日の業務 1 日分じゃないですか。
[PSYCHOLOGY] 悠介さん、4 ヶ月前に同じカテゴリのオーディオ買ってますよね。結局買って結果的に使ってるじゃないですか。それって悠介さんの購買履歴がもう答え出してるんですよ。
[REWARD] ストレス溜めて翌日の生産性下げる方が、コスト的に損じゃないですか？論理的に考えて、これって先行投資なんですよ。
```

Mobile 側 event-parser.ts はマーカーを認識して UI のラベル（事実 / 心理 / ご褒美）を切り替える。論理優位ディベート系トーン（敬語ベース、論理で黙らせるスタイル）（〜じゃないですか / 結局 / 論理的に / データあるんで）は v3.4 で Unit-3 のみ採用。

---

## 4. クールダウン

### 4.1 CooldownState（DDB エンティティ、唯一の自前テーブル）

**テーブル名**: `yudane-debate-<env>-cooldowns`

> **DDB 属性名は camelCase で統一**（v3.3 C3-2 修正）。Python 実装では `Item['cooldownUntil']` のように DDB 属性名と同じキーで dict アクセスする。Pydantic モデルでは `Field(alias=...)` で camelCase 属性を保持。

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `USER#{actor_id}` |
| `SK` | String | `COOLDOWN#current` |
| `consecutiveRefuses` | Number | 連続拒否回数（自然解除後の次回拒否で 1 にリセット）|
| `lastRefuseAt` | String (ISO 8601) | 最終拒否時刻 |
| `cooldownUntil` | String? (ISO 8601) | クールダウン解除時刻、未設定なら null |
| `ttl` | Number | UNIX timestamp、30 日後に自動削除 |

**Python（Pydantic v2、alias で camelCase 維持）**:
```python
from pydantic import BaseModel, Field, ConfigDict

class CooldownState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pk: str = Field(alias='PK')
    sk: str = Field(alias='SK')
    consecutive_refuses: int = Field(alias='consecutiveRefuses')
    last_refuse_at: datetime = Field(alias='lastRefuseAt')
    cooldown_until: Optional[datetime] = Field(default=None, alias='cooldownUntil')
    ttl: int  # UNIX timestamp
```

#### 不変条件（PBT-03 重点）
- `consecutiveRefuses == 3` に達した瞬間に必ず `cooldownUntil = now + 3h`
- `ttl == int((now + 30d).timestamp())`
- `consecutiveRefuses` は **自然解除後の次回拒否で 1 にリセット**（v3.3 M3-1 修正、business-rules COOLDOWN-04）

### 4.2 CooldownDecision（value object、business-logic ALG-COOLDOWN-CHECK の戻り値）

**Python**:
```python
class CooldownDecision(BaseModel):
    active: bool
    cooldown_until: Optional[datetime] = None
    consecutive_refuses: int = 0
```

> 戻り値の Python オブジェクトは snake_case（Python 慣習）、DDB 属性は camelCase（API / JSON 標準）で使い分け。Pydantic alias で変換。

#### 不変条件
- `active == True` のとき `cooldown_until` が必ず存在
- 純関数の戻り値（同一入力 → 同一出力）

---

## 5. ストレス推定

### 5.1 StressSignals（dataclass、no persistence）

ストレス推定の中間結果。Telemetry には `stress_level` のみ送信、signals 自体は送らない（PII 配慮）。

**Python**:
```python
StressLevel = Literal['low', 'mid', 'high']

class StressSignals(BaseModel):
    client_signals: ClientSignals
    memory_signals: list[str]   # Memory retrieve 結果のサマリ（low cardinality）
    score: int

class StressLevelResult(BaseModel):
    level: StressLevel
    score: int
    signals_used: list[str]  # debug 用、Telemetry には送らない
```

#### 不変条件（PBT-07 重点）
- `level in {'low', 'mid', 'high'}`
- `score >= 0`

---

## 6. プロンプト合成

### 6.1 ComposedPrompt（value object、business-logic ALG-PROMPT の戻り値）

**Python**:
```python
DebateAxis = Literal['fact', 'psychology', 'reward']

class ComposedPrompt(BaseModel):
    text: str = Field(..., max_length=8000)  # PROMPT_MAX_LENGTH_CHARS、概算 token 数として
    axes: list[DebateAxis]  # 含まれる軸（PBT-03 検証用）
```

#### 不変条件（PBT-03 / PBT-08 重点）
- `'reward' in axes if stress_level in {'mid', 'high'} else 'reward' not in axes`
- `'fact' in axes` 必須、`'psychology' in axes` 必須
- `len(text) <= PROMPT_MAX_LENGTH_CHARS`（既定 8000、概算 token 数として）

### 6.2 AffirmationMessage（肯定フィードバック）

**Python**:
```python
AffirmationStyle = Literal['casual', 'cool', 'caring']

class AffirmationMessage(BaseModel):
    text: str = Field(..., max_length=160)
    style: AffirmationStyle
```

**TypeScript**:
```typescript
export type AffirmationStyle = 'casual' | 'cool' | 'caring';

export interface AffirmationMessage {
  text: string;
  style: AffirmationStyle;
}
```

#### 不変条件（business-rules MOD-03 / 06）
- 必ず NG-6 正規表現検査を経由（生成失敗時は `AFFIRMATION_FALLBACK` 文言で置換）
- `len(text) <= 160`（プッシュ通知 / トースト UI に収まる長さ）

---

## 7. AgentCore Memory データモデル

### 7.1 AgentCoreMemoryEventMetadata（Memory `create_event` の event_metadata）

Memory に保存される構造化メタ。組み込み 2 種 + custom Strategy の抽出ターゲット。

**Python**:
```python
DebateOutcome = Literal['agreed', 'refused', 'ongoing']
# 注: タイムアウトは StrandsStreamEvent.session_complete.reason='graceful_timeout' | 'hard_timeout'
# として扱い、DebateOutcome には含めない（v3.3 M5-2 修正、M4-2 と整合）

class AgentCoreMemoryEventMetadata(BaseModel):
    axis: DebateAxis
    outcome: DebateOutcome
    turn: int = Field(..., ge=1, le=20)  # 1 セッション最大 20 ターン想定
    stress_level: StressLevel
    asin: str = Field(..., pattern=r'^[A-Z0-9]{10}$')
```

#### 不変条件
- PII を含めない（business-rules MEMORY-07）
- `turn >= 1`、`asin` は 10 桁英数字大文字
- serialize → deserialize で同一値（PBT-02）

### 7.2 Memory Strategy 設定（CDK 設計反映）

| Strategy | name | namespace | 採用 Phase | 抽出内容 |
|---|---|---|---|---|
| userPreference（組み込み）| `debate_outcomes` | `/user/debate/{actorId}/` | P0 | 翻意した軸 / ターン数 / 商品カテゴリの好み |
| semantic（組み込み）| `stress_signals` | `/user/stress/{actorId}/` | P0 | 直近の活動パターン |
| custom（v3.2 / Q16=B）| `m1_m2_axis_extractor` | `/user/m1m2/{actorId}/` | P1 | M-1 / M-2 軸での翻意パターン（Haiku 4.5 抽出）|

### 7.3 MemoryContext（dataclass、ALG-MEMORY-READ の戻り値）

**Python**:
```python
class OutcomeRecord(BaseModel):
    axis: DebateAxis
    outcome: DebateOutcome
    turn: int
    occurred_at: datetime

class CalendarContext(BaseModel):
    upcoming_event_categories: list[str]   # 'work' | 'social' | 'travel' 等
    busy_hours_per_week: int

class MemoryContext(BaseModel):
    recent_debate_outcomes: list[OutcomeRecord]
    preferred_axis: DebateAxis
    stress_signals: list[str]
    m1m2_axis_extracted: list[str]  # P1 のみ、P0 は空 list
    hourly_wage_yen: Optional[int]
    calendar_context: CalendarContext
    preferred_affirmation_style: AffirmationStyle
```

#### 不変条件
- empty MemoryContext でも `preferred_axis = 'fact'` の既定値で動作（business-rules PROMPT-CONFIG）
- `recent_debate_outcomes` は最新 5 件まで（top_k=5 制限、business-rules MEMORY-09）

---

## 8. DebateSession（in-memory dataclass、永続化なし）

論破セッション全体を Strands Agent 内で保持する作業領域（永続化なし、AgentCore Memory + DDB に書き出し）。

**Python**:
```python
class DebateSession(BaseModel):
    session_id: str  # ULID
    runtime_session_id: str  # f"{session_id}_{actor_id}"、26 + 1 + 36 = 63 文字（business-rules STREAM-03）
    actor_id: str
    asin: str
    started_at: datetime
    ends_at: datetime  # started_at + 90s
    stress_level: StressLevel
    turn_count: int = 0
    outcome: DebateOutcome = 'ongoing'
```

> `qualifier`（'live' / 'canary'）は Mobile 側で `InvokeAgentRuntimeCommand` 呼び出し時に指定するパラメータ。AgentCore Runtime 起動後の Strands Agent 内では参照しないため DebateSession には含めない（v3.3 M4-1 修正）。

#### 不変条件
- `ends_at == started_at + 90s`
- `session_id` は 1 セッション内で不変
- 永続化しない（AgentCore Runtime microVM 終了で破棄、必要なメタは Memory に都度書き込み）

---

## 9. DTO 一覧サマリ

| 区分 | エンティティ | 永続化 | TS / Py 両方 | PII | 備考 |
|---|---|---|---|---|---|
| 入力 | DebateInvocationPayload | — | ✅ | ❌ | Mobile → Runtime payload |
| 入力補助 | ClientSignals | — | ✅ | ❌ | ストレス推定信号 |
| Stream | StrandsStreamEvent | — | TS のみ | ❌ | Mobile 側型定義 |
| Stream | EventType | — | ✅ | ❌ | enum 相当 |
| 永続 | CooldownState | DDB | Py | actor_id（Cognito sub）| 唯一の自前テーブル |
| 値 | CooldownDecision | — | Py | ❌ | ALG-COOLDOWN-CHECK 戻り値 |
| 中間 | StressSignals | — | Py | ❌ | Telemetry 送信時は level のみ |
| 中間 | StressLevel | — | ✅ | ❌ | 'low' \| 'mid' \| 'high' |
| 値 | ComposedPrompt | — | Py | ❌ | プロンプト合成結果 |
| 値 | DebateAxis | — | ✅ | ❌ | 'fact' \| 'psychology' \| 'reward' |
| 値 | AffirmationMessage | — | ✅ | ❌ | 肯定フィードバック |
| 永続 | AgentCoreMemoryEventMetadata | Memory | Py | actor_id のみ（namespace 経由）| 組み込み 2 種 + custom Strategy 抽出対象 |
| 中間 | MemoryContext | — | Py | ❌ | ALG-MEMORY-READ 戻り値 |
| in-mem | DebateSession | — | Py | actor_id | Strands Agent 内のみ、永続化なし |

> 全 DTO は OpenAPI 契約に登場せず（AgentCore Runtime 直接呼び出し）、`shared/agentcore-contracts/debate.ts`（新設）で TypeScript 型を共有する。詳細は `strands-agent-design.md` を参照。
