# Unit-3 Debate — Domain Models 実装サマリ（Phase 1 Step 3）

> Phase 1 Step 3（Backend / Domain Models、クラシック TDD + PBT-02）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 3](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [domain-entities.md](../functional-design/domain-entities.md) / [business-rules.md](../functional-design/business-rules.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: クラシック TDD + PBT-02

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `backend/src/debate/domain/__init__.py` | パッケージ公開 API（`ClientSignals` / `CooldownDecision` / `CooldownState` / `DebateAction` / `DebateInvocationPayload` / `DebateTrigger`） |
| `backend/src/debate/domain/payloads.py`（80 行） | 入力 DTO（Mobile → AgentCore）|
| `backend/src/debate/domain/results.py`（55 行） | 結果 DTO（Cooldown 判定 / DDB レコード）|
| `backend/tests/debate/domain/test_payloads.py`（200 行）| ユニットテスト 22 ケース |
| `backend/tests/debate/property/test_payloads_property.py`（90 行）| PBT-02 ラウンドトリップ 2 ケース |

---

## 2. ドメインモデル一覧

### 2.1 DebateTrigger（Literal 型）

```python
DebateTrigger = Literal["reel_skip", "cart_intercept", "product_dwell"]
```

論破セッションの起動経路を 3 種に限定。 `unknown_trigger` / `REEL_SKIP`（大文字）等は ValidationError。

### 2.2 DebateAction（Literal 型）

```python
DebateAction = Literal["start_session", "request_affirmation"]
```

AgentCore entrypoint の分岐。デフォルトは `start_session`。

### 2.3 ClientSignals（PII を含まないストレス推定信号）

| フィールド | 型 | 制約 | 用途 |
|---|---|---|---|
| `recent_cart_intercepts` | int | 0..100 | 直近 7 日カート介入回数 |
| `recent_debate_refuses` | int | 0..100 | 直近 7 日論破拒否回数 |
| `last_signin_at_late_night` | bool | – | 直近 24h 深夜帯サインインしたか |
| `current_hour_jst` | int | 0..23 | 現在 JST 時 |

**PII 含まない**こと（NFR-SEC-DEBATE-04 / MEMORY-07）を Telemetry 送信前提として保証。

### 2.4 DebateInvocationPayload（Mobile → AgentCore Runtime の入力 DTO）

| フィールド | 型 | 制約 / 既定値 | 役割 |
|---|---|---|---|
| `action` | `DebateAction` | 既定 `'start_session'` | entrypoint 分岐 |
| `user_input` | str | 1〜2000 文字 | ユーザー入力（プロンプト爆発防止）|
| `asin` | str | `^[A-Z0-9]{10}$` | Amazon ASIN（business-rules ASIN-01）|
| `trigger` | `DebateTrigger` | 必須 | 起動経路 |
| `client_session_id` | str? | 26〜128 文字 | Mobile 側 ULID（None なら Backend 発番）|
| `client_signals` | `ClientSignals?` | 任意 | ストレス推定信号 |
| `outcome` | `Literal["agreed"]?` | 任意 | `request_affirmation` 時のみ意味あり |

**SECURITY-08 不変条件**: `Pydantic ConfigDict(extra="ignore")` により、攻撃者が `actor_id` を payload に偽装しても **完全に破棄される**。AgentCore Runtime の `context.user.sub` から取得するのが正（Step 5 main.py で実装）。

### 2.5 CooldownDecision（純粋 value object）

`ALG-COOLDOWN-CHECK` の戻り値型：

```python
class CooldownDecision(BaseModel):
    active: bool                              # True ならクールダウン中
    cooldown_until: datetime | None = None    # active=True で必ず存在
    consecutive_refuses: int = 0              # ≥ 0
```

### 2.6 CooldownState（DDB Cooldowns レコード、camelCase ↔ snake_case 変換）

DDB 属性名は **camelCase**（domain-entities §4.1）、Python 内部は snake_case。`pydantic.Field(alias=...)` で双方向変換：

| Python 属性 | DDB 属性 | 制約 |
|---|---|---|
| `pk` | `PK` | `'USER#<actor_id>'` |
| `sk` | `SK` | `'COOLDOWN#current'` |
| `consecutive_refuses` | `consecutiveRefuses` | ≥ 0 |
| `last_refuse_at` | `lastRefuseAt` | datetime（ISO 8601 自動 parse）|
| `cooldown_until` | `cooldownUntil` | datetime? |
| `ttl` | `ttl` | UNIX timestamp ≥ 0 |

`ConfigDict(populate_by_name=True)` により、Python コードからは `CooldownState(pk=..., sk=...)` も `CooldownState(PK=..., SK=...)` も両方使える。

---

## 3. テスト 24 ケース

### 3.1 ユニットテスト 22 ケース（test_payloads.py）

| グループ | テストケース | 検証 |
|---|---|---|
| Valid Cases | start_session payload / default action / request_affirmation+outcome / with client_signals | 正常系 |
| SECURITY-08 | actor_id を payload に入れても無視される | 攻撃者の偽装を破棄 |
| ASIN 検証（5 件） | 小文字 / 9 桁 / 11 桁 / ハイフン / 空文字 | 全て ValidationError |
| user_input 検証 | 2001 文字 / 空文字 | ValidationError |
| trigger 検証（4 件）| unknown / 大文字 / share_extension / 空文字 | ValidationError |
| ClientSignals | 正常 / hour 範囲外（-1, 24, 100） / count 範囲外（-1, 101）| 検証ロジック確認 |

### 3.2 PBT-02 ラウンドトリップ 2 ケース（test_payloads_property.py）

```python
@given(user_input=..., asin=..., trigger=..., action=...)
def test_payload_round_trip_preserves_values(...):
    payload_a = DebateInvocationPayload.model_validate(data)
    dumped = payload_a.model_dump()
    payload_b = DebateInvocationPayload.model_validate(dumped)
    assert payload_a == payload_b  # 任意の有効データで保存
```

**Hypothesis profile**: default（100 examples 自動生成）/ shrinking + seed ログ確認可能。

---

## 4. テスト結果

| 指標 | 値 |
|---|---|
| Tests | 22 unit + 2 PBT-02 = **24/24 green** |
| Duration | 1.10s |
| Line coverage（src.debate.domain）| **100%** |
| Branch coverage | **100%** |

---

## 5. 設計上の判断

### 5.1 `extra='ignore'` の戦略的採用（SECURITY-08）

Pydantic v2 既定は `extra='ignore'` だが、明示的に `ConfigDict(extra='ignore')` を書くことで「actor_id は payload に来るべきでない」という設計意図を **コードレベルで宣言** する。`extra='allow'` にすると属性として保持され攻撃面を作るため厳禁、`extra='forbid'` にすると古い Mobile クライアントが新フィールドを誤って付与した際に互換性破壊するため不採用。

### 5.2 `populate_by_name=True` で双方向 alias

DDB 属性名（camelCase）と Python 慣習（snake_case）の差を Pydantic alias で吸収。`CooldownState.model_validate(ddb_item)` でも `CooldownState(pk=..., sk=...)` でも動作させる。

### 5.3 Phase 2 への引き継ぎ

- **追加されるモデル**: `StrandsStreamEvent` / `EventType`（TS 側で実装、TS は Step 7 で実装）/ `DebateSession`（in-memory dataclass、Phase 2 main.py 拡張時）/ `MemoryContext` / `ComposedPrompt` / `AffirmationMessage` / `StressSignals`（Phase 2 T2.1〜T2.5）
- **拡張**: `DebateInvocationPayload` に新フィールド追加時は `extra='ignore'` を維持（後方互換性）

---

## 6. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: 純粋ドメインモデル（80 + 55 行）として独立、Strands Agent / Cooldown DDB / 他層から疎結合に利用可能
- **創造性とテーマ適合性**: SECURITY-08 不変条件（actor_id 偽装の自動破棄）を **コード + テスト + ドキュメント** で 3 重保証、倫理担保の物理層
- **ドキュメント品質**: 全モデルに Google-style docstring、ruff D ルールパス、不変条件をコード内コメントで明示
- **AI-DLC プロセス**: PBT-02（NFR-PBT-DEBATE-02）を Phase 1 で **テスト先行** で実装、Phase 2 以降の TDD サイクルの土台を確立
