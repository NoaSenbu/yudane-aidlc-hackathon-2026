# Unit-3 Debate — Business Logic Model

> Unit-3 Debate のビジネスロジックを **技術非依存** で記述。アルゴリズム・処理フロー・状態遷移を扱う（インフラ実装は NFR Design / Infrastructure Design で確定）。
>
> 参照: [domain-entities.md](./domain-entities.md) / [business-rules.md](./business-rules.md) / [strands-agent-design.md](./strands-agent-design.md) / [prompt-composition.md](./prompt-composition.md) / [sequence-diagrams.md](./sequence-diagrams.md)
>
> 確定方針（[functional-design-plan.md v3.3](./functional-design-plan.md#6-decision-recordv33-確定2026-05-29) Decision Record）: Q1=C / Q2=C / Q3=A / Q4=A+SSM / Q5=A / Q6=A / Q7=A / Q8=B / Q9=D / Q10=B / Q11=A+graceful shutdown 80s / Q12=D 多層 / Q13=D+S3 / Q14=A PBT 全面 / Q15=A / Q16=B / Q17=B live+canary
>
> 関連要件: FR-DEBATE-01〜09（[requirements.md §5.1](../../../inception/requirements/requirements.md#51-論破チャット-fr-debate--コア)）/ M-1 + M-2 併走（[requirements.md §2.5.1](../../../inception/requirements/requirements.md#251-ダメ化の-3-段メカニズム)）

---

## ALG-DEBATE-START: 論破セッション開始 / 肯定フィードバック生成（B-02 entrypoint、FR-DEBATE-01 / 09、v3.3 C3-3 修正）

### 入力 / 出力

- 入力: `DebateInvocationPayload`（domain-entities §2.1）— `action`（'start_session' | 'request_affirmation'）+ `user_input`, `asin`, `trigger`, `client_session_id?`, `outcome?`
- 出力: `AsyncIterable<StrandsStreamEvent>`（domain-entities §3.1）— Strands streaming chunk

### 処理フロー（action 分岐）

```
debate_handler(payload, context):
  1. 認証コンテキスト解決
       - context から actor_id（Cognito JWT.sub）を取得
       - actor_id が無ければ AccessDenied として error event を yield + return（401 相当）

  2. payload 検証
       - DebateInvocationPayload.model_validate(payload)
       - action = invocation.action（既定 'start_session'）

  3. action による分岐（v3.3 C3-3 修正）
       - if action == 'request_affirmation':
             # ALG-AFFIRMATION（肯定フィードバック生成）に直接 dispatch
             affirmation = generate_affirmation(actor_id, invocation.asin, invocation.client_signals, invocation.outcome)
             yield event(type='debate.affirmation_shown', metadata={text, style})
             return

       - else: # 'start_session' = 通常の論破セッション開始

  4. クールダウン判定（ALG-COOLDOWN-CHECK）
       - DDB yudane-debate-<env>-cooldowns から (USER#{actor_id}, COOLDOWN#current) を取得
       - cooldownUntil > now なら debate.cooldown_triggered イベントを yield + return（再掲ループの主要発火点）

  5. セッション識別子の確定
       - session_id = payload.client_session_id ?? generate_ulid()  # ULID 26 文字
       - runtime_session_id = f"{session_id}_{actor_id}"  # 26 + 1 + 36 = 63 文字、AgentCore Runtime 制約 33-256 を満たす（business-rules STREAM-03、v3.3 M6-1 修正）

  6. ストレスレベル推定（ALG-STRESS）
       - stress_level = estimate_stress_level(actor_id, invocation.client_signals)

  7. プロンプト合成（ALG-PROMPT）
       - composed_prompt = compose_debate_prompt(invocation.user_input, invocation.asin, stress_level, memory_context)

  8. Strands Agent 起動 + ストリーミング配信（ALG-MOD 多層モデレーション統合）
       - async for event in agent.stream_async(composed_prompt):
             yield event（モデレーション後）

  9. ターン履歴の Memory 保存（ALG-MEMORY-WRITE、Strands hooks で自動）

  10. 終了処理
       - 翻意（agreed） → debate.agreed event。Mobile が次ターンで action='request_affirmation' で再呼び出し
       - 拒否（refused） → debate.refused + ALG-COOLDOWN-INC でカウント増分
       - timeout（80s elapsed）→ ALG-GRACEFUL-SHUTDOWN でサマリ生成 + session_complete reason='graceful_timeout'
       - timeout（90s 厳守）→ session_complete reason='hard_timeout'（graceful 失敗時の保険）
       - error → DomainError → error event
```

### 不変条件
- `actor_id` の取得失敗時に Bedrock 呼び出しを行わない（コスト保護）
- `session_id` は 1 セッション内で不変（リトライ・graceful shutdown 時も同一）
- payload に含まれる `actor_id` は **無視**、JWT.sub のみを正とする（SECURITY-08）
- `action='request_affirmation'` のみ ALG-AFFIRMATION を実行、それ以外は通常の論破フロー

---

## ALG-COOLDOWN-CHECK: クールダウン判定（DDB Cooldowns、FR-DEBATE-05、Q2=C）

### 入力 / 出力
- 入力: `actor_id: string`, `now: ISO 8601`
- 出力: `CooldownDecision`（domain-entities §4.2）— `{ active: bool, cooldownUntil?, consecutiveRefuses }`

### 処理フロー

```
check_cooldown(actor_id, now):
  1. ddb.get_item(PK=USER#{actor_id}, SK=COOLDOWN#current)
       - 該当なし → return CooldownDecision(active=False, consecutive_refuses=0)

  2. cooldownUntil をパース
       - cooldownUntil > now → return CooldownDecision(active=True, cooldown_until=cooldownUntil, consecutive_refuses=consecutiveRefuses)
       - cooldownUntil <= now → 自然解除済として return CooldownDecision(active=False, cooldown_until=None, consecutive_refuses=0)
         （DDB レコードは TTL 30 日まで残るが、戻り値の consecutive_refuses は 0 として扱う、business-rules COOLDOWN-04）
```

### 不変条件
- 純関数（DDB read のみ、副作用なし）
- `cooldownUntil` は厳密比較（>= ではなく >、解除時刻ちょうどはアクセス可能）
- DDB 属性名は camelCase（`cooldownUntil` / `consecutiveRefuses` / `lastRefuseAt`、v3.3 C3-2 修正）。Python オブジェクト返却時は snake_case に変換（Pydantic alias）

---

## ALG-COOLDOWN-INC: 連続拒否カウンタ増分（DDB Cooldowns、Q2=C / PBT-03、v3.3 M3-1 修正）

### 入力 / 出力
- 入力: `actor_id: string`, `now: ISO 8601`
- 出力: `CooldownState`（domain-entities §4.1）

### 処理フロー（自然解除後のリセット対応版）

```
increment_refuse_count(actor_id, now):
  1. 自然解除検知のため CooldownState を読む
       state = ddb.get_item(PK=USER#{actor_id}, SK=COOLDOWN#current)

  2. 自然解除後の最初の拒否なら 1 から再カウント（M3-1 修正）
       if state.cooldownUntil and state.cooldownUntil <= now:
           # 自然解除後 → consecutiveRefuses を 1 にリセット、cooldownUntil をクリア
           ddb.update_item(
             PK=USER#{actor_id}, SK=COOLDOWN#current,
             UpdateExpression: "SET consecutiveRefuses = :one, lastRefuseAt = :now REMOVE cooldownUntil",
             ExpressionAttributeValues: {":one": 1, ":now": now},
           )
           return CooldownState(consecutive_refuses=1, last_refuse_at=now, cooldown_until=None, ttl=...)

  3. 通常の +1 増分
       result = ddb.update_item(
         PK=USER#{actor_id}, SK=COOLDOWN#current,
         UpdateExpression: "ADD consecutiveRefuses :one SET lastRefuseAt = :now",
         ExpressionAttributeValues: {":one": 1, ":now": now},
         ReturnValues: 'ALL_NEW',
       )

  4. consecutiveRefuses が COOLDOWN_TRIGGER_THRESHOLD（=3）に **到達した瞬間** に：
       - cooldownUntil = now + COOLDOWN_DURATION（=3h）
       - ttl = unix_timestamp(now) + COOLDOWN_TTL_SECONDS（=30 日）
       - ddb.update_item で cooldownUntil + ttl を SET

  5. result を返す（Pydantic alias で snake_case に変換）
```

### 不変条件（PBT-03 重点）
- `consecutiveRefuses == 3` に到達した瞬間に必ず `cooldownUntil = now + 3h` が DDB に SET される（PBT-03 の核心 property）
- 自然解除（`cooldownUntil <= now`）後の最初の拒否で `consecutiveRefuses == 1` にリセット（M3-1 修正、business-rules COOLDOWN-04 と整合）
- DDB 属性名は camelCase 統一（v3.3 C3-2 修正）
- 同一入力に対する増分は冪等ではない（毎回 +1）が、リクエスト境界で重複呼び出しは Mobile 側で防止

---

## ALG-STRESS: ストレスレベル推定（stress.py、Q8=B、PBT-07）

### 入力 / 出力
- 入力: `actor_id: string`, `now: ISO 8601`, `client_signals: ClientSignals?`（domain-entities §5.1）
- 出力: `stress_level: 'low' | 'mid' | 'high'`

### 処理フロー（軽量ヒューリスティック + Memory semantic 併用）

```
estimate_stress_level(actor_id, now, client_signals):
  score = 0

  # ステップ1: 時間帯（軽量ヒューリスティック）
  hour = parse_hour(now)
  if 23 <= hour or hour < 4:           # 深夜帯
      score += 2
  elif 18 <= hour < 23:                # 残業帯
      score += 1

  # ステップ2: クライアント信号
  if client_signals:
      if client_signals.recent_cart_intercepts >= 3:
          score += 1
      if client_signals.recent_debate_refuses >= 1:
          score += 1
      if client_signals.last_signin_at_late_night:
          score += 1

  # ステップ3: Memory semantic Strategy retrieve（Day 1 で空でも OK）
  signals = memory_client.retrieve_memories(
      namespace=f"/user/stress/{actor_id}/",
      query="ユーザーの最近のストレス兆候",
      top_k=3,
  )
  if signals contains '会議過多' or '深夜稼働' or '連続キャンセル':
      score += 1
  if signals contains '休日返上' or '徹夜':
      score += 2

  # ステップ4: スコアからレベル変換
  if score >= 4:
      return 'high'
  elif score >= 2:
      return 'mid'
  else:
      return 'low'
```

### 不変条件（PBT-07 重点）
- **戻り値は必ず `'low' | 'mid' | 'high'` の 3 種**（任意の入力 + 任意の Memory retrieval 結果でこの不変条件が成立）
- Memory retrieval が失敗・空でも `score = 0` で動作（Day 1 から動作可能、business-rules.md STRESS-04）
- 純関数ではない（Memory IO あり）が、決定論性は `score` の合計で保証（同一 score → 同一 level）

---

## ALG-PROMPT: M-1 + M-2 併走プロンプト合成（compose.py、FR-DEBATE-02 / FR-DEBATE-09、PBT-03、v3.3 C3-4 修正）

### 入力 / 出力
- 入力: `user_input: str`, `asin: str`, `stress_level: StressLevel`, `memory_context: MemoryContext`, `price_yen: int? = None`
- 出力: `composed_prompt: ComposedPrompt`（domain-entities §6.1）

> **NG-1〜8 ディレクティブは base block（`prompts/base.py`）に静的に埋め込み済**。`ng_directives` を関数引数として渡さない（v3.3 C3-4 修正、prompt-composition.md §7 と整合）。

### 処理フロー

```
compose_debate_prompt(user_input, asin, stress_level, memory_context, price_yen=None):
  base_block = render(BASE_TEMPLATE, asin=asin, user_input=user_input)
       # 論理優位ディベート系トーン（Unit-3 のみ v3.4 で再定義、FR-DEBATE-08）+ NG-1〜8 プロンプトガードレール（Q12 P0 層）静的埋め込み

  m1_fact_block = render(M1_FACT_AXIS_TEMPLATE,
                         hourly_wage_yen=memory_context.hourly_wage_yen or 2500,
                         price_yen=price_yen or 0,
                         calendar_context_summary=summarize_calendar(memory_context.calendar_context))
       # FR-DEBATE-02 事実軸: 時給換算 / 在庫希少性 / 予定整合

  m1_psychology_block = render(M1_PSYCHOLOGY_AXIS_TEMPLATE,
                               preferred_axis=memory_context.preferred_axis,
                               recent_outcomes_summary=summarize_outcomes(memory_context.recent_debate_outcomes),
                               m1m2_extracted_summary=summarize_m1m2(memory_context.m1m2_axis_extracted))
       # M-1 心理軸: 個別最適化情報を組み込み

  blocks = [base_block, m1_fact_block, m1_psychology_block]
  axes = ['fact', 'psychology']

  # M-2 併走: stress_level=mid/high なら必ず m2_reward_block を含める
  if stress_level in ('mid', 'high'):
      m2_reward_block = render(M2_REWARD_AXIS_TEMPLATE,
                               stress_level=stress_level,
                               calendar_busy_hint=summarize_busy_hint(memory_context.calendar_context),
                               price_yen=price_yen or 0)
       # FR-DEBATE-09 ストレス × ご褒美軸
      blocks.append(m2_reward_block)
      axes.append('reward')

  composed = '\n\n---\n\n'.join(blocks)
       # セクションマーカー [FACT] / [PSYCHOLOGY] / [REWARD] は各テンプレート内で記述

  if len(composed) > PROMPT_MAX_LENGTH_CHARS:
      composed = truncate_safely(composed, PROMPT_MAX_LENGTH_CHARS)

  return ComposedPrompt(text=composed, axes=axes)
```

### 不変条件（PBT-03 / PBT-08 重点）
- **`stress_level in ('mid', 'high')` なら必ず M-2 軸トークンが含まれる**（FR-DEBATE-09 不変条件、PBT-03 / PBT-08 の最重要 property）
- **base_block は必ず先頭**（プロンプト序列に依存する Bedrock の挙動を安定化）
- **NG-1〜8 ディレクティブが必ず含まれる**（base block に静的埋め込み、Q12 P0 = プロンプトガードレール層）
- 任意の入力で生成された `composed.text` は概算 token 数で 8000 token 以下（日本語 1 文字 ≒ 1〜2 token、Bedrock 200K token 上限の余裕）
- 純関数（同一入力 → 同一出力、副作用なし、Memory IO は呼び出し側）

---

## ALG-MEMORY-WRITE: Memory 書き込み（MemoryHook、Q1=C / Q10=B / Q16=B）

### 入力 / 出力
- 入力: `actor_id`, `session_id`, `messages`, `metadata`
- 出力: 副作用のみ（Memory への永続化）

### 処理フロー

```
on_turn_complete(actor_id, session_id, user_msg, ai_msg, axis, outcome, turn_num):
  1. memory_client.create_event(
       memory_id=DEBATE_MEMORY_ID,
       actor_id=actor_id,
       session_id=session_id,
       messages=[(user_msg, "USER"), (ai_msg, "ASSISTANT")],
       event_metadata={
           "axis": axis,           # "fact" | "psychology" | "reward"
           "outcome": outcome,     # "agreed" | "refused" | "ongoing"
           "turn": turn_num,
           "stress_level": stress_level,  # 推定値
           "asin": asin,
       },
     )
  2. event_metadata は AgentCore Memory の組み込み 2 種 Strategy（userPreference / semantic）と
     custom Strategy（m1_m2_axis_extractor）の抽出ターゲットとして自動処理される
```

### 段階実装（v3.3 M-3 修正）

| Phase | Strategy 構成 | 抽出される情報 |
|---|---|---|
| **P0**（Phase 1 〜 2）| userPreference + semantic（組み込み 2 種）| 翻意した軸の傾向 / 一般的な活動パターン |
| **P1**（Phase 4）| + custom `m1_m2_axis_extractor` | M-1 / M-2 メカニズム特化の構造化抽出 |

### 不変条件（PBT-02）
- `create_event` 直後に同 `session_id` で `get_last_k_turns(k=N)` を呼ぶと、保存した messages が最新 N 件以内に含まれる（round-trip 性質）
- `event_metadata` の serialize → deserialize で同一値（PBT-02 重点）

---

## ALG-MEMORY-READ: Memory retrieval（MemoryHook on_session_start）

### 処理フロー

```
build_memory_context(actor_id):
  1. recent_outcomes = memory_client.retrieve_memories(
       namespace=f"/user/debate/{actor_id}/",
       query="このユーザーが論破で翻意した軸の傾向",
       top_k=5,
     )
  2. preferred_axis = analyze(recent_outcomes)
       - 'fact' / 'psychology' / 'reward' の中で最頻
       - 初回ユーザー（empty）→ 'fact'（既定）
  3. stress_signals = memory_client.retrieve_memories(
       namespace=f"/user/stress/{actor_id}/",
       query="ユーザーの最近のストレス兆候",
       top_k=3,
     )
  4. axis_extracted = memory_client.retrieve_memories(  # P1 のみ
       namespace=f"/user/m1m2/{actor_id}/",
       query="M-1 / M-2 軸での翻意パターン",
       top_k=3,
     ) if custom_strategy_enabled else []
  5. return MemoryContext(
       recent_debate_outcomes=recent_outcomes,
       preferred_axis=preferred_axis,
       stress_signals=stress_signals,
       m1m2_axis_extracted=axis_extracted,
       hourly_wage_yen=lookup_user_profile(actor_id, 'hourly_wage_yen'),
       calendar_context=...,
     )
```

### 不変条件
- Memory retrieve が失敗・空でも例外を上げず `MemoryContext` 既定値を返す（Day 1 から動作）
- `top_k` は 5 を超えない（プロンプト爆発防止）

---

## ALG-AFFIRMATION: 肯定フィードバック生成（affirmation.py、FR-DEBATE-09 後段、M-2 ドーパミン回路強化、v3.3 C3-3 / m3-2 / m4-2 修正）

### 入力 / 出力
- 入力: `actor_id`, `asin`, `client_signals: ClientSignals?`, `outcome: 'agreed'`
- 出力: `AffirmationMessage`（domain-entities §6.2）

### 起動経路（v3.3 C3-3 修正）

肯定フィードバックは ALG-DEBATE-START の `action='request_affirmation'` 分岐から呼ばれる。Mobile が翻意後 `InvokeAgentRuntime(payload={action: 'request_affirmation', outcome: 'agreed', ...})` で 2 回目の呼び出しを行う。

### 処理フロー（async 関数）

```
async def generate_affirmation(actor_id, asin, client_signals, outcome):
  if outcome != 'agreed':
      return None  # 翻意した場合のみ発火（business-rules AFF-01）

  # 1. ストレスレベルを再推定（client_signals から軽量に）
  stress_level = estimate_stress_level(actor_id, utcnow(), client_signals)

  # 2. Memory から preferred_affirmation_style を取得
  context = await build_memory_context(actor_id)
  preferred_style = context.preferred_affirmation_style or 'casual'

  # 3. 短文生成（Bedrock、非ストリーミング、低 cost）
  message = await bedrock.invoke_model_async(
      model_id=MODEL_ID,                # SSM 経由で起動時に取得済（Q4=A+SSM）
      prompt=render(AFFIRMATION_TEMPLATE,
                    style=preferred_style,
                    asin=asin,
                    stress_level=stress_level),
      max_tokens=80,
      stream=False,
  )

  # 4. NG-6（脅迫・罪悪感強要）の正規表現検査（Q12 多層 第 3 層）
  if matches_ng6_patterns(message):
      return AffirmationMessage(text=AFFIRMATION_FALLBACK, style=preferred_style)

  return AffirmationMessage(text=message, style=preferred_style)
```

### 不変条件
- 翻意（agreed）以外では発火しない（拒否者を追い込まない、business-rules AFF-01）
- 必ず NG-6 正規表現検査を経由（M-2 ドーパミン強化が NG-6 に滑落しない安全装置、business-rules MOD-06）
- 「買わないと損する」「買わないとあなたはダメだ」型の表現は `AFFIRMATION_FALLBACK` に置換
- `MODEL_ID` は起動時 SSM `/yudane/<env>/debate/model-id` で解決済（v3.3 m3-2 修正、Q4=A+SSM）
- `async` 関数として呼び出し側（main.py の `await generate_affirmation(...)`）と整合（v3.3 m4-2 修正）

---

## ALG-GRACEFUL-SHUTDOWN: 80s graceful shutdown（v3.2 Q11、L1 機能面修正）

### 入力 / 出力
- 入力: `session_started_at`, `current_token_buffer`
- 出力: `final_summary_event` を yield、ストリームを綺麗にクローズ

### 処理フロー

```
async for event in agent.stream_async(composed_prompt):
    elapsed = now() - session_started_at

    if elapsed >= 80.0:
        # graceful shutdown trigger
        yield event_with_marker('graceful_shutdown_initiated')

        # 残り 10 秒（80s〜90s）でサマリ生成
        summary = await agent.invoke_async(
            "ここまでの論破サマリを 1〜2 文で生成。トーンは論理優位ディベート系（敬語、〜じゃないですか / 結局 / 論理的に / データあるんですか？）、未確定の論破軸を含めない",
            timeout_sec=10,
        )
        yield event_with_marker('summary', text=summary)
        yield event_with_marker('session_complete', reason='graceful_timeout')
        return

    yield event  # 通常配信
```

### 不変条件
- 80s 経過時には必ず `graceful_shutdown_initiated` event を 1 度だけ yield
- summary 生成のタイムアウトは 10 秒以内（90s 全体タイマーへの侵食を防ぐ）
- summary 生成が失敗した場合も `session_complete` は必ず yield（UI のローディング解除）

---

## ALG-MOD: 出力モデレーション 3 層（Q12=D 多層防御、PBT-08）

### 処理フロー

```
async for event in agent.stream_async(composed_prompt):
    # 第 1 層: プロンプトガードレール
    #   - composed_prompt.text 内に NG-1〜8 のディレクティブが既に含まれる
    #   - Bedrock がプロンプト指示を尊重して出力を生成（first defense）

    # 第 2 層: Bedrock Guardrails streaming
    #   - bedrock_kwargs.guardrailIdentifier が関連付けられた Strands Agent
    #   - DENIED_TOPICS = NG-1〜8、outputAssessments で chunk 単位検査
    #   - Guardrails 違反 chunk は Bedrock 側で blocked event に置換

    # 第 3 層: 正規表現多層検査（callback_handler）
    if regex_match_ng_patterns(event.delta_text):
        yield event_with_marker('moderation_blocked', reason=detected_pattern)
        return  # ストリーム終了

    yield event
```

### 不変条件（PBT-08 重点）
- **3 層のうち少なくとも 1 層が NG-1〜8 を必ず検出**（任意の出力で property 検証）
- 第 3 層（正規表現）の判定は decisive: ヒットしたら必ずストリーム終了 + `moderation_blocked` 配信
- 第 1 / 第 2 層のすり抜けがあっても第 3 層で確実に止める（fail-safe、business-rules.md MOD-01〜05）

---

## ALG-S3-EXPORT: Memory streamDeliveryResources S3 並行書き出し（Q13 P1、UC-06/07/08 のデータソース）

### 処理フロー

```
（CDK で Memory に streamDeliveryResources を設定）

agentcore.Memory(...).stream_delivery_resources({
  "s3": {
    "bucket": memory_export_bucket,    # yudane-debate-<env>-memory-export
    "prefix": "events/{year}/{month}/{day}/{hour}/",
    "kms_key": platform_kms_key,
  },
})

# Memory 側が events / strategy records を S3 に並行書き出し
# Memory expirationDuration: 90 日 で消えても、S3 側は Lifecycle で 365 日保全
```

### 処理フロー（Unit-8 から参照する側）

```
build_year1_degradation_arc(actor_id):
  1. Athena query:
       SELECT
         date_trunc('day', occurred_at) as day,
         metadata.axis,
         metadata.outcome,
         count(*) as turns
       FROM debate_outcomes_v1
       WHERE actor_id = ?
         AND occurred_at >= now() - interval '365' day
       GROUP BY 1, 2, 3
       ORDER BY 1
  2. Unit-8 が結果を時系列グラフ + 退化アーク UI に変換
```

### 不変条件
- S3 書き出しは Memory operation の **副作用** であり、`create_event` の同期返却を遅延させない
- Lifecycle: Standard → IA (30d) → Glacier (90d) → 削除 (365d)。Glacier 移行後も Athena からアクセス可能（Glacier Instant Retrieval）
- Unit-8 から S3 を参照する経路は IAM Role（Unit-8 stack の lambda execution role）に `s3:GetObject` for `memory-export-bucket-arn/*` を付与

---

## アルゴリズム一覧と検証方針サマリ

| ID | ロジック | 主担当ファイル | PBT 性質候補 | 関連 FR / Q |
|---|---|---|---|---|
| ALG-DEBATE-START | セッション開始 | backend/src/debate/main.py | — | FR-DEBATE-01 / Q3 / Q5 |
| ALG-COOLDOWN-CHECK | クールダウン読込 | backend/src/debate/cooldown.py | 純関数性 / 厳密比較 | FR-DEBATE-05 / Q2 |
| ALG-COOLDOWN-INC | カウンタ増分 | backend/src/debate/cooldown.py | **3 到達で必ず +3h**（PBT-03）| FR-DEBATE-05 / Q2 |
| ALG-STRESS | ストレス推定 | backend/src/debate/stress.py | **戻り値が low/mid/high の 3 種**（PBT-07）| FR-DEBATE-09 / Q8 |
| ALG-PROMPT | M-1 + M-2 併走合成 | backend/src/debate/prompts/compose.py | **stress=mid/high で必ず M-2 トークン**（PBT-03 / PBT-08）| FR-DEBATE-02 / 09 / Q7 / Q12 |
| ALG-MEMORY-WRITE | Memory 書き込み | backend/src/debate/memory_hooks.py | round-trip / metadata serialize（PBT-02）| Q1 / Q10 / Q16 |
| ALG-MEMORY-READ | Memory retrieval | backend/src/debate/memory_hooks.py | empty 時の既定値 | FR-DEBATE-04 / Q1 / Q10 |
| ALG-AFFIRMATION | 肯定フィードバック | backend/src/debate/prompts/affirmation.py | NG-6 検査 fail-safe | FR-DEBATE-09 後段 |
| ALG-GRACEFUL-SHUTDOWN | 80s 綺麗終了 | backend/src/debate/main.py | 80s 経過で必ず session_complete yield | Q11 P1（v3.2）|
| ALG-MOD | 多層モデレーション | backend/src/debate/main.py + Bedrock GR | **3 層で NG 必ず検出**（PBT-08）| FR-DEBATE-07 / Q12 |
| ALG-S3-EXPORT | Memory → S3 | infra（agentcore.Memory.stream_delivery）| Unit-8 から Athena 読込可能 | Q13 P1（v3.2）|

> PBT / Security の具体的なテスト戦略・カバレッジ目標は NFR Requirements / NFR Design ステージで Unit-3 向けに確定する。
