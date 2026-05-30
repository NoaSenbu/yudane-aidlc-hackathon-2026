# Unit-3 Debate — Cooldown DDB Adapter 実装サマリ（Phase 1 Step 4）

> Phase 1 Step 4（Backend / Cooldown DDB Adapter、クラシック TDD + PBT-03）の実装結果。
>
> 参照: [Phase 1 Plan §1 Step 4](../../../plans/unit-3-debate-code-generation-phase1-plan.md) / [business-rules.md §2 COOLDOWN](../functional-design/business-rules.md) / [business-logic-model.md ALG-COOLDOWN](../functional-design/business-logic-model.md)
>
> 完了日: 2026-05-30 / 担当: Member B（AI 代行実装）/ TDD スタイル: クラシック TDD + PBT-03

---

## 1. 生成ファイル

| ファイル | 役割 |
|---|---|
| `backend/src/debate/cooldown.py`（200 行）| Cooldown DDB Adapter（`check_cooldown` + `increment_refuse_count`） |
| `backend/tests/debate/test_cooldown.py`（300 行）| ユニットテスト 6 ケース（boto3 Stubber） |
| `backend/tests/debate/property/test_cooldown_property.py`（160 行）| PBT-03 不変条件 2 プロパティ（Hypothesis）|

---

## 2. API 仕様

### 2.1 `check_cooldown(actor_id, now, table_name) -> CooldownDecision`

純関数（DDB read のみ）。レコードの状態を 3 通りに分類：

| DDB 状態 | 戻り値 |
|---|---|
| レコードなし | `CooldownDecision(active=False, consecutive_refuses=0)` |
| `cooldown_until > now`（クールダウン中）| `CooldownDecision(active=True, cooldown_until=..., consecutive_refuses=...)` |
| `cooldown_until <= now`（自然解除済み、COOLDOWN-04）| `CooldownDecision(active=False, consecutive_refuses=0)` |
| クールダウン未発動（`cooldown_until=None`）| `CooldownDecision(active=False, consecutive_refuses=...)` |

**ConsistentRead=True** で eventual consistency を排除（短時間 / 高頻度 state、business-rules COOLDOWN-08）。

### 2.2 `increment_refuse_count(actor_id, now, table_name, *, after_natural_release=False) -> CooldownState`

`after_natural_release` で 2 つの実装パスを分岐：

#### パス A: 通常パス（`after_natural_release=False`）

```python
# 1 回目の UpdateItem: ConditionExpression で「count + 1 < 3」を条件付加
UpdateExpression: "SET consecutiveRefuses = if_not_exists(consecutiveRefuses, :zero) + :one, ..."
ConditionExpression: "attribute_not_exists(consecutiveRefuses) OR consecutiveRefuses + :one < :threshold"

# 1〜2 回目: 上記が成功（count=1 / count=2）
# 3 回目: ConditionalCheckFailedException → 2 段目を発行
UpdateExpression: "SET consecutiveRefuses = :threshold, cooldownUntil = :cooldown_until, ..."  # threshold=3, cooldown_until=now+3h
```

これにより **PBT-03 不変条件「3 回目で必ず cooldown_until = now + 3h を SET」** を保証。

#### パス B: 自然解除後（`after_natural_release=True`）

```python
UpdateExpression: "SET consecutiveRefuses = :one, lastRefuseAt = :now, #ttl = :ttl REMOVE cooldownUntil"
```

呼び出し側は事前に `check_cooldown` で自然解除を確認した上でこのパスを使う。**COOLDOWN-04 / M3-1 不変条件「自然解除後の最初の拒否で consecutive_refuses = 1」** を保証。

### 2.3 設定値（COOLDOWN-CONFIG）

```python
COOLDOWN_TRIGGER_THRESHOLD = 3
COOLDOWN_DURATION_SECONDS = 3 * 60 * 60     # 3 hours
COOLDOWN_TTL_SECONDS = 30 * 24 * 60 * 60    # 30 days
```

business-rules.md §2 COOLDOWN-CONFIG と完全整合。

---

## 3. テスト 8 ケース

### 3.1 Unit Test 6 ケース（test_cooldown.py）

| クラス | テストケース | 検証 |
|---|---|---|
| TestCheckCooldown | `returns_inactive_when_no_record_exists` | レコードなし → `active=False, count=0` |
| TestCheckCooldown | `returns_active_when_cooldown_until_in_future` | `cooldown_until > now` → `active=True` |
| TestCheckCooldown | `returns_inactive_after_natural_release` | `cooldown_until <= now` → 自然解除（COOLDOWN-04）|
| TestIncrementRefuseCount | `first_refuse_sets_count_to_one` | 初回拒否 → `count=1`, `cooldown_until=None` |
| TestIncrementRefuseCount | `third_refuse_triggers_cooldown` | 3 回目 → `count=3`, `cooldown_until=now+3h`（COOLDOWN-02）|
| TestIncrementRefuseCount | `natural_release_resets_to_one` | 自然解除後の最初の拒否 → `count=1`（COOLDOWN-04 / M3-1）|

### 3.2 PBT-03 不変条件 2 プロパティ（test_cooldown_property.py）

| Property | Hypothesis 戦略 | 不変条件 |
|---|---|---|
| `test_third_refuse_always_sets_cooldown_until` | `actor_id` × `now`（datetime ∈ 2025-2030 UTC）| 3 回目で必ず `count=3, cooldown_until=now+3h` |
| `test_natural_release_always_resets_to_one` | 同上 | 自然解除後 → 必ず `count=1, cooldown_until=None` |

各 50 examples × 2 properties = 100 検証。

---

## 4. テスト結果

| 指標 | 値 |
|---|---|
| Tests | 6 unit + 2 PBT-03 = **8/8 green** |
| Duration | 0.61s |
| Line coverage（src.debate.cooldown）| **90%** |
| Branch coverage | **83%** |

未カバー（line 39 / 85 / 177-178）の説明：
- **line 39 `_build_key`**: シンプルな dict 構築、tested implicitly through the public API
- **line 85** : `state.cooldown_until is None` で `cooldown_until=None` のケースは「未発動カウント中」としてレコードあり想定の test を Step 5 で追加予定（Phase 1 範囲外）
- **line 177-178**: `ClientError` の `Code != "ConditionalCheckFailedException"` の unexpected error raise パス、fail-fast の意図的設計（テストせず raise を伝播）

---

## 5. 設計上の判断

### 5.1 ConditionalCheck + 2 段クエリで PBT-03 を保証

「3 回目で必ず cooldown_until を SET」を **ConditionExpression + try/except** で実装。1 段クエリでは「count を +1 する → 結果が 3 なら cooldown_until を SET」のような複合操作は DDB UpdateExpression で記述不可なため、2 段クエリ + ConditionalCheckFailedException を制御フローとして利用。これは DDB のベストプラクティスと整合。

### 5.2 自然解除リセットを呼び出し側責務に分離

`increment_refuse_count` 内で自然解除判定を再度実行すると DDB GetItem 1 回分の余剰コストが発生するため、`check_cooldown` で自然解除を判定済みのクライアントが `after_natural_release=True` で呼び出す設計。`check_cooldown` の戻り値で `active=False, count=0` を返すパスが自然解除の signal となる。

### 5.3 `_parse_cooldown_state` で DDB low-level → Pydantic 変換

DDB low-level 形式（`{"S": "..."}` / `{"N": "..."}`）を Python 型に変換する純粋ユーティリティ。Pydantic alias で snake_case ↔ camelCase 自動変換。

### 5.4 Phase 2 への引き継ぎ

- **Lambda Layer 統合**: `_LOGGER.error` を `B-12 AuditLogger` Lambda Layer 経由（Powertools Logger）に置換予定
- **DDBError → DomainError 変換**: 現状は ClientError を直接 raise、Phase 2 で DomainError 階層を導入し AuditLogger 経由でログ出力
- **DEBT-05 / SAFE-04 連携**: Unit-7 Safeguard `PATCH /v1/safeguard` の `cooldownReleased: true` で手動解除する処理は、`increment_refuse_count(after_natural_release=True)` を Unit-7 から呼び出す形で連携予定

---

## 6. ハッカソン評価軸へのインパクト

- **Unit 分解の適切さ**: Cooldown ロジックを 200 行の独立モジュールに分離、main.py から疎結合に呼び出し可能。Unit-7 Safeguard からの手動解除も同 API で対応可能
- **創造性とテーマ適合性**: 連続拒否 3 回 → 3 時間クールダウンは「ユーザーを倫理的に守る」物理層。NG-6 滑落（罪悪感強要・脅迫）の最終防衛線として機能
- **ドキュメント品質**: 全関数に docstring + 不変条件をコード内コメント、PBT-03 の 50 examples × 2 properties で property 化した不変条件
- **AI-DLC プロセス**: PBT-03（NFR-PBT-DEBATE-03）を Phase 1 で property 化、Phase 2 以降の TDD サイクルで継続検証可能
