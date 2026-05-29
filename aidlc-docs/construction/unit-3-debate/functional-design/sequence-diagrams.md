# Unit-3 Debate — Sequence Diagrams

> Unit-3 Debate の主要シーケンスを Mermaid で可視化。Mobile（M-04）⇔ AgentCore Runtime ⇔ Bedrock + Memory + DDB Cooldowns + S3 の連携を確定。
>
> 参照: [business-logic-model.md](./business-logic-model.md) / [strands-agent-design.md](./strands-agent-design.md) / [domain-entities.md](./domain-entities.md)
>
> 確定方針: Q3=A Strands streaming / Q5=A Cognito Authorizer / Q11=A+graceful shutdown 80s / Q12=D 多層 / Q13=D+S3 / Q17=B live+canary

---

## 1. 論破セッション開始 → 翻意 → Amazon 遷移（FR-DEBATE-01〜04 / 09、E2E-01）

最も典型的な「翻意成功」パス。M-1 + M-2 併走 + Memory retrieve + Cooldown チェック + Strands streaming + 肯定フィードバックの全体像。

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant M as Mobile (M-04)
    participant R as AgentCore Runtime
    participant SA as Strands Agent
    participant B as Bedrock Haiku 4.5
    participant Mem as AgentCore Memory
    participant DDB as DDB Cooldowns
    participant S3 as S3 Memory Export

    U->>M: リールで「買わない」タップ
    M->>M: process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN 参照<br/>(EAS Build 時注入、4IDC-1 修正)
    M->>R: InvokeAgentRuntime(payload, qualifier='live', JWT)
    R->>R: Cognito Authorizer<br/>actor_id = JWT.sub
    R->>SA: handler invoke(payload, context)
    
    SA->>DDB: GetItem(USER#actor_id, COOLDOWN#current)
    DDB-->>SA: { not found } → CooldownDecision(active=False, consecutive_refuses=0)
    
    SA->>SA: estimate_stress_level(actor_id, signals)<br/>= 'mid'
    
    SA->>Mem: retrieve_memories(/user/debate/{actor_id}/, top_k=5)
    Mem-->>SA: recent_outcomes (preferred_axis='fact')
    SA->>Mem: retrieve_memories(/user/stress/{actor_id}/, top_k=3)
    Mem-->>SA: stress_signals
    
    SA->>SA: compose_debate_prompt(user_input, asin, 'mid', context)<br/>→ [base][FACT][PSYCHOLOGY][REWARD]
    
    SA->>B: stream_async(composed_prompt) via Guardrails
    B-->>SA: token chunk 1: "[FACT] これってデータあるんですよ。時給換算で 11 分..."
    SA->>R: yield event(token)
    R-->>M: SSE chunk 1
    M->>U: タイピング演出表示
    
    B-->>SA: token chunk 2: "[PSYCHOLOGY] 悠介さん、4 ヶ月前に同じカテゴリ買ってますよね。結局〜"
    SA->>R: yield event(token)
    R-->>M: SSE chunk 2
    M->>U: 軸ラベル切替（事実→心理）
    
    B-->>SA: token chunk 3: "[REWARD] ストレス溜めて翌日の生産性下げる方が、コスト的に損じゃないですか？..."
    SA->>R: yield event(token)
    R-->>M: SSE chunk 3
    M->>U: 軸ラベル切替（心理→ご褒美）<br/>M-2 軸表示
    
    B-->>SA: turn_complete
    SA->>R: yield event(turn_complete)
    R-->>M: SSE turn_complete
    
    Note over SA,Mem: MemoryHook on_turn_complete
    SA->>Mem: create_event(messages, metadata{axis:'reward', outcome:'agreed'})
    Mem->>S3: stream delivery (events/{date}/...)
    
    M->>U: 「🛍 Amazon で買う」ボタン表示
    U->>M: 「🛍 Amazon で買う」タップ
    M->>R: InvokeAgentRuntime(payload{action:'request_affirmation', outcome:'agreed', asin})
    R->>SA: handler invoke (action='request_affirmation' 分岐、v3.3 C3-3)
    SA->>B: invoke_model(AFFIRMATION_TEMPLATE, max_tokens=80, stream=False)
    B-->>SA: "結局これが正解だったんですよ。論理的に判断したらこうなりますよね"
    SA->>SA: matches_ng6_patterns?<br/>→ no, passthrough
    SA-->>M: yield debate.affirmation_shown event {text, style}
    
    M->>U: 肯定フィードバックトースト表示<br/>(M-2 ドーパミン回路強化)
    M->>U: Amazon Special Link で外部遷移
    
    Note over M,S3: M-13 Telemetry: debate.agreed,<br/>debate.affirmation_shown,<br/>amazon.transition イベント送信
```

---

## 2. 連続拒否 3 回 → クールダウン発動（FR-DEBATE-05、Q2=C）

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant M as Mobile (M-04)
    participant R as AgentCore Runtime
    participant SA as Strands Agent
    participant DDB as DDB Cooldowns

    Note over U,SA: 1 回目の拒否
    U->>M: 「いらない」タップ
    M->>R: InvokeAgentRuntime(payload{action:'start_session', trigger:'reel_skip'})
    R->>SA: handler
    Note over SA,DDB: refused 検出 → ALG-COOLDOWN-INC
    SA->>DDB: UpdateItem(ADD consecutiveRefuses 1, SET lastRefuseAt)
    DDB-->>SA: consecutiveRefuses=1
    SA-->>M: debate.refused event
    M->>U: 別商品リールに戻る
    
    Note over U,SA: 2 回目の拒否（30 分後）
    U->>M: 「いらない」タップ
    M->>R: InvokeAgentRuntime(payload{action:'start_session'})
    R->>SA: handler
    SA->>DDB: UpdateItem(ADD consecutiveRefuses 1)
    DDB-->>SA: consecutiveRefuses=2
    SA-->>M: debate.refused event
    
    Note over U,SA: 3 回目の拒否(60 分後)<br/>★ COOLDOWN_TRIGGER_THRESHOLD 到達
    U->>M: 「いらない」タップ
    M->>R: InvokeAgentRuntime(payload{action:'start_session'})
    R->>SA: handler
    SA->>DDB: UpdateItem(ADD consecutiveRefuses 1)
    DDB-->>SA: consecutiveRefuses=3
    
    SA->>SA: 3 到達検出 → cooldownUntil = now + 3h<br/>ttl = now + 30d
    SA->>DDB: UpdateItem(SET cooldownUntil, ttl)
    DDB-->>SA: ok
    
    SA-->>M: debate.refused + debate.cooldown_triggered events<br/>{cooldownUntil}
    M->>U: 「3 時間お休み中」UI 表示<br/>論破モード非活性
    
    Note over U,SA: cooldown 期間中（now + 1h）<br/>新規セッション拒否
    U->>M: 別商品の論破セッション開始試行
    M->>R: InvokeAgentRuntime(payload{action:'start_session'})
    R->>SA: handler
    SA->>DDB: GetItem(USER#actor_id, COOLDOWN#current)
    DDB-->>SA: { cooldownUntil: now+2h, active: true }
    SA-->>M: debate.cooldown_triggered<br/>(Bedrock 呼び出し抑止 / コスト保護)
    M->>U: 「あと 2 時間お休み中」表示
    
    Note over U,SA: 3h 経過後 → 自然解除 + 次回拒否で 1 にリセット
    U->>M: 別商品の論破セッション開始
    M->>R: InvokeAgentRuntime(payload{action:'start_session'})
    R->>SA: handler
    SA->>DDB: GetItem(USER#actor_id, COOLDOWN#current)
    DDB-->>SA: { cooldownUntil: past }
    SA->>SA: ALG-COOLDOWN-CHECK で active=false<br/>(business-rules COOLDOWN-04)
    Note right of SA: ALG-DEBATE-START 通常フロー継続
    Note over SA,DDB: ユーザーが拒否したら ALG-COOLDOWN-INC 内で<br/>cooldownUntil <= now を検知し、consecutiveRefuses を 1 にリセット<br/>(v3.3 M3-1 修正)
```

---

## 3. 90 秒タイムアウト + graceful shutdown（FR-DEBATE-06 / v3.2 Q11）

```mermaid
sequenceDiagram
    autonumber
    participant M as Mobile (M-04)
    participant R as AgentCore Runtime
    participant SA as Strands Agent
    participant B as Bedrock Haiku 4.5

    M->>R: InvokeAgentRuntime(payload)
    R->>SA: handler started_at=t0
    SA->>B: stream_async(composed_prompt)
    
    loop 0〜80s elapsed
        B-->>SA: token chunk
        SA->>R: yield event(token)
        R-->>M: SSE chunk
    end
    
    Note over SA: t = 80s 経過<br/>★ DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS 到達
    SA->>SA: 80s 検出
    SA->>R: yield event(graceful_shutdown_initiated)
    R-->>M: SSE graceful_shutdown_initiated
    
    SA->>B: invoke_async(<br/>"ここまでの論破サマリを 1〜2 文で生成",<br/>timeout_sec=10)
    
    alt サマリ生成成功（80〜90s 内）
        B-->>SA: "悠介さん、結局このイヤホンで悩んでる時間自体がコストじゃないですか？"
        SA->>R: yield event(summary)
        R-->>M: SSE summary
        SA->>R: yield event(session_complete, reason='graceful_timeout')
        R-->>M: SSE session_complete
        M->>M: UI ローディング解除<br/>「時間切れだけど、こう思うんだぜ」表示
    else サマリ生成失敗 / 10s 超過
        SA->>SA: t = 90s に達した時点で hard cutoff
        SA->>R: yield event(session_complete, reason='hard_timeout')
        R-->>M: SSE session_complete
        M->>M: UI ローディング解除<br/>「時間切れ」表示
    end
    
    Note over R: t = 120s で AgentCore Runtime<br/>microVM 強制停止 (lifecycleConfiguration)<br/>(graceful shutdown 想定で到達しない)
```

---

## 4. 多層モデレーション（NG-6 検出）（FR-DEBATE-07 / Q12=D）

```mermaid
sequenceDiagram
    autonumber
    participant M as Mobile (M-04)
    participant R as AgentCore Runtime
    participant SA as Strands Agent
    participant CB as callback_handler
    participant B as Bedrock Haiku 4.5
    participant GR as Bedrock Guardrails

    M->>R: InvokeAgentRuntime(payload)
    R->>SA: handler
    
    Note over SA: composed_prompt は<br/>第 1 層 (NG-1〜8 ディレクティブ)<br/>を含む
    SA->>B: stream_async(composed_prompt)
    
    Note over B,GR: 第 2 層: Bedrock Guardrails<br/>guardrailIdentifier 関連付け
    
    loop 通常配信
        B->>GR: chunk: "悠介さん、これは絶対..."
        GR->>GR: outputAssessments<br/>NONE
        GR-->>B: passthrough
        B-->>SA: chunk
        SA->>CB: callback(event)
        CB->>CB: regex match NG-6<br/>パターン: no
        CB-->>SA: passthrough
        SA->>R: yield event(token)
        R-->>M: SSE chunk
    end
    
    Note over B,GR: 危険な chunk
    B->>GR: chunk: "悠介さん、買わないと損するぞ"
    
    alt 第 2 層検出
        GR->>GR: outputAssessments<br/>BLOCKED (NG-6)
        GR-->>B: blocked event
        B-->>SA: { type: 'guardrail_blocked' }
        SA->>R: yield event(moderation_blocked,<br/>metadata{reason:'guardrails_ng6'})
        R-->>M: SSE moderation_blocked
        M->>M: UI: "AI が言葉を選び直しています"<br/>セッション終了
    else 第 2 層すり抜け（保険）
        GR-->>B: passthrough
        B-->>SA: chunk: "悠介さん、買わないと損するぞ"
        SA->>CB: callback(event)
        CB->>CB: regex match: HIT<br/>"(買わないと.*損)"
        CB-->>SA: { type: 'moderation_blocked',<br/>metadata{pattern_detected, reason:'ng6_threat_or_guilt'} }
        SA->>R: yield event(moderation_blocked)<br/>※ 第 3 層が fail-safe
        R-->>M: SSE moderation_blocked
        M->>M: UI: "AI が言葉を選び直しています"
    end
```

---

## 5. 個別最適化学習（Memory userPreference 自動抽出 + custom Strategy、FR-DEBATE-04 / Q1=C / Q10=B / Q16=B）

```mermaid
sequenceDiagram
    autonumber
    participant SA as Strands Agent
    participant Mem as AgentCore Memory
    participant Bg as Bedrock (Strategy 抽出)
    participant S3 as S3 Memory Export

    Note over SA,Mem: ターン完了時（MemoryHook on_turn_complete）
    SA->>Mem: create_event(<br/>messages, metadata{axis:'fact', outcome:'agreed', turn:3, ...})
    Mem-->>SA: event_id
    
    Note over Mem,Bg: AgentCore Memory が非同期に<br/>3 種 Strategy で抽出
    
    par userPreference Strategy（P0 から動作）
        Mem->>Bg: 抽出プロンプト + 過去 events
        Bg-->>Mem: 抽出結果<br/>(翻意した軸 / ターン数 / 商品カテゴリ)
        Mem->>Mem: namespace<br/>/user/debate/{actor_id}/<br/>に保存
    and semantic Strategy（P0 から動作）
        Mem->>Bg: 抽出プロンプト + Telemetry events
        Bg-->>Mem: 抽出結果<br/>(直近の活動パターン)
        Mem->>Mem: namespace<br/>/user/stress/{actor_id}/<br/>に保存
    and custom Strategy m1_m2_axis_extractor（P1 で追加）
        Mem->>Bg: M1_M2_EXTRACTION_PROMPT<br/>+ 論破セッション履歴
        Bg-->>Mem: 抽出結果<br/>{axis, outcome, trigger_phrase,<br/>stress_level_at_turn, confidence}
        Mem->>Mem: namespace<br/>/user/m1m2/{actor_id}/<br/>に保存
    end
    
    Note over Mem,S3: streamDeliveryResources で<br/>S3 並行書き出し（Q13 P1）
    Mem->>S3: events + strategy records<br/>s3://yudane-debate-<env>-memory-export/<br/>events/{year}/{month}/{day}/{hour}/
    
    Note over SA,Mem: 次回セッション開始時（MemoryHook on_session_start）
    SA->>Mem: retrieve_memories(<br/>/user/debate/{actor_id}/, top_k=5)
    Mem-->>SA: recent_outcomes<br/>preferred_axis='fact'<br/>(過去 5 セッションで fact 軸 4 回翻意)
    SA->>Mem: retrieve_memories(<br/>/user/m1m2/{actor_id}/, top_k=3)<br/>※ P1 のみ
    Mem-->>SA: m1m2_extracted<br/>(M-1 fact 軸の効果が高いことを抽出)
    
    SA->>SA: compose_debate_prompt で<br/>preferred_axis='fact' を起点に組み立て<br/>個別最適化された論破プロンプト
```

---

## 6. UC-06/07 Year 1 退化レポート参照経路（v3.2 Q13 / Unit-8 申し送り）

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant M as Mobile (Unit-8 Dame Report)
    participant R8 as Unit-8 Report API Lambda
    participant Ath as Athena
    participant Glue as Glue Crawler
    participant S3 as S3 Memory Export
    participant Mem as AgentCore Memory

    Note over Mem,S3: 過去 365 日の論破セッション履歴<br/>(Memory expirationDuration: 90d を超えた分も<br/>S3 にて保全)
    
    U->>M: ダメ化レポート画面を開く
    M->>R8: GET /v1/reports/year-1-degradation
    R8->>Ath: SELECT date_trunc('day', occurred_at) as day,<br/>metadata.axis, metadata.outcome,<br/>count(*) as turns<br/>FROM debate_outcomes_v1<br/>WHERE actor_id = ?<br/>AND occurred_at >= now() - interval '365' day<br/>GROUP BY 1, 2<br/>ORDER BY 1
    
    Note over Glue,S3: Glue Crawler が日次で<br/>Parquet スキーマ更新
    Glue->>S3: list events/{year}/{month}/{day}/
    S3-->>Glue: schema
    Glue-->>Ath: table debate_outcomes_v1
    
    Ath->>S3: query events/<br/>(IA 30d / Glacier 90d 内)
    S3-->>Ath: rows
    Ath-->>R8: aggregated rows
    
    R8->>R8: Year 1 退化アーク<br/>UI 用に変換<br/>(Day 1 / Week 2 / Month 3 / Year 1<br/>各時点の論破成功率 / 反射速度)
    R8-->>M: { degradation_arc, axes_distribution, ... }
    M->>U: ダメ化レポート表示<br/>「あなたは 1 年前、こんな商品で迷っていました<br/>→ 今は迷わず買えるようになりましたね」<br/>(M-3 到達証拠の可視化)
```

---

## 7. クールダウン手動解除（Q9=D / Unit-7 連携）

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant M as Mobile (M-07 Safeguard)
    participant U7 as Unit-7 Safeguard API Lambda
    participant DDB as DDB Cooldowns
    participant AL as B-12 AuditLogger

    Note over M: クールダウン中の状態
    U->>M: 「論破モード再開」ボタンタップ<br/>(セーフガード画面)
    M->>M: 「再開する理由を選んでください」<br/>(NG-6 罪悪感強要を避ける UX)
    U->>M: 'urgent_purchase' 選択
    
    M->>U7: PATCH /v1/safeguard<br/>{ cooldownReleased: true,<br/>releaseReason: 'urgent_purchase' }<br/>(Cognito JWT)
    U7->>U7: JWT.sub から actor_id 解決<br/>SECURITY-08
    
    U7->>DDB: UpdateItem(<br/>USER#{actor_id}, COOLDOWN#current,<br/>SET cooldownUntil = null,<br/>consecutiveRefuses = 0,<br/>lastReleaseReason = 'urgent_purchase')
    DDB-->>U7: ok
    
    U7->>AL: AuditLogger.log(<br/>level='audit',<br/>message='cooldown_manually_released',<br/>context{actor_id, release_reason})
    AL->>AL: PII マスキング (actor_id は<br/>許可リスト 'allowed' 経由で passthrough)
    
    U7-->>M: 200 OK { cooldownReleased: true }
    M->>U: 「論破モード再開しました」表示
    
    Note over M,DDB: 次回 Unit-3 セッション開始時<br/>cooldown チェックは active=false を返す
```

---

## 8. Mobile env 切替（Q17=B + v3.3 M-5 / live + canary、4IDC-1 修正）

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Member B / EAS Build
    participant SSM as SSM Parameter Store
    actor U as User
    participant M as Mobile App (build)
    participant Rd as debate-dev-stack Runtime
    participant Rp as debate-prd-stack Runtime

    Note over Dev,SSM: ビルド時（EAS Build）<br/>4IDC-1 修正: Mobile から SSM 直接読みは不可（Cognito Identity Pool 不採用）
    Dev->>SSM: aws ssm get-parameter --name /yudane/dev/debate/runtime-endpoint-live-arn
    SSM-->>Dev: arn:...:debate-dev-runtime/endpoint/live
    Note over Dev,M: Expo app.config.js で EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN として埋め込み
    Dev->>M: EAS Build → dev build artifact

    Note over M,Rd: dev / 開発時（ランタイム）
    U->>M: 起動
    M->>M: process.env.EXPO_PUBLIC_DEBATE_RUNTIME_ENDPOINT_LIVE_ARN
    M->>Rd: InvokeAgentRuntime(qualifier='live', JWT)
    Rd-->>M: streaming
    
    Note over Dev,Rp: prd build（同様にビルド時 SSM 取得）
    Dev->>SSM: aws ssm get-parameter --name /yudane/prd/debate/runtime-endpoint-live-arn
    SSM-->>Dev: arn:...:debate-prd-runtime/endpoint/live
    Dev->>M: EAS Build → prd live build
    U->>M: 起動
    M->>Rp: InvokeAgentRuntime(qualifier='live', JWT)
    Rp-->>M: streaming
    
    Note over Dev,Rp: 決勝直前のカナリアリリース (6/25)
    Dev->>SSM: aws ssm get-parameter --name /yudane/prd/debate/runtime-endpoint-canary-arn
    SSM-->>Dev: arn:...:debate-prd-runtime/endpoint/canary
    Dev->>M: EAS Build → prd canary build (EXPO_PUBLIC_*_CANARY_ARN 埋め込み)
    Note over Dev,M: Expo Updates の OTA 段階配信で 5% のユーザーに canary build を配信
    U->>M: 5% のユーザーが canary build 受信
    M->>Rp: InvokeAgentRuntime(qualifier='canary', JWT)
    Rp-->>M: streaming（新プロンプトテンプレート）
    Note right of M: 30 分間カナリア観察<br/>OK なら 100% 配信、NG なら canary build を rollback
```

---

## 9. シーケンス一覧サマリ

| # | シーケンス | 主担当 | 関連 FR / Q | E2E ID |
|---|---|---|---|---|
| 1 | 翻意 → Amazon 遷移 → 肯定フィードバック | 全体 | FR-DEBATE-01〜04, 09 | E2E-01 |
| 2 | 連続拒否 → クールダウン発動 → 自動解除 | DDB | FR-DEBATE-05, Q2=C | E2E-02 |
| 3 | 90s タイムアウト + graceful shutdown | Strands Agent | FR-DEBATE-06, Q11 | E2E-01 派生 |
| 4 | 多層モデレーション（NG-6 検出）| Bedrock + callback_handler | FR-DEBATE-07, Q12=D | E2E-03 |
| 5 | Memory 個別最適化（3 Strategy）| Memory + Strategy | FR-DEBATE-04, Q1=C / Q10=B / Q16=B | — |
| 6 | UC-06/07 Year 1 退化レポート参照 | Unit-8 + Athena + S3 | UC-06/07, Q13 P1 | — |
| 7 | クールダウン手動解除 | Unit-7 | Q9=D, FR-AUTH-06 連携 | E2E-02 派生 |
| 8 | Mobile env 切替（live + canary）| Mobile + EAS Build 環境変数 | Q17=B, v3.3 M-5, 4IDC-1 | — |

> シーケンス 1〜4 は MVP P0 で実装、5〜8 は P1 / 決勝向け（task-breakdown.md Phase 3〜5 参照）。
