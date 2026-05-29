# Unit-3 Debate — NFR Design Patterns

> Unit-3 Debate の NFR Requirements を **設計パターン** に落とし込んだ成果物。AgentCore Runtime + Memory + Bedrock Haiku 4.5 + 多層モデレーション + Cooldown DDB + S3 Memory Export の構成における、性能 / コスト / 倫理 / 信頼性 / 観測パターンを確定。
>
> 参照: [NFR Requirements](../nfr-requirements/) / [Functional Design](../functional-design/) / [Unit-1 NFR Design Patterns](../../unit-1-platform/nfr-design/nfr-design-patterns.md) / [logical-components.md](./logical-components.md)
>
> 確定方針: NFR-Req（plan v3.4 + NFR Requirements 全項目）+ NFR-Design 採用パターン

---

## 0. パターン一覧

| ID | パターン | 対応 NFR | 適用コンポーネント |
|---|---|---|---|
| PAT-D-PERF-01 | Streaming First-Token Optimization | NFR-PERF-DEBATE-01/02 | AgentCore Runtime + Strands Agent |
| PAT-D-PERF-02 | Two-Stage Timer (lifecycleConfig + graceful shutdown 80s) | NFR-PERF-DEBATE-03/04 / Q11 | Strands Agent main.py |
| PAT-D-PERF-03 | Memory Retrieve Top-K Bound | NFR-PERF-DEBATE-07 | memory_hooks.py |
| PAT-D-PERF-04 | Pure Function Prompt Composition | NFR-PERF-DEBATE-08 | prompts/compose.py |
| PAT-D-COST-01 | Cost-Protective Cooldown Gate | NFR-COST-DEBATE-07 / COOLDOWN-03 | main.py + cooldown.py |
| PAT-D-COST-02 | Mobile Single-Retry on Throttling | NFR-COST-DEBATE-06 / NFR-AVAIL-DEBATE-02 | agentcore-client.ts |
| PAT-D-COST-03 | SSM-driven Model Switch | NFR-COST-DEBATE-01 / Q4 | ssm.py + Strands Agent init |
| PAT-D-COST-04 | DDB Failure Kill Switch (5min Cooldown Bypass) | NFR-AVAIL-DEBATE-04 | main.py + ssm.py |
| PAT-D-ETHICS-01 | 3-Layer Moderation Defense in Depth | NFR-ETHICS-DEBATE-01/02 / Q12 | base prompt + Bedrock Guardrails + callback_handler |
| PAT-D-ETHICS-02 | Affirmation NG-6 Regex Fail-Safe | NFR-ETHICS-DEBATE-01 / AFF-04 | prompts/affirmation.py |
| PAT-D-ETHICS-03 | Outcome-Gated Affirmation | NFR-ETHICS-DEBATE-03 / AFF-01 | main.py action 分岐 |
| PAT-D-RESIL-01 | Memory Retrieve Failure Fail-Open | NFR-AVAIL-DEBATE-03 / MEMORY-* | memory_hooks.py |
| PAT-D-RESIL-02 | Cooldown Natural Expiry + Reset | NFR-PBT-DEBATE-03 / business-rules COOLDOWN-04 | cooldown.py |
| PAT-D-RESIL-03 | Bedrock Guardrails BLOCKED Surface | NFR-ETHICS-DEBATE-04 / Q12 第 2 層 | Bedrock Guardrails + Strands main.py event 変換 |
| PAT-D-OBS-01 | M-1/M-2 Axis-Tagged Telemetry | NFR-OBS-DEBATE-02 / FR-DEBATE-04 | M-13 Telemetry + axis 軸タグ |
| PAT-D-OBS-02 | Bedrock Token EMF Metrics | NFR-OBS-DEBATE-04 | Strands Agent callback |
| PAT-D-OBS-03 | Canary Endpoint Routing | Q17 / NFR-AVAIL-DEBATE-06 | RuntimeEndpoint live + canary |
| PAT-D-SEC-01 | JWT-only actor_id Resolution | SECURITY-08 / NFR-SEC-DEBATE-01 | AgentCore Cognito Authorizer |
| PAT-D-SEC-02 | Memory Namespace Isolation | NFR-SEC-DEBATE-04 / MEMORY-05 | memory_hooks.py |
| PAT-D-SEC-03 | IAM Wildcard 2-Model Pre-Grant | NFR-SEC-DEBATE-07 / M-4 | infra/lib/debate-stack.ts |

---

## 1. 性能パターン（PAT-D-PERF）

### PAT-D-PERF-01 Streaming First-Token Optimization（NFR-PERF-DEBATE-01/02）

**目的**: Bedrock 初回トークン到達 <= 300ms（p95）、UI 提示 <= 3 秒（p95）

**設計**:

- AgentCore Runtime の `agent.stream_async()` で Bedrock Haiku 4.5 を **streaming モード** で呼び出し（同期 invoke は使わない）
- Strands Agent はトークンを受け取った瞬間に `yield event` で Mobile に転送（Runtime 側のバッファリングを最小化）
- Mobile `event-parser.ts` は AsyncIterable をそのまま UI レイヤーに流す（中間バッファなし）
- プロンプト合成は **同期完了後に Bedrock 呼び出し**（Memory retrieve は session_start hook で事前完了）

**フロー**:

```
Mobile invoke → AgentCore Runtime (cognito auth ~10ms) →
  → Strands Agent on_session_start (Memory retrieve ~150-200ms) →
  → compose_debate_prompt（純関数 <=10ms）→
  → Bedrock stream_async（first token target 300ms）→
  → yield event → Mobile UI 反映 →
  目標: 認証 + Memory + プロンプト + Bedrock = 約 470-520ms p95（10 + 200 + 10 + 300）
```

**最適化ポイント**:
- Memory retrieve は `top_k=5` 制限（PAT-D-PERF-03）でレイテンシ抑制
- プロンプト合成は純関数（IO なし）で <= 10ms
- Bedrock コールドスタート対策は AgentCore Runtime 標準（lifecycleConfiguration の microVM 暖機）

---

### PAT-D-PERF-02 Two-Stage Timer（lifecycleConfig + graceful shutdown 80s、Q11）

**目的**: 1 セッション 90 秒厳守 + 論破文の途中切断防止（M-1 体験品質保証）

**二段構造**:

| 経過時間 | 状態 | 動作 |
|---|---|---|
| 0〜80s | normal streaming | Bedrock chunk を通常配信 |
| 80〜90s | **graceful shutdown 起動** | サマリ生成（最大 10s）+ 綺麗な session_complete |
| 90〜120s | hard cutoff | サマリ失敗時の保険、即 session_complete reason='hard_timeout' |
| 120s〜 | microVM 強制停止 | AgentCore Runtime lifecycleConfiguration 発火、Mobile は 410 Gone |

**実装**: Strands Agent ループ内で `elapsed = utcnow() - started_at` をチェック、`>= DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS` で graceful 入り

**サマリ生成プロンプト**: 「ここまでの論破サマリを 1〜2 文で生成。トーンは論理優位ディベート系（敬語、〜じゃないですか / 結局 / 論理的に / データあるんですか？）、未確定の論破軸を含めない」

**fail-safe**: サマリ失敗（10s 超過）でも `session_complete` event は必ず yield（UI ローディング解除を保証）

---

### PAT-D-PERF-03 Memory Retrieve Top-K Bound（NFR-PERF-DEBATE-07 / MEMORY-09）

**目的**: Memory retrieve <= 200ms（p95）、プロンプト爆発防止

**設計**: `memory_client.retrieve_memories(namespace=..., top_k <= 5)` を全箇所で強制
- `/user/debate/{actorId}/`（嗜好）: top_k=5
- `/user/stress/{actorId}/`（ストレス信号）: top_k=3
- `/user/m1m2/{actorId}/`（M-1/M-2 軸抽出、P1）: top_k=3

**ガード**: `business-rules MEMORY-09` で top_k <= 5 を契約化、Lint で `top_k=10` 等の値が出たら fail

---

### PAT-D-PERF-04 Pure Function Prompt Composition（NFR-PERF-DEBATE-08）

**目的**: `compose_debate_prompt` <= 10ms、PBT で純関数性を property 検証

**設計**:

- `compose.py` は **副作用なし**（Memory IO は `memory_hooks.py` の責務）
- 入力 `MemoryContext` は事前完成された値オブジェクト
- 純関数性により: 同一入力 → 同一出力（PBT-03 で検証）、テストが容易、並列実行安全

**property test** (NFR-PBT-DEBATE-01/02):
- `stress_level=mid/high` で必ず `[REWARD]` を含む
- 任意の入力で `len(text) <= 8000`
- `'fact' in axes`、`'psychology' in axes` 必須
- base block が必ず先頭

---

## 2. コストパターン（PAT-D-COST）

### PAT-D-COST-01 Cost-Protective Cooldown Gate（NFR-COST-DEBATE-07）

**目的**: クールダウン中の Bedrock 呼び出しを 0 件にする（コスト保護）

**設計**: `main.py` debate_handler の **手順 4**（`check_cooldown` の直後、Bedrock 呼び出し前）でクールダウン判定:

```
if cd.active:
    yield {"type": "debate.cooldown_triggered", "metadata": {"cooldown_until": ...}}
    return  # ← Bedrock 呼び出し前に return、コスト 0
```

**property test** (NFR-PBT-DEBATE-03 / NFR-COST-DEBATE-07):
- 任意の actor_id で cooldown.active=True ならその後 Bedrock invoke が 0 件

---

### PAT-D-COST-02 Mobile Single-Retry on Throttling（NFR-COST-DEBATE-06）

**目的**: Bedrock Throttling 時のコスト爆発を防ぎつつ UX を保つ

**設計**: Mobile `agentcore-client.ts` で:
- HTTP 429（ThrottlingException）受信時 **1 回のみ即時リトライ**（指数バックオフなし）
- 2 回目失敗で `error event` を yield、UI に「論破モード一時停止中」を表示
- AbortController で接続を閉じる

**Provisioned Throughput は採用しない**（NFR-COST-DEBATE-06）— 月額数百ドルのコスト増を回避、On-Demand + 1 回リトライで MVP / 決勝の規模に十分

---

### PAT-D-COST-03 SSM-driven Model Switch（Q4=A+SSM、NFR-COST-DEBATE-01）

**目的**: Bedrock モデル切替（Haiku → Sonnet）を Stack 再デプロイなしで実現

**設計**:
- SSM Parameter `/yudane/<env>/debate/model-id`（既定 `anthropic.claude-haiku-4-5`）
- Strands Agent の起動時 1 回だけ `boto3.client('ssm').get_parameter()` で取得
- 値変更後 Lambda 再起動（AgentCore Runtime のローリング再起動）で反映
- IAM は **Haiku + Sonnet の 2 ARN ワイルドカード** を先行付与（PAT-D-SEC-03）

**運用**: 決勝後にユーザー数 1000 超 / 論破成功率 < 70% 連続 1 週間で Sonnet 切替検討（B-305 backlog）

---

### PAT-D-COST-04 DDB Failure Kill Switch（NFR-AVAIL-DEBATE-04）

**目的**: DDB Cooldowns 障害時の fail-open がコスト爆発に至るのを防ぐ

**設計**: SSM Parameter `/yudane/<env>/debate/kill-switch`（'enabled' / 'disabled'、既定 'disabled'）

```
on session start:
  try:
      cd_state = check_cooldown(actor_id, now=utcnow())
  except DDBError as e:
      audit_logger.warn("Cooldown DDB error", actor_id=actor_id, error=str(e))
      ddb_error_metric.increment()  # B-12 経由で構造化ログ + Alarm 発火
      if is_kill_switch_enabled(env_name=ENV_NAME):
          # NFR-AVAIL-DEBATE-04: 5 分以上連続障害で運用者が SSM kill-switch を 'enabled' に切替
          yield event(debate.cooldown_triggered, reason='kill_switch')
          return
      # fail-open: プロダクト体験優先（kill-switch 'disabled' のとき）
      cd_state = CooldownDecision(active=False, consecutive_refuses=0)

  if cd_state.active:
      yield event(debate.cooldown_triggered, reason='cooldown_active')
      return
  # 通常の論破フローへ進む
```

**監視**: NFR-SEC-DEBATE-08 のアラート（DDB 障害連続 5 件）が発火したら、運用者が SSM kill-switch を 'enabled' に切替（または自動切替の Lambda を P2 で実装）

---

## 3. 倫理担保パターン（PAT-D-ETHICS）

### PAT-D-ETHICS-01 3-Layer Moderation Defense in Depth（Q12=D）

**目的**: NG-1〜8（特に NG-6 脅迫・罪悪感強要）の滑落を 3 層で防ぐ

**3 層構造**:

| 層 | 実装 | タイミング | 検出対象 |
|---|---|---|---|
| **第 1 層** プロンプトガードレール | `prompts/base.py` 内に NG-1〜8 ディレクティブを静的埋め込み | Bedrock 呼び出し前 | Bedrock がプロンプト指示を尊重して NG 出力を抑制 |
| **第 2 層** Bedrock Guardrails streaming | `bedrock_kwargs.guardrailIdentifier` で Strands Agent に関連付け | Bedrock 出力中 | DENIED_TOPICS（NG-1〜8）を chunk 単位で BLOCKED |
| **第 3 層** 正規表現 callback_handler | `moderation/callback_handler.py` の Strands callback | yield 直前 | `(買わないと.*損)` / `(バカ\|アホ\|無能)` 等のパターン |

**fail-safe**: 第 1 / 第 2 層をすり抜けた chunk も第 3 層で必ず止まる（**MOD-04 / NFR-ETHICS-DEBATE-02**: 100% 検出 property、PBT-08 重点）

**ヒット時の動作**:
- `yield event(moderation_blocked, metadata={layer, pattern, reason})`
- ストリーム終了
- Mobile UI: 「AI が言葉を選び直しています」表示

---

### PAT-D-ETHICS-02 Affirmation NG-6 Regex Fail-Safe（AFF-04）

**目的**: 肯定フィードバックが NG-6 に滑落しない安全装置

**設計**:

```
async def generate_affirmation(actor_id, asin, client_signals, outcome='agreed'):
    message = await bedrock.invoke_model(...)  # 80 token 短文
    if matches_ng6_patterns(message):
        return AffirmationMessage(text=AFFIRMATION_FALLBACK, style=preferred_style)
    return AffirmationMessage(text=message, style=preferred_style)
```

**`AFFIRMATION_FALLBACK`**: 「結局これが正解だったんですよ。論理的に判断したらこうなりますよね。」（論理優位ディベート系トーン、NG-6 リスクゼロ）

---

### PAT-D-ETHICS-03 Outcome-Gated Affirmation（AFF-01）

**目的**: 拒否者（refused / timeout）への肯定強要を 0 件にする

**設計**: `main.py` debate_handler で:
- `action='request_affirmation'` かつ `outcome='agreed'` のときのみ `generate_affirmation` 呼び出し
- それ以外は早期 return + `error event`

**property test** (NFR-PBT-DEBATE-07 派生 + NFR-ETHICS-DEBATE-03):
- `outcome != 'agreed'` で `generate_affirmation` が 0 回呼ばれる

---

## 4. レジリエンスパターン（PAT-D-RESIL）

### PAT-D-RESIL-01 Memory Retrieve Failure Fail-Open（MEMORY-* / NFR-AVAIL-DEBATE-03）

**目的**: AgentCore Memory 障害時にも論破セッションを継続（Day 1 ユーザー = empty Memory も同じ経路）

**設計**:

```
def build_memory_context(actor_id):
    try:
        recent_outcomes = memory_client.retrieve_memories(...)
    except (MemoryServiceError, TimeoutError):
        recent_outcomes = []
        log.warn("Memory retrieve failed, using empty context", actor_id=actor_id)
    
    return MemoryContext(
        recent_debate_outcomes=recent_outcomes,
        preferred_axis='fact' if not recent_outcomes else analyze(recent_outcomes),
        # その他既定値
    )
```

**property test** (NFR-PBT-DEBATE-04): empty MemoryContext で `compose_debate_prompt` が例外を上げない

---

### PAT-D-RESIL-02 Cooldown Natural Expiry + Reset（COOLDOWN-04 / M3-1）

**目的**: クールダウン期限切れ時に自動的に論破再開可能、再カウントは 1 から

**設計** (`cooldown.py`):

```
def increment_refuse_count(actor_id, now):
    state = ddb.get_item(...)
    if state.cooldownUntil and state.cooldownUntil <= now:
        # 自然解除後の最初の拒否 → 1 にリセット
        ddb.update_item(
            UpdateExpression="SET consecutiveRefuses = :one, lastRefuseAt = :now REMOVE cooldownUntil",
            ExpressionAttributeValues={":one": 1, ":now": now}
        )
        return CooldownState(consecutive_refuses=1, ...)
    
    # 通常の +1 増分
    result = ddb.update_item(UpdateExpression="ADD consecutiveRefuses :one ...")
    
    if result.consecutiveRefuses == COOLDOWN_TRIGGER_THRESHOLD:
        # 3 到達でクールダウン発動
        ddb.update_item(
            UpdateExpression="SET cooldownUntil = :until, ttl = :ttl",
            ExpressionAttributeValues={":until": now + 3h, ":ttl": now + 30d}
        )
    return result
```

**property test** (NFR-PBT-DEBATE-03):
- `consecutiveRefuses == 3` 到達で必ず `cooldownUntil = now + 3h` SET
- 自然解除後の拒否で `consecutiveRefuses == 1` リセット

---

### PAT-D-RESIL-03 Bedrock Guardrails BLOCKED Surface（Q12 第 2 層）

**目的**: Bedrock 側で NG が検出されたとき Mobile に正しく伝える

**設計**: Strands Agent の `bedrock_kwargs.guardrailIdentifier` で Guardrails を関連付け、`outputAssessments` で `BLOCKED` を受信した chunk を:

```
async for event in agent.stream_async(composed.text):
    if event.type == 'guardrail_blocked':
        yield event_with_marker('moderation_blocked', metadata={
            'reason': 'guardrails_blocked',
            'topic': event.metadata.get('blocked_topic'),
        })
        return
    yield event
```

**Bedrock Guardrails の設定** (NFR-SEC-DEBATE / tech-stack §3.1):
- DENIED_TOPICS = NG-1〜8 の 8 トピック
- contentPolicy = HATE / VIOLENCE / SEXUAL / INSULTS = HIGH
- streaming 対応有効

---

## 5. 観測パターン（PAT-D-OBS）

### PAT-D-OBS-01 M-1/M-2 Axis-Tagged Telemetry（NFR-OBS-DEBATE-02、北極星指標）

**目的**: M-1（事実 + 心理）/ M-2（ご褒美）軸別の翻意率を計測（YUDANE のダメ化メカニズムの効果計測）

**設計**:

```
on debate.agreed event:
    M-13 Telemetry.track('debate.agreed', {
        'axis': detected_axis,  # 'fact' | 'psychology' | 'reward'
        'turn': turn_number,
        'stress_level': stress_level,
        # actor_id / asin は次元に入れない（高カーディナリティ防止、NFR-OBS-02）
    })
```

**Mobile event-parser** が Strands chunk 内の `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` セクションマーカーを軸として抽出 → Telemetry 送信時に `axis` フィールドに付与

**集計**: CloudWatch Logs Insights / Athena で `axis` 別に集計、北極星指標として CloudWatch Dashboard に表示

---

### PAT-D-OBS-02 Bedrock Token EMF Metrics（NFR-OBS-DEBATE-04）

**目的**: Bedrock token 消費を継続計測しコスト傾向を把握

**設計**: Strands Agent の callback で各 invoke 後に Lambda Powertools の `metrics.add_metric()` で:
- `debate.bedrock.input_tokens`
- `debate.bedrock.output_tokens`
- `debate.bedrock.invocation_count{model_id}`

EMF 形式で CloudWatch Metrics に push、Cost Explorer と突合せ可能

---

### PAT-D-OBS-03 Canary Endpoint Routing（Q17）

**目的**: 決勝直前のカナリアリリース対応

**設計**:

```
[CDK]
RuntimeEndpoint × 2:
  - live  (SSM /yudane/<env>/debate/runtime-endpoint-live-arn)
  - canary (SSM /yudane/<env>/debate/runtime-endpoint-canary-arn)

[Mobile]
通常: SSM live-arn を取得 → InvokeAgentRuntime(qualifier='live')
カナリア: SSM canary-arn を取得 → InvokeAgentRuntime(qualifier='canary')
```

**運用** (NFR-AVAIL-DEBATE-06):
- 6/25（決勝前日）に staging Stack の canary endpoint で 30 分カナリア
- OK なら prd Stack の canary endpoint で同様に 30 分
- 失敗したら roll back（live endpoint をそのまま使い続ける）

---

## 6. セキュリティパターン（PAT-D-SEC）

### PAT-D-SEC-01 JWT-only actor_id Resolution（SECURITY-08）

**目的**: クライアント送信値を信用せず、actor_id は Cognito JWT.sub のみを正とする

**設計**:

```
@app.entrypoint
async def debate_handler(payload: dict, context):
    # context は AgentCore Runtime が Cognito Authorizer 経由で構築
    actor_id = context.user.sub  # JWT.sub を直接取得
    if not actor_id:
        yield error_event('auth.unauthenticated')
        return
    
    # payload の actor_id フィールドは無視
    invocation = DebateInvocationPayload.model_validate(payload)
    # ... 以降 actor_id を使う
```

**property test**: payload に偽の `actor_id` を入れても context 由来の actor_id が使われる

---

### PAT-D-SEC-02 Memory Namespace Isolation（NFR-SEC-DEBATE-04 / MEMORY-05）

**目的**: ユーザー間のデータ漏洩を Memory namespace で防ぐ

**設計**: 全 namespace に `{actorId}` を含める:
- `/user/debate/{actorId}/`
- `/user/stress/{actorId}/`
- `/user/m1m2/{actorId}/`

**横断 retrieval 禁止**: コードレベルで `namespace = f'/user/.../{actor_id}/'` の f-string で生成、`{actor_id}` を抜いた namespace（`/user/debate/all/` 等）は CI Lint で検出 + fail

**property test**: 異なる actor_id で `retrieve_memories` した結果に他者のデータが混入しないこと（Hypothesis で ブラックボックステスト）

---

### PAT-D-SEC-03 IAM Wildcard 2-Model Pre-Grant（NFR-SEC-DEBATE-07 / M-4）

**目的**: SSM model_id 切替時の AccessDenied を予防

**設計** (CDK):

```typescript
debateRuntime.addToRolePolicy(new iam.PolicyStatement({
  actions: ['bedrock:InvokeModelWithResponseStream', 'bedrock:InvokeModel'],
  resources: [
    `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-haiku-4-5`,
    `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-6`,
  ],
}));
```

Sonnet 4.6 利用は B-305 backlog だが IAM だけ先行付与することで、SSM 値変更だけで切替可能

---

## 7. 失敗モードと対応パターン（FMEA）

| 失敗モード | 検出 | 対応パターン |
|---|---|---|
| Bedrock Throttling | HTTP 429 | PAT-D-COST-02 Mobile 1 回リトライ |
| AgentCore Runtime コールドスタート | レイテンシ > 2s | NFR-PERF-DEBATE-05、Provisioned 不採用 |
| Memory retrieve タイムアウト | TimeoutError | PAT-D-RESIL-01 fail-open（empty MemoryContext）|
| DDB Cooldowns 障害 | get_item / update_item 例外 | PAT-D-COST-04 fail-open + kill switch |
| Bedrock 完全障害 | 5xx 連続 | NFR-AVAIL-DEBATE-07 「論破モード一時停止中」UI |
| Guardrails 誤検出 | BLOCKED 率 > 1% | NFR-SEC-DEBATE-08 Alarm + プロンプト見直し |
| Memory namespace 漏洩 | 単体テスト / Lint | PAT-D-SEC-02 Lint で f-string チェック |
| Sonnet 切替時 AccessDenied | N/A（IAM 2 ARN 先行付与で予防済）| PAT-D-SEC-03（事前ミティゲーション、検出は CloudWatch Errors 0 件であることを確認）|
| 90s タイマー超過 | elapsed > 90s | PAT-D-PERF-02 二段タイマー（graceful + hard）|
| 拒否者への肯定強要 | コードレビュー | PAT-D-ETHICS-03 outcome gate |

---

## 8. パターン適用の優先度（マイルストーン別）

### P0（5/30 暫定 → 6/6 完了、E2E-01 動作必達）
- PAT-D-PERF-01 Streaming First-Token
- PAT-D-PERF-04 Pure Function Prompt
- PAT-D-COST-01 Cooldown Gate
- PAT-D-COST-03 SSM model-id Switch
- PAT-D-COST-04 DDB Kill Switch（NFR-AVAIL-DEBATE-04 と整合、kill-switch SSM Parameter 出力 + Bedrock コストアラート併用は P0）
- PAT-D-ETHICS-01 第 1 層プロンプトガードレール
- PAT-D-ETHICS-03 Outcome-Gated Affirmation
- PAT-D-RESIL-01 Memory fail-open
- PAT-D-RESIL-02 Cooldown reset
- PAT-D-OBS-01 Axis-Tagged Telemetry（基本）
- PAT-D-SEC-01 JWT-only actor_id
- PAT-D-SEC-02 Memory Namespace Isolation
- PAT-D-SEC-03 IAM Wildcard 2-Model

### P1（6/15 決勝 Readiness）
- PAT-D-PERF-02 Two-Stage Timer 80s graceful
- PAT-D-PERF-03 Memory Retrieve Top-K Bound
- PAT-D-COST-02 Throttling Single-Retry
- PAT-D-ETHICS-01 第 2 / 第 3 層モデレーション完成
- PAT-D-ETHICS-02 Affirmation Fail-Safe
- PAT-D-RESIL-03 Bedrock Guardrails BLOCKED Surface
- PAT-D-OBS-02 Bedrock Token EMF
- PAT-D-OBS-03 Canary Endpoint Routing

### P2（決勝後）
- DDB 障害自動 kill switch 切替 Lambda
- B-304 AgentCore Online Evaluation
- B-306 custom Strategy プロンプト改善

---

## 9. NFR Requirements との対応サマリ

| NFR Requirements | 実現パターン |
|---|---|
| NFR-PERF-DEBATE-01〜05 | PAT-D-PERF-01 / 02 |
| NFR-PERF-DEBATE-06〜10 | PAT-D-PERF-03 / 04 + Cooldown DDB On-Demand |
| NFR-COST-DEBATE-01〜08 | PAT-D-COST-01 / 02 / 03 / 04 |
| NFR-ETHICS-DEBATE-01〜10 | PAT-D-ETHICS-01 / 02 / 03 + PAT-D-RESIL-03 |
| NFR-AVAIL-DEBATE-02〜07 | PAT-D-RESIL-01 / 02 / 03 + PAT-D-COST-04 |
| NFR-OBS-DEBATE-01〜12 | PAT-D-OBS-01 / 02 / 03 |
| NFR-SEC-DEBATE-01〜11 | PAT-D-SEC-01 / 02 / 03 + Unit-1 継承 |
| NFR-PBT-DEBATE-01〜10 | 各パターンの property test で検証 |
| NFR-COV-DEBATE-01〜10 | 各パターン適用ファイルで Coverage 目標達成 |
| NFR-A11Y-DEBATE-01〜05 | Mobile `M-04 DebateScreen.tsx` 側で対応（Outside-In TDD で本 Unit-3 LC スコープ外、Mobile feature 直接実装）|
