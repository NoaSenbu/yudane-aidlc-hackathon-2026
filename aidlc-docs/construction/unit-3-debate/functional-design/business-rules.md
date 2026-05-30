# Unit-3 Debate — Business Rules

> Unit-3 Debate の **ルール・定数・制約** を一覧化。実装・テストの判定基準となる。
>
> 参照: [domain-entities.md](./domain-entities.md) / [business-logic-model.md](./business-logic-model.md) / [strands-agent-design.md](./strands-agent-design.md)
>
> 確定方針（[functional-design-plan.md v3.3](./functional-design-plan.md#6-decision-recordv33-確定2026-05-29)）: Q1=C / Q2=C / Q3=A / Q4=A+SSM / Q5=A / Q6=A / Q7=A / Q8=B / Q9=D / Q10=B / Q11=A+graceful shutdown 80s / Q12=D 多層 / Q13=D+S3 / Q14=A PBT 全面 / Q15=A / Q16=B / Q17=B live+canary

---

## 1. 論破セッションルール（DEBATE-* / FR-DEBATE-01〜09）

| ID | ルール |
|---|---|
| DEBATE-01 | 論破セッションは 3 トリガーで起動: (a) リール「買わない」タップ、(b) カート介入通知タップ、(c) 商品ページ長時間滞留（FR-DEBATE-01）|
| DEBATE-02 | 1 セッションあたり最大 90 秒で自動終了（FR-DEBATE-06、AgentCore Runtime `lifecycleConfiguration.maxLifetimeSeconds: 120` の 90s 超過時に Strands Agent 内部チェックで停止）|
| DEBATE-03 | 80s 経過時に graceful shutdown フックが発火し、サマリ生成 + 綺麗な session_complete を返す（v3.2 Q11、L1 機能面の品質保証）|
| DEBATE-04 | Bedrock 初回トークン到達 300ms 以下、ストリーミング配信で初回反論を 3 秒以内に提示（FR-DEBATE-03）|
| DEBATE-05 | コピートーンは **論理優位ディベート系（Unit-3 のみ v3.4 で再定義、要件書 §2.2 友達系を Unit-3 内で再定義）**。敬語ベース、論理で黙らせるスタイル。「悠介さん」と呼ぶ（さん付け）。**採用言い回し**: 「〜じゃないですか？」「結局〜」「要するに〜」「論理的に考えて〜」「合理的に判断したら〜」「客観的に見て〜」「事実として〜」「データあるんですか？」「根拠あるんですか？」「ソースあります？」「それってあなたの感想ですよね？」「コスト的に損じゃないですか？」「時間の無駄じゃないですか？」「ROI 的に〜」「お疲れ様です」「いい判断ですね」。**絶対禁止**: 侮辱語（バカ / アホ / 無能 / センスない 等）/ 人格決めつけ / 罪悪感強要（買わないと損 / ダメ）/ 勝ち誇り（はい論破 / 議論終わり）/ 見下し（分かりますか？/ 悠介さんレベルでも）/ 強制（買え / 買うべき）。詳細は [prompt-composition.md §2 base block](../../unit-3-debate/functional-design/prompt-composition.md) 参照 |
| DEBATE-06 | 論破セッション中に外部 API（Creators / Calendar 等）の同期呼び出しを行わない（90s タイマー侵食を防止）。必要な情報は Memory + Profile キャッシュから事前注入 |
| DEBATE-07 | `actor_id` は payload を信用せず、AgentCore Runtime Cognito Authorizer が解決した JWT.sub のみを正とする（SECURITY-08 / Q5）|

### 設定値（DEBATE-CONFIG）

| 定数 | 値 | 意味 | 出典 |
|---|---|---|---|
| `DEBATE_MAX_DURATION_SECONDS` | 90 | 1 セッション上限（FR-DEBATE-06）| Q11 |
| `DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS` | 80 | graceful shutdown 発火タイミング | v3.2 Q11 |
| `DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS` | 10 | サマリ生成の最大待機（80→90s 内）| v3.2 Q11 |
| `RUNTIME_IDLE_TIMEOUT_SECONDS` | 120 | AgentCore Runtime microVM idle 上限 | v3.2 Q11 |
| `RUNTIME_MAX_LIFETIME_SECONDS` | 120 | AgentCore Runtime microVM 強制終了 | v3.2 Q11 |
| `STREAM_FIRST_TOKEN_TARGET_MS` | 300 | 初回トークン到達目標（FR-DEBATE-03）| Q3 |

---

## 2. クールダウン規則（COOLDOWN-* / FR-DEBATE-05、Q2=C）

| ID | ルール |
|---|---|
| COOLDOWN-01 | カウントは **ユーザー横断**（同一 actor_id）。session 単位ではカウントしない |
| COOLDOWN-02 | 連続拒否 3 回到達で `cooldownUntil = now + 3h` を設定（business-logic ALG-COOLDOWN-INC、PBT-03 不変条件）|
| COOLDOWN-03 | クールダウン中は新規 InvokeAgentRuntime に対して `debate.cooldown_triggered` event を yield + Bedrock 呼び出し抑止（コスト保護）|
| COOLDOWN-04 | `cooldownUntil` 期限切れ時に自動的に「自然解除」扱い。`consecutiveRefuses` は次回拒否時に **1 にリセット**（ALG-COOLDOWN-INC で `cooldownUntil <= now` を検知して `SET consecutiveRefuses = 1 REMOVE cooldownUntil`、v3.3 M3-1 修正）|
| COOLDOWN-05 | DDB レコードの TTL 属性は 30 日後の UNIX timestamp（COOLDOWN-CONFIG `COOLDOWN_TTL_SECONDS = 30 * 86400`）|
| COOLDOWN-06 | 手動解除は Unit-7 Safeguard `PATCH /v1/safeguard` の `cooldownReleased` フラグで実施（Q9=D、Mobile が直接 Unit-7 に呼び出し、Unit-3 経由不要）|
| COOLDOWN-07 | 解除時に B-12 AuditLogger で `releaseReason` を構造化ログ出力（NG-6 罪悪感強要にならない範囲で）|
| COOLDOWN-08 | クールダウン状態は AgentCore Memory に保存しない（短時間 / 高頻度 state、Memory 不向き）。DDB `yudane-debate-<env>-cooldowns` 唯一の自前テーブル |

### 設定値（COOLDOWN-CONFIG）

| 定数 | 値 | 意味 |
|---|---|---|
| `COOLDOWN_TRIGGER_THRESHOLD` | 3 | 連続拒否でクールダウン開始する回数 |
| `COOLDOWN_DURATION_SECONDS` | 10800（=3h）| クールダウン期間 |
| `COOLDOWN_TTL_SECONDS` | 2592000（=30d）| DDB レコード自動削除 TTL |

---

## 3. プロンプト合成ルール（PROMPT-* / FR-DEBATE-02 / FR-DEBATE-09）

| ID | ルール |
|---|---|
| PROMPT-01 | プロンプトは 4 ブロック構造: `base` → `m1_fact_axis` → `m1_psychology_axis` → （条件付き）`m2_reward_axis`（business-logic ALG-PROMPT 順序固定）|
| PROMPT-02 | **`stress_level in ('mid', 'high')` の場合、必ず `m2_reward_axis` を含める**（FR-DEBATE-09 不変条件、PBT-03 / PBT-08 重点）|
| PROMPT-03 | M-2 軸併走時のコピー型: 「今日のイライラ、{商品}で明日リセットしようぜ」型。直接的な「ストレス解消」表現を避け、暗喩的に示す |
| PROMPT-04 | NG-6（脅迫・罪悪感強要）に該当する表現はプロンプト指示文（base block）で明示的に禁止。「買わないとあなたはダメだ」「買わないと損する」は禁止 |
| PROMPT-05 | M-1 事実軸の論理は 3 系統のいずれか以上を含む: (a) 時給換算 / (b) 在庫希少性 / (c) カレンダー予定との整合（FR-DEBATE-02）|
| PROMPT-06 | M-1 心理軸は Memory `userPreference` から取得した `preferred_axis` を起点に組み立て（個別最適化、FR-DEBATE-04）|
| PROMPT-07 | プロンプト合成テキストは概算 8000 token 以下（日本語 1 文字 ≒ 1〜2 token として 4000〜5000 文字相当、Bedrock token 上限 200K の余裕、business-rules ALG-PROMPT 不変条件）|
| PROMPT-08 | セクションマーカー `[FACT]` / `[PSYCHOLOGY]` / `[REWARD]` を出力に含める（Mobile 側 event-parser.ts の軸判別を補助）|
| PROMPT-09 | `compose_debate_prompt()` は純関数（同一入力 → 同一出力、副作用なし）。Memory retrieve は呼び出し側で実施 |
| PROMPT-10 | プロンプトテンプレートの SSOT は `backend/src/debate/prompts/` 配下（Q7=A、SSM / DDB 不採用）。決勝後の改善は B-306 backlog で扱う |

### 設定値（PROMPT-CONFIG）

| 定数 | 値 | 意味 |
|---|---|---|
| `PROMPT_MAX_LENGTH_CHARS` | 8000 | 合成後プロンプトの上限 |
| `PROMPT_DEFAULT_PREFERRED_AXIS` | 'fact' | 初回ユーザー（Memory empty）の既定軸 |
| `PROMPT_HOURLY_WAGE_FALLBACK_YEN` | 2500 | profile 未設定時の時給換算既定値（IT 系会社員平均）|

---

## 4. ストレス推定ルール（STRESS-* / FR-DEBATE-09 / Q8=B）

| ID | ルール |
|---|---|
| STRESS-01 | 戻り値は **必ず `'low' | 'mid' | 'high'` の 3 種**（business-logic ALG-STRESS 不変条件、PBT-07 重点）|
| STRESS-02 | 軽量ヒューリスティック + Memory semantic Strategy retrieval の併用（Q8=B）|
| STRESS-03 | スコア配点: 深夜帯（23-04時）= +2、残業帯（18-23時）= +1、Memory 'high' signals = +1〜+2、クライアント信号（cart_intercepts >= 3、recent_refuses >= 1、late_night_signin）= 各 +1 |
| STRESS-04 | Memory retrieve が失敗・空でもスコアを 0 として動作（Day 1 から動作可能、business-rules ALG-STRESS）|
| STRESS-05 | スコアレベル変換: `score >= 4` → high / `score >= 2` → mid / それ以外 → low |
| STRESS-06 | ストレス推定の結果は M-13 Telemetry に `debate.stress_estimated{level}` として送信（運用観察用、PII なし）|

---

## 5. Memory 連携ルール（MEMORY-* / Q1=C / Q10=B / Q16=B）

| ID | ルール |
|---|---|
| MEMORY-01 | AgentCore Memory リソースは `yudane_debate_<env>_memory`（命名規約 `a-zA-Z0-9_` のみ、ハイフン不可）|
| MEMORY-02 | `expirationDuration: 90 日` 単一値（events + strategy records 共通の生存期間、v3.3 で C-2 修正）|
| MEMORY-03 | 90 日超のデータは `streamDeliveryResources` で S3 に並行書き出し（Q13 D + S3 export、v3.2 P1）。S3 Lifecycle で 365 日保全 |
| MEMORY-04 | Strategy 構成: P0 = 組み込み 2 種（`userPreferenceMemoryStrategy(name="debate_outcomes")` + `semanticMemoryStrategy(name="stress_signals")`）/ P1 = + custom 1 種（`customMemoryStrategy(name="m1_m2_axis_extractor")`）|
| MEMORY-05 | Namespace 規則: `/user/debate/{actorId}/`（嗜好）/ `/user/stress/{actorId}/`（ストレス信号）/ `/user/m1m2/{actorId}/`（M-1/M-2 軸抽出、P1）|
| MEMORY-06 | `actor_id` は Cognito JWT.sub。payload に含まれる `actor_id` は無視（SECURITY-08）|
| MEMORY-07 | event_metadata に保存する PII は禁止。`axis` / `outcome` / `turn` / `stress_level` / `asin` のみ（PII-09 と整合、ASIN は PII でなく商品 ID）|
| MEMORY-08 | FR-AUTH-06 アカウント削除時、Unit-7 のバッチが `delete_all_long_term_memories_in_namespace(namespace=f"/user/.../{actor_id}/")` を呼び、S3 export bucket の `s3://.../<actorId>/` prefix も削除する（v3.3 修正）|
| MEMORY-09 | Memory retrieve top_k <= 5（プロンプト爆発防止）|
| MEMORY-10 | Memory への書き込みは Strands Agent の `MemoryHook` で自動化、entrypoint 側で個別呼び出ししない（business-logic ALG-MEMORY-WRITE）|

---

## 6. 出力モデレーションルール（MOD-* / FR-DEBATE-07 / Q12=D 多層）

| ID | ルール |
|---|---|
| MOD-01 | **3 層多層防御**: (1) プロンプトガードレール（base block 内 NG-1〜8 指示文、P0）/ (2) Bedrock Guardrails streaming（DENIED_TOPICS = NG-1〜8、P1）/ (3) 正規表現検査（callback_handler、P1）|
| MOD-02 | 第 3 層（正規表現）の判定は decisive: ヒットしたら必ずストリーム終了 + `moderation_blocked` event を yield |
| MOD-03 | NG-6（脅迫・罪悪感強要）+ NG-3（侮辱・人格攻撃）の正規表現パターン: <br>**罪悪感強要**: `(買わないと.*損)`, `(買わないと.*ダメ)`, `(買わない.*罰)`, `(買わない.*後悔)`, `(買わない.*おかしい)`, `(買え$)`, `(買うべき)` <br>**侮辱・侮蔑語**: `(バカ\|アホ\|無能\|頭.*悪い\|センス.*ない\|常識.*ない\|能力.*低い)` <br>**勝ち誇り型**: `(はい論破\|論破完了\|議論終わり\|反論できない\|論破できます)` <br>**過度な見下し**: `(理解できますか\|悠介さんレベル\|分かりますか[？?])` <br>v3.4 論理優位ディベート系トーン採用に伴い、**「これってダメじゃないですか？」型の疑問文に誤マッチしないよう曖昧パターン `(.*じゃないですか.*ダメ)` は採用しない**（NM3-1 / NC4-2 修正）。業務ルールで継続更新、`backend/src/debate/moderation/ng_patterns.py` |
| MOD-04 | 任意の出力で 3 層のうち少なくとも 1 層が NG-1〜8 を必ず検出する（PBT-08 重点 property）|
| MOD-05 | 第 1 / 第 2 層のすり抜けがあっても第 3 層で確実に止める（fail-safe）|
| MOD-06 | 肯定フィードバック（ALG-AFFIRMATION）も MOD-03 の NG-6 正規表現検査を経由。fallback 文言は「今日もいい選択だったね。明日の自分、ちょっと機嫌いいはず」|
| MOD-07 | Bedrock Guardrails の `outputAssessments` は `BLOCKED` のみ Strands に通知、`NONE` は素通し（過敏な遮断を回避）|

### 6.1 肯定フィードバック規則（AFF-* / FR-DEBATE-09 後段、v3.3 C3-3 で新設）

| ID | ルール |
|---|---|
| AFF-01 | 肯定フィードバックは翻意（`outcome='agreed'`）のときのみ発火。拒否（refused）/ タイムアウト（timeout）では発火しない |
| AFF-02 | 起動経路は AgentCore Runtime entrypoint への 2 回目呼び出し（`action='request_affirmation'`、domain-entities §2.1）|
| AFF-03 | 生成モデルは Bedrock Haiku 4.5（非ストリーミング、`max_tokens=80`、低 cost）|
| AFF-04 | NG-6 正規表現検査（MOD-03）でヒットしたら `AFFIRMATION_FALLBACK` 文言に置換（fail-safe）|
| AFF-05 | スタイルは Memory userPreference Strategy から取得した `preferred_affirmation_style`（`casual` / `cool` / `caring`、既定 `casual`）|
| AFF-06 | Mobile 側で **トースト or プッシュ通知** として表示（M-04 DebateScreen の遷移後 1.2s タイマー、または OS プッシュ）|

---

## 7. 認証・認可ルール（AUTHZ-* / Q5=A / Q6=A）

| ID | ルール |
|---|---|
| AUTHZ-01 | AgentCore Runtime に Cognito Authorizer を直接設定（`agentcore.RuntimeAuthorizerConfiguration.cognito()`、Q5=A）|
| AUTHZ-02 | `userPoolId` / `userPoolClientId` は Unit-1 main の SSM Parameter から参照（`/yudane/<env>/platform/userpool-id` / `userpool-client-id`、v3.3 で実コード `infra/lib/platform-stack.ts:138` 確認済）|
| AUTHZ-03 | Network Configuration: Public Network（Q6=A、AgentCore Runtime デフォルト）|
| AUTHZ-04 | Bedrock InvokeModelWithResponseStream / InvokeModel 権限を Runtime IAM Role に付与（CDK `runtime.grantInvokeBedrockModel`）|
| AUTHZ-05 | IAM Bedrock 対象 ARN は **Haiku 4.5 + Sonnet 4.6 のワイルドカード 2 ARN** を先行付与（v3.3 M-4、Q4 SSM 切替時の AccessDenied 防止）|
| AUTHZ-06 | Memory R/W 権限: `bedrock-agentcore:CreateEvent / GetLastKTurns / RetrieveMemories / DeleteAllLongTermMemoriesInNamespace`（Unit-7 アカウント削除と整合）|
| AUTHZ-07 | DDB Cooldowns R/W 権限: `dynamodb:GetItem / UpdateItem`（PutItem は使わない、UpdateItem のみで Upsert）|
| AUTHZ-08 | S3 PutObject 権限は `agentcore.Memory.streamDeliveryResources` 設定で自動付与（Memory が S3 に書き込むため）|
| AUTHZ-09 | SSM `GetParameter` 権限: `/yudane/<env>/debate/model-id` のみ（model-id 切替用、Q4=A+SSM）|

---

## 8. ストリーミング配信ルール（STREAM-* / Q3=A）

| ID | ルール |
|---|---|
| STREAM-01 | Strands Agent の `agent.stream_async()` 出力をそのまま `yield`（YUDANE 独自イベント形式への変換は行わない、Q3=A）|
| STREAM-02 | Mobile 側 `event-parser.ts` で `event-source-parser` パッケージを用いて Strands chunk → UI イベント（token / turn_complete / session_complete / error / moderation_blocked / graceful_shutdown_initiated / summary）を変換 |
| STREAM-03 | `runtimeSessionId = f"{session_id}_{actor_id}"`（ULID 26 文字 + "_" + Cognito sub UUID 36 文字 = 63 文字、AgentCore Runtime 制約 33-256 を満たす、v3.3 M6-1 修正で 3 文書統一）|
| STREAM-04 | ストリーム接続断時はリトライしない（重複配信防止、PII / 課金リスク）|
| STREAM-05 | Mobile 側で AbortController を保持し、画面離脱時に接続を閉じる（コスト保護）|
| STREAM-06 | endsAt = sessionStartedAt + 90s を Mobile が計算（NTP 同期前提）。サーバー権威タイマーは AgentCore Runtime の lifecycleConfiguration |
| STREAM-07 | `qualifier` は環境ごとに `'live'` を既定使用（v3.3 M-5）。決勝直前のカナリアリリース時のみ `'canary'` 切替 |

---

## 9. RuntimeEndpoint 環境戦略ルール（ENDPOINT-* / Q17=B / v3.3 M-5）

| ID | ルール |
|---|---|
| ENDPOINT-01 | 環境分離は **Stack 単位**（`debate-dev-stack` / `debate-staging-stack` / `debate-prd-stack`）|
| ENDPOINT-02 | 各 Stack 内に `live` + `canary` の 2 RuntimeEndpoint を作成 |
| ENDPOINT-03 | `live` endpoint は通常運用、SSM `/yudane/<env>/debate/runtime-endpoint-live-arn` で他 Backend Unit に公開（Mobile は EAS Build 時の `EXPO_PUBLIC_*` 環境変数経由で参照、4IDC-1 修正）|
| ENDPOINT-04 | `canary` endpoint は決勝直前のカナリアリリース / プロンプト A/B テスト用、SSM `/yudane/<env>/debate/runtime-endpoint-canary-arn` で他 Backend Unit に公開（Mobile は canary build に `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_CANARY_ARN` として埋め込み、4IDC-1 修正）|
| ENDPOINT-05 | dev / staging endpoint の Auto-Pause は B-307 backlog（決勝後にコスト最適化）|
| ENDPOINT-06 | Mobile は **EAS Build 時に SSM `live-arn` の値を環境変数 `EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN` として埋め込み**、ランタイムでは環境変数から取得して `qualifier: 'live'` で呼び出す（4IDC-1 修正、Cognito Identity Pool 不採用のため Mobile は SSM API 直接呼び出し不可）。staging Stack で A/B テスト疎通確認後、prd Stack の canary endpoint で 6/25 に 30 分カナリア実施 |
| ENDPOINT-07 | 決勝デモ時（6/26）は prd Stack の `live` endpoint を使用 |

---

## 10. SSM Parameter 規約（SSM-* / Q4=A+SSM、v3.3 C-5）

| ID | ルール |
|---|---|
| SSM-01 | Unit-3 の SSM 出力は 8 個: `runtime-arn` / `memory-id` / `runtime-endpoint-live-arn` / `runtime-endpoint-canary-arn`（P1 で追加）/ `model-id` / `memory-export-bucket-arn`（P1 で追加）/ `cooldowns-table-arn` / `kill-switch`（v3.3 NC2-2 で追加）|
| SSM-02 | Path prefix: `/yudane/<env>/debate/<param-name>`（shared-infrastructure.md §2 命名規約準拠）|
| SSM-03 | `model-id` の既定値: `anthropic.claude-haiku-4-5`（Q4=A）|
| SSM-04 | `model-id` の SSM 値変更はランタイム再起動で反映（コールドスタート時に取得、Lambda 起動 1 回のみ）|
| SSM-05 | 他 Unit から参照する場合は `ssm.StringParameter.valueForStringParameter()` で読み取り（Stack 跨ぎ）|

---

## 11. PBT カバレッジ規約（UNIT3-PBT-* / Q14=A、v3.3 NC-4 修正で番号体系を Extension PBT-* と区別）

> **番号体系の区別**:
> - **UNIT3-PBT-01〜06**: 本セクションの Unit-3 ローカル規約（カバレッジ運用）
> - **Extension PBT-01〜10**: プロジェクト全体規約（[property-based-testing.md](../../../../.kiro/aws-aidlc-rule-details/extensions/testing/property-based/property-based-testing.md)）
> - **NFR-PBT-DEBATE-01〜10**: 個別 property 定義（[nfr-requirements.md §6](../nfr-requirements/nfr-requirements.md#6-テスタビリティ要件nfr-pbt-debateq14a-pbt-全面)）
>
> 他セクションから「PBT-XX」と参照されている箇所（COOLDOWN-02 の「PBT-03 不変条件」/ PROMPT-02 の「PBT-03 / PBT-08 重点」等）は **Extension PBT** の意味（PBT-03 = Invariant、PBT-08 = Shrinking）。

| ID | ルール |
|---|---|
| UNIT3-PBT-01 | PBT 全面適用（v3.2 Q14=A）。重点 5 関数 + 5 統合点 = 計 10 property を `backend/tests/debate/property/` に配置 |
| UNIT3-PBT-02 | 重点 5 関数: `estimate_stress_level()` / `increment_refuse_count()` / `compose_debate_prompt()` / `memory_event_round_trip()`（Memory create_event ↔ get_last_k_turns）/ `agentcore_payload_round_trip()`（InvokeAgentRuntime payload serialize ↔ Strands deserialize）|
| UNIT3-PBT-03 | 統合点 5: `compose_debate_prompt` 全体 / `memory_hooks.MemoryHook` 統合 / `stress.estimate_stress_level` 統合 / Mobile `event-parser.ts` / Mobile `agentcore-client.ts` |
| UNIT3-PBT-04 | Hypothesis（Python）+ fast-check（TypeScript）併用 |
| UNIT3-PBT-05 | Coverage 目標: Line 80%+ / Branch 70%+（[tech.md §6](../../../../.kiro/steering/tech.md) 準拠）。Unit-3 では Coverage 85% を目標 |
| UNIT3-PBT-06 | Extension PBT-01〜10（`.kiro/aws-aidlc-rule-details/extensions/testing/property-based/property-based-testing.md`）への適合性を CI で検証 |

---

## 12. 設定値カタログ（チューニング可能パラメータ、v3.3 確定）

| パラメータ | 既定値 | 所属 | 備考 |
|---|---|---|---|
| `DEBATE_MAX_DURATION_SECONDS` | 90 | DEBATE-CONFIG | FR-DEBATE-06、変更は破壊的影響あり |
| `DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS` | 80 | DEBATE-CONFIG | v3.2 Q11、L1 機能面の品質保証 |
| `DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS` | 10 | DEBATE-CONFIG | サマリ生成の上限 |
| `RUNTIME_IDLE_TIMEOUT_SECONDS` | 120 | DEBATE-CONFIG | AgentCore lifecycleConfiguration |
| `RUNTIME_MAX_LIFETIME_SECONDS` | 120 | DEBATE-CONFIG | 同上 |
| `STREAM_FIRST_TOKEN_TARGET_MS` | 300 | STREAM-* | FR-DEBATE-03 SLI |
| `COOLDOWN_TRIGGER_THRESHOLD` | 3 | COOLDOWN-CONFIG | FR-DEBATE-05 |
| `COOLDOWN_DURATION_SECONDS` | 10800（=3h）| COOLDOWN-CONFIG | Q2=C |
| `COOLDOWN_TTL_SECONDS` | 2592000（=30d）| COOLDOWN-CONFIG | DDB レコード自動削除 |
| `MEMORY_EXPIRATION_DAYS` | 90 | MEMORY-* | events + strategy records 共通 |
| `S3_LIFECYCLE_DELETE_DAYS` | 365 | MEMORY-* | UC-06/07 Year 1 退化レポート保全 |
| `PROMPT_MAX_LENGTH_CHARS` | 8000 | PROMPT-CONFIG | 概算 token 上限（日本語 1 文字 ≒ 1〜2 token として 4000〜5000 文字相当、Bedrock 200K token 上限の余裕）|
| `PROMPT_DEFAULT_PREFERRED_AXIS` | 'fact' | PROMPT-CONFIG | 初回ユーザー既定 |
| `PROMPT_HOURLY_WAGE_FALLBACK_YEN` | 2500 | PROMPT-CONFIG | profile 未設定時 |
| `MEMORY_RETRIEVE_TOP_K_MAX` | 5 | MEMORY-09 | プロンプト爆発防止 |
| `STRESS_HIGH_SCORE_THRESHOLD` | 4 | STRESS-* | high の境界 |
| `STRESS_MID_SCORE_THRESHOLD` | 2 | STRESS-* | mid の境界 |

> NFR 的な閾値（SLI/SLO の具体値・性能目標）は NFR Requirements / NFR Design ステージで Unit-3 向けに最終確定する。本表は機能設計時点の既定値。
