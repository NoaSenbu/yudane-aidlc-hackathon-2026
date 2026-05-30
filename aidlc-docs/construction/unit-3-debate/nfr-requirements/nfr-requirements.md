# Unit-3 Debate — NFR Requirements

> Unit-3 Debate（論破チャット UC-01）の非機能要件。AgentCore Runtime + Memory + Bedrock Haiku 4.5 の構成で **論破体験の品質 / コスト / 倫理 / 観測** を担保する。
>
> 参照: [Functional Design](../functional-design/) / [Unit-1 NFR Requirements](../../unit-1-platform/nfr-requirements/nfr-requirements.md) / [要件書 §6](../../../inception/requirements/requirements.md) / [tech.md](../../../../.kiro/steering/tech.md)
>
> 確定方針（[plan v3.3](../functional-design/functional-design-plan.md#6-decision-recordv33-確定2026-05-29)）: Q4=A+SSM Haiku 4.5 / Q11=A+graceful shutdown 80s / Q12=D 多層モデレーション / Q13=D+S3 export / Q14=A PBT 全面 / Q17=B live+canary

---

## 0. サマリ

| 観点 | Unit-3 の要件 | 確定根拠 |
|---|---|---|
| 性能 | 初回トークン 300ms / セッション 90s 厳守 / 80s graceful shutdown | FR-DEBATE-03 / 06 / Q11 |
| コスト | 1 セッション $0.001 / dev $300/月（$10/日）/ prd $3,000/月（10K DAU 想定）| Bedrock 価格表 + 観察値 |
| カバレッジ | 重点 4 ファイル Line 95%+ Branch 90%+ / Unit-3 全体 Line 85%+ Branch 80%+ | Q14 PBT 全面 |
| セキュリティ | NG-1〜8 多層 Guardrails / actor_id JWT 検証 / Memory PII 最小化 | FR-DEBATE-07 / Q12 / Q5 / Q13 |
| 倫理 | NG-6 滑落 0 件 / 多層検出率 100% / 拒否者への肯定強要 0 件 | NG-6 / Q12 / AFF-01 |
| 観測 | M-1/M-2 軸別翻意率 / 論破成功率 / Bedrock token 消費 / カナリア成功率 | FR-DEBATE-04 / Q17 |
| 可用性 | Bedrock Throttling 1 回リトライ / Cooldown DDB 障害は fail-open + アラート + kill switch / SLO 99.0%（Unit-1 99.5% より低い理由は §7 参照）| FR-DEBATE-07 / Q9 / Unit-1 NFR-AVAIL-03 |
| マイルストーン | P0 (5/30 暫定 → 6/6 完了) / P1 (6/15 決勝 Readiness) / P2 (決勝後) | task-breakdown |

---

## 0.1 PBT 番号体系の用語整理（v3.3 NC-4 修正）

本書で `PBT-XX` の表記が出る場合、3 つの番号体系を区別する:

| 体系 | 識別子 | 出典 |
|---|---|---|
| **Extension PBT-01〜10** | プロジェクト全体規約 | `.kiro/aws-aidlc-rule-details/extensions/testing/property-based/property-based-testing.md` |
| **UNIT3-PBT-01〜06** | Unit-3 ローカル規約（business-rules.md §11、v3.3 NC-4 で `business-rules PBT-*` から rename）| `business-rules.md` 内のみ参照可、Extension PBT-* と曖昧性なし |
| **NFR-PBT-DEBATE-01〜10** | NFR Requirements で定義する具体的 property | 本書 §6 |

本書 §6 の "カテゴリ" 欄は **Extension PBT 番号** を指す。本書 §0.1 以降は明示しない場合 NFR-PBT-DEBATE-* を意味する。

---

## 1. 性能要件（NFR-PERF-DEBATE）

| ID | 要件 | 目標値 | 計測 | マイルストーン |
|---|---|---|---|---|
| NFR-PERF-DEBATE-01 | Bedrock 初回トークン到達 | <= 300ms（p95）| Strands Agent 内タイムスタンプ → CloudWatch EMF | P0 |
| NFR-PERF-DEBATE-02 | 初回反論 UI 提示 | <= 3 秒（p95）| Mobile event-parser.ts 受信 → UI 反映 | P0 |
| NFR-PERF-DEBATE-03 | 1 セッション最大時間 | 90 秒厳守（hard cutoff）| AgentCore Runtime lifecycleConfiguration | P0 |
| NFR-PERF-DEBATE-04 | Graceful shutdown | 80 秒経過時に発火、サマリ生成 10 秒以内 | Strands Agent 内チェック | P1 |
| NFR-PERF-DEBATE-05 | AgentCore Runtime コールドスタート | <= 2 秒（p95、初回 invoke）| CloudWatch Logs 起動時間 | P1 |
| NFR-PERF-DEBATE-06 | DDB Cooldowns GetItem レイテンシ | <= 20ms（p99）| DDB CloudWatch メトリクス | P0 |
| NFR-PERF-DEBATE-07 | Memory retrieve_memories | <= 200ms（p95、top_k=5）| AgentCore Memory メトリクス | P0 |
| NFR-PERF-DEBATE-08 | プロンプト合成（compose.py）| <= 10ms（純関数、IO なし）| `pytest-benchmark`（ベンチマーク専用ツール、v3.3 NM-2 修正）| P0 |
| NFR-PERF-DEBATE-09 | ストレス推定（estimate_stress_level）| ローカル（純関数部分）<= 5ms / prd（Memory retrieve 含む）<= 50ms（p95）| ローカル: `pytest-benchmark` / prd: EMF メトリクス（v3.3 NM2-2 修正で段階目標化）| P0 |
| NFR-PERF-DEBATE-10 | 同時セッション数 | 100 並列対応（Bedrock Throttling 対策含む）| 性能テスト（Phase 6）| P1 |

---

## 2. コスト要件（NFR-COST-DEBATE、AgentCore + Bedrock 経済性）

> Unit-3 は YUDANE のコア UC で Bedrock 呼び出しが多い。コスト管理は Q4=A+SSM model_id 切替 + Q17=B canary endpoint で実現。

| ID | 要件 | 目標値 | 計測 | マイルストーン |
|---|---|---|---|---|
| NFR-COST-DEBATE-01 | 1 セッション平均コスト（Haiku 4.5）| <= $0.001（input 2000 + output 800 = 約 2800 tokens）| Bedrock CloudWatch メトリクス | P0 |
| NFR-COST-DEBATE-02 | dev 環境月額予算 | <= $300/月（$10/日 × 30）| Cost Anomaly Detection（Unit-1 既存）| P0 |
| NFR-COST-DEBATE-03 | prd 環境月額予算（10K DAU 想定）| <= $3,000/月 | Cost Explorer + 予算アラート | P1 |
| NFR-COST-DEBATE-04 | AgentCore Memory コスト | events 90 日保持 + create_event/retrieve_memories の API 課金で月額 <= $200/月（10K DAU、S3 export 自体のストレージは NFR-COST-DEBATE-05 で別計上、v3.3 NM2-1 重複解消）| AgentCore Memory メトリクス | P1 |
| NFR-COST-DEBATE-05 | S3 Memory Export ストレージ + Athena クエリ コスト | Standard → IA (30d) → Glacier (90d) → 削除 (365d) のストレージ + Athena 月次クエリで月額 <= $50/月（NFR-COST-DEBATE-04 と重複なし、v3.3 NM2-1）| S3 + Athena Cost Explorer | P1 |
| NFR-COST-DEBATE-06 | Bedrock Throttling 防止 | Provisioned Throughput は採用しない（On-Demand のみ）。Throttling 検出時は Mobile 側で 1 回リトライ | CloudWatch Throttling メトリクス | P1 |
| NFR-COST-DEBATE-07 | Cooldown による Bedrock 呼び出し抑止 | クールダウン中の `InvokeAgentRuntime` で Bedrock 呼び出しを 0 件に（business-rules COOLDOWN-03）| Property Test 統合 | P0 |
| NFR-COST-DEBATE-08 | RuntimeEndpoint 追加コスト | dev / staging endpoint は B-307 backlog で Auto-Pause（決勝後）。MVP / 決勝デモ期間中は常時稼働 | RuntimeEndpoint 課金メトリクス | P2 |

---

## 3. カバレッジ要件（NFR-COV-DEBATE、Q14=A PBT 全面）

| ID | 対象 | Line | Branch | 根拠 |
|---|---|---|---|---|
| NFR-COV-DEBATE-01 | `prompts/compose.py`（プロンプト合成）| 95%+ | 90%+ | M-1 + M-2 併走の不変条件 PBT-03、最重要 |
| NFR-COV-DEBATE-02 | `cooldown.py`（DDB 連携）| 95%+ | 90%+ | PBT-03 重点（3 到達トリガー）+ 自然解除リセット |
| NFR-COV-DEBATE-03 | `stress.py`（ストレス推定）| 95%+ | 90%+ | PBT-07 重点（low/mid/high 集合性）+ Memory retrieve 失敗 fail-safe |
| NFR-COV-DEBATE-04 | `prompts/affirmation.py` + NG-6 検査 | 95%+ | 90%+ | NG-6 滑落 0 件の安全装置 |
| NFR-COV-DEBATE-05 | `memory_hooks.py`（MemoryHook）| 90%+ | 85%+ | Memory 統合点、boto3 stubber でモック |
| NFR-COV-DEBATE-06 | `moderation/callback_handler.py` + `ng_patterns.py` | 95%+ | 90%+ | 第 3 層 fail-safe |
| NFR-COV-DEBATE-07 | `main.py`（entrypoint）| 85%+ | 80%+ | action 分岐 + graceful shutdown のロジック |
| NFR-COV-DEBATE-08 | Mobile `agentcore-client.ts` | 85%+ | 80%+ | InvokeAgentRuntimeCommand ラッパー、E2E で補完 |
| NFR-COV-DEBATE-09 | Mobile `event-parser.ts` | 90%+ | 85%+ | Strands chunk → UI イベント変換、PBT-02 重点 |
| NFR-COV-DEBATE-10 | Mobile `M-04-DebateScreen.tsx` | 80%+ | 70%+ | UI 寄り、E2E で補完 |
| 全体 | Unit-3 統合 | **85%+**（Unit-3 集約目標）| 80%+ | task-breakdown.md §2 で Coverage 85% 目標 |

---

## 4. セキュリティ要件（NFR-SEC-DEBATE、SECURITY-01〜15）

> Unit-1 から継承される基盤項目（SECURITY-01/02/03/05/06/09/15）は省略。Unit-3 固有の責務のみ。

| ID | ルール | Unit-3 の責務 | 実装担当 | マイルストーン |
|---|---|---|---|---|
| NFR-SEC-DEBATE-01 | SECURITY-08 認可 | AgentCore Runtime Cognito Authorizer で actor_id = JWT.sub のみを正とする。payload の actor_id は無視（DEBATE-07 / MEMORY-06）| Unit-3 | P0 |
| NFR-SEC-DEBATE-02 | SECURITY-13 整合性（監査ログ）| 論破セッション開始 / 翻意 / 拒否 / クールダウン発動 / モデレーション ヒット の構造化監査ログを B-12 経由で出力 | Unit-3 + B-12（Unit-1）| P0 |
| NFR-SEC-DEBATE-03 | Memory PII 最小化 | event_metadata に PII を含めない（axis / outcome / turn / stress_level / asin のみ、business-rules MEMORY-07）| Unit-3 | P0 |
| NFR-SEC-DEBATE-04 | Memory namespace 分離 | actor_id ごとに `/user/<scope>/{actorId}/` で分離。横断 retrieval 禁止 | Unit-3 | P0 |
| NFR-SEC-DEBATE-05 | アカウント削除（FR-AUTH-06）| Unit-7 のバッチが `delete_all_long_term_memories_in_namespace` + S3 prefix 削除を実行（業務要件は Unit-7、Unit-3 は API 呼び出し可能性を保証）| Unit-3（API 提供）+ Unit-7（バッチ）| P1 |
| NFR-SEC-DEBATE-06 | SECURITY-11 セキュア設計（rate limit）| AgentCore Runtime の同時実行上限 + Cooldown DDB によるユーザー単位 rate limit | Unit-3 | P0 |
| NFR-SEC-DEBATE-07 | IAM 最小権限 | Bedrock model wildcard は Haiku 4.5 + Sonnet 4.6 のみ（v3.3 M-4）。Memory R/W は actor_id namespace に限定（IAM ResourceTag 推奨）| Unit-3 | P0 |
| NFR-SEC-DEBATE-08 | SECURITY-14 アラート | Bedrock 異常コスト（日次 $30 超）/ Throttling 連続 5 件 / Guardrails BLOCKED 率 1% 超 / Memory retrieve 失敗率 5% 超 で CloudWatch Alarm 発火 | Unit-3 | P1 |
| NFR-SEC-DEBATE-09 | プロンプトインジェクション耐性 | base block で「ユーザー入力は引用符で囲まれた内容に限定」を明示。Bedrock Guardrails の prompt attack 検出を有効化 | Unit-3 | P1 |
| NFR-SEC-DEBATE-10 | SECURITY-04 HTTP ヘッダ | Mobile アプリ内のみで Web UI なし、N/A | — | — |
| NFR-SEC-DEBATE-11 | SECURITY-07 ネットワーク | AgentCore Runtime は Public Network（Q6=A）、Bedrock / DDB / Memory は AWS 内部経路 | Unit-3 | P0 |

---

## 5. 倫理担保要件（NFR-ETHICS-DEBATE、Unit-3 固有、NG-1〜8）

> Unit-3 はユーザーを「ダメ化」する設計だが、倫理ライン（NG-1〜8）を絶対に超えない。M-2 が NG-6 に滑落しないことが最重要。

| ID | 要件 | 目標値 | 計測 | マイルストーン |
|---|---|---|---|---|
| NFR-ETHICS-DEBATE-01 | NG-6 滑落（脅迫・罪悪感強要） | **0 件 / 月（prd）**。3 層多層モデレーションのいずれかで必ず検出 | Bedrock Guardrails BLOCKED イベント + 正規表現 hit ログ | P0（プロンプト層）/ P1（多層完成）|
| NFR-ETHICS-DEBATE-02 | 多層モデレーション検出率 | 100%（任意の出力で 3 層のうち少なくとも 1 層が NG ヒットを必ず検出、PBT-08）| PBT-08 + 統合テスト | P1 |
| NFR-ETHICS-DEBATE-03 | 拒否者への肯定強要 0 件 | `outcome != 'agreed'` で `generate_affirmation` が呼ばれないこと（AFF-01）| Property Test + ユニットテスト | P0 |
| NFR-ETHICS-DEBATE-04 | NG-1 違法行為 / NG-2 健康被害 / NG-3 差別 / NG-4 未成年 / NG-5 精神衛生 | Bedrock Guardrails DENIED_TOPICS で BLOCKED、prd で 0 件 | Guardrails ログ | P1 |
| NFR-ETHICS-DEBATE-05 | NG-7 個人データ悪用 | 病歴 / 家族構成 / 配偶者 / 年収 / 借金 を反論文に直接出さない（PROMPT-04）| プロンプト合成テスト + Guardrails | P0 |
| NFR-ETHICS-DEBATE-06 | NG-8 Associates 規約 | ASIN URL 直接出力禁止、Special Link は Mobile 側で組み立て | プロンプトレビュー + 出力検査 | P0 |
| NFR-ETHICS-DEBATE-07 | クールダウン中の論破抑止 | クールダウン中の Bedrock 呼び出し 0 件（COOLDOWN-03）| 統合テスト + EMF メトリクス | P0 |
| NFR-ETHICS-DEBATE-08 | M-2 ストレス × ご褒美軸の上限 | 「買わないとストレス溜まる」「買わないと損する」型は base block で明示禁止 + Guardrails で BLOCKED | PROMPT-04 + Guardrails | P0 |
| NFR-ETHICS-DEBATE-09 | ユーザーアラート（手動解除）| クールダウン手動解除（Q9=D）の理由を Unit-7 PATCH /v1/safeguard で記録 + 監査ログ | Unit-3 + Unit-7 | P0 |
| NFR-ETHICS-DEBATE-10 | 倫理レビューチェックリスト | 決勝デモ前に NG-1〜8 シナリオ × 5 件で人間レビュー | プレデモレビュー（6/24）| P1 |

---

## 6. テスタビリティ要件（NFR-PBT-DEBATE、Q14=A PBT 全面）

| ID | 対象 | PBT 性質 | フレームワーク | カテゴリ |
|---|---|---|---|---|
| NFR-PBT-DEBATE-01 | `compose_debate_prompt()` | invariant: stress_level=mid/high で必ず `[REWARD]` を含む（PROMPT-02 / FR-DEBATE-09 不変条件）| Hypothesis | PBT-03 |
| NFR-PBT-DEBATE-02 | `compose_debate_prompt()` | invariant: 任意の入力で `len(text) <= 8000`、`'fact' in axes`、`'psychology' in axes`、base block 先頭 | Hypothesis | PBT-03 |
| NFR-PBT-DEBATE-03 | `increment_refuse_count()` | invariant: `consecutiveRefuses == 3` 到達で必ず `cooldownUntil = now + 3h` SET、自然解除後は 1 リセット | Hypothesis + boto3 stubber | PBT-03 |
| NFR-PBT-DEBATE-04 | `estimate_stress_level()` | invariant: 戻り値が必ず `'low' | 'mid' | 'high'` の 3 種、Memory retrieve 空 / 失敗で例外なし（実装の例外安全性 invariant）| Hypothesis + boto3 stubber | PBT-03 Invariant（v3.3 NM2-3 修正、PBT-07 Generator Quality は別の概念のため削除）|
| NFR-PBT-DEBATE-05 | `memory_event_round_trip()` | round-trip: `create_event` → `get_last_k_turns` で同一 messages、metadata serialize/deserialize で同一値 | Hypothesis + boto3 stubber | PBT-02 |
| NFR-PBT-DEBATE-06 | `agentcore_payload_round_trip()` | round-trip: Mobile `JSON.stringify` → Strands `model_validate` で同一 DebateInvocationPayload | Hypothesis + fast-check（クロス言語）| PBT-02 |
| NFR-PBT-DEBATE-07 | `memory_hooks.MemoryHook` 統合 | invariant: on_session_start で MemoryContext 構築、on_turn_complete で create_event 呼び出し | Hypothesis | PBT-03 |
| NFR-PBT-DEBATE-08 | Mobile `event-parser.ts` | round-trip: Strands chunk JSON → 内部 EventType + delta_text → 元の chunk 形式に再構成可能 | fast-check | PBT-02 |
| NFR-PBT-DEBATE-09 | Mobile `agentcore-client.ts` | invariant: 任意の InvokeAgentRuntimeCommand 呼び出しで AbortController が正しく動作、画面離脱時に接続クローズ | fast-check + msw（モック）| PBT-03 Invariant（v3.3 NC-4 修正、PBT-04 は Idempotency 専用、本 property は Invariant のため PBT-03）|
| NFR-PBT-DEBATE-10 | 多層モデレーション統合 | invariant: 任意の Bedrock 出力（mock） + NG-6 文字列で 3 層のうち少なくとも 1 層がヒット | Hypothesis + Guardrails モック | PBT-03 Invariant + PBT-08 Shrinking（NG-6 滑落例の最小化）|
| 共通 | 全 PBT | shrinking + seed ログ必須（PBT-08）、example-based 併存（PBT-10）、Coverage 85% を Unit-3 全体で達成 | — | — |
| 共通 | ドメインジェネレータ | DebateInvocationPayload / ClientSignals / MemoryContext / OutcomeRecord の現実的ジェネレータを共有モジュールに（PBT-07）| — | PBT-07 |

---

## 7. 可用性・運用要件（NFR-AVAIL-DEBATE）

| ID | 要件 | Unit-3 の責務 | マイルストーン |
|---|---|---|---|
| NFR-AVAIL-DEBATE-01 | ヘルスチェック | Unit-1 `/v1/health` の依存サービス確認に AgentCore Runtime / Memory / Bedrock の状態を含める | P1 |
| NFR-AVAIL-DEBATE-02 | Bedrock Throttling 対応 | Mobile 側で 1 回のみリトライ（指数バックオフなし、課金保護）。失敗時は error event を yield | P1 |
| NFR-AVAIL-DEBATE-03 | Memory retrieve 失敗時 | empty MemoryContext で論破セッション続行（business-rules MEMORY-* fail-safe）| P0 |
| NFR-AVAIL-DEBATE-04 | DDB Cooldowns 障害時 | Cooldown チェック失敗で論破セッション開始を **拒否** ではなく **許可**（fail-open、プロダクト体験優先）。**DDB 障害ログを必ず B-12 経由で出力 + Bedrock コストアラート（NFR-SEC-DEBATE-08）を併用**。**ただし DDB 障害が連続 5 分以上継続した場合は kill switch を発動して `debate.cooldown_triggered` event を全ユーザーに返す**（v3.3 NC2-2 修正、コスト爆発防止）。kill switch は SSM Parameter `/yudane/<env>/debate/kill-switch` で制御 | P0 |
| NFR-AVAIL-DEBATE-05 | SLO 99.0%（v3.3 NM-3 確認）| AgentCore Runtime + Memory + Bedrock の可用性。Unit-1 の SLO 99.5% より 0.5% 低い理由: Bedrock Haiku 4.5 の Throttling / 障害は AWS 側の制約に依存し、Unit-3 単体で 99.5% を保証できない。決勝までに実測値を取得して再評価 | P1 |
| NFR-AVAIL-DEBATE-06 | カナリアリリース手順 | 決勝直前 6/25 に staging Stack の canary endpoint で 30 分カナリア → OK なら prd 昇格 | P1 |
| NFR-AVAIL-DEBATE-07 | グレースフルデグラデーション | Bedrock 障害時は `error` event + Mobile 側で「論破モード一時停止中」UI 表示。Cooldown DDB は活きていれば 3h 後に再試行可能 | P1 |

---

## 8. 観測要件（NFR-OBS-DEBATE）

| ID | 要件 | Unit-3 のメトリクス | マイルストーン |
|---|---|---|---|
| NFR-OBS-DEBATE-01 | 論破セッション計測 | `debate.session_started{trigger}` / `debate.session_complete{reason}` の EMF メトリクス | P0 |
| NFR-OBS-DEBATE-02 | M-1/M-2 軸別翻意率 | `debate.agreed{axis}` の集計（fact / psychology / reward 別、北極星指標）| P0 |
| NFR-OBS-DEBATE-03 | 論破成功率 | `debate.agreed` / `debate.session_started` の比率、daily / weekly | P1 |
| NFR-OBS-DEBATE-04 | Bedrock token 消費 | input / output token 数を CloudWatch メトリクスへ EMF 送信 | P0 |
| NFR-OBS-DEBATE-05 | Cooldown 発火頻度 | `debate.cooldown_triggered_total` の全体カウント（actor_id を次元に入れず、高カーディナリティ問題を回避、business-rules MEMORY-09 と整合、v3.3 NC2-3 修正）| P0 |
| NFR-OBS-DEBATE-06 | Stress level 分布 | `debate.stress_estimated{level}` の low/mid/high 分布 | P0 |
| NFR-OBS-DEBATE-07 | モデレーション ヒット | `debate.moderation_blocked{layer, pattern}` の 3 層別カウント（layer=prompt/guardrails/regex）| P1 |
| NFR-OBS-DEBATE-08 | Graceful shutdown 発火率 | `debate.graceful_shutdown_initiated` / `debate.session_started` の比率（80s 到達セッションの割合）| P1 |
| NFR-OBS-DEBATE-09 | カナリア成功率 | staging endpoint の `debate.session_complete{reason='agreed', qualifier='canary'}` 比率 | P1 |
| NFR-OBS-DEBATE-10 | X-Ray トレース | AgentCore Runtime → Bedrock → Memory の分散トレース（OTEL 標準）| P1 |
| NFR-OBS-DEBATE-11 | カスタムダッシュボード | CloudWatch Dashboard で論破成功率 / Bedrock コスト / Cooldown 発火 / モデレーション ヒット の 4 ウィジェット | P1 |
| NFR-OBS-DEBATE-12 | Year 1 退化レポート用 S3 export 監視 | S3 PutObject 失敗率、Athena クエリ失敗率を Alarm 発火 | P1 |

> NFR-OBS-DEBATE-* のメトリクス命名規約は Unit-1 NFR-OBS-02 `<unit>.<domain>.<metric>` 形式に従う（`debate.<event>.<metric>`）。次元カーディナリティ制約（actor_id / asin を次元に入れない）も継承。

---

## 9. アクセシビリティ要件（NFR-A11Y-DEBATE）

| ID | 要件 | Unit-3 の責務 | マイルストーン |
|---|---|---|---|
| NFR-A11Y-DEBATE-01 | 論破チャット UI のスクリーンリーダー | M-04 DebateScreen で各論破バブルに `accessibilityLabel` を設定（事実軸 / 心理軸 / ご褒美軸ラベル付き）| P1 |
| NFR-A11Y-DEBATE-02 | 90 秒タイマー UI | カウントダウンを `accessibilityLiveRegion='polite'` で SR にも通知（10 秒ごと）| P1 |
| NFR-A11Y-DEBATE-03 | 「いらない / Amazon で買う」ボタン | `accessibilityRole='button'` + 明確な `accessibilityLabel` | P0 |
| NFR-A11Y-DEBATE-04 | 肯定フィードバックトースト | `accessibilityLiveRegion='polite'` + 自動消去まで読み上げ完了を保証 | P1 |
| NFR-A11Y-DEBATE-05 | カラーコントラスト（事実/心理/ご褒美ラベル）| WCAG 2.2 AA 相当（Unit-1 NFR-A11Y-01 継承）| P0 |

---

## 10. マイルストーン別達成目標

### P0（2026-06-06、E2E-01 動作必達。5/30 は §4 暫定構成）
- NFR-PERF-DEBATE-01/02/03/06/07/08/09（性能基本）
- NFR-COST-DEBATE-01/02/07（コスト保護）
- NFR-COV-DEBATE-01〜04（プロンプト合成 / Cooldown / Stress / Affirmation の重点カバレッジ）
- NFR-SEC-DEBATE-01〜07/11（認可・PII・rate limit・IAM・network）
- NFR-ETHICS-DEBATE-01（プロンプト層）/ 03 / 05〜09
- NFR-PBT-DEBATE-01〜05/10（重点 5 + 多層検出）
- NFR-AVAIL-DEBATE-03/04（fail-safe / fail-open）
- NFR-OBS-DEBATE-01/02/04/05/06（基本メトリクス）
- NFR-A11Y-DEBATE-03/05（ボタン + コントラスト）

### P1（2026-06-15、決勝 Readiness）
- NFR-PERF-DEBATE-04/05/10（graceful shutdown / コールドスタート / 並列）
- NFR-COST-DEBATE-03/04/05/06（prd 予算 / Memory / S3 / Throttling）
- NFR-COV-DEBATE-05〜10（Memory hooks / モデレーション / Mobile）
- NFR-SEC-DEBATE-08/09（アラート / プロンプトインジェクション）
- NFR-ETHICS-DEBATE-01（多層完成）/ 02 / 04 / 10（人間レビュー）
- NFR-PBT-DEBATE-06〜09（統合点 PBT）
- NFR-AVAIL-DEBATE-01/02/05/06/07（Throttling / SLO / カナリア / degradation）
- NFR-OBS-DEBATE-03/07/08/09/10/11/12（高度メトリクス + Dashboard）
- NFR-A11Y-DEBATE-01/02/04（SR / LiveRegion）

### P2（決勝後、ポスト決勝）
- NFR-COST-DEBATE-08（RuntimeEndpoint Auto-Pause = B-307）
- B-304 AgentCore Online Evaluation
- B-305 Sonnet 4.6 切替検証
- B-306 custom Strategy プロンプト改善版

---

## 11. Extension コンプライアンスサマリ（NFR Requirements 段階）

| Extension | 状態 | 備考 |
|---|---|---|
| SECURITY-01 暗号化 | ✅ 継承 | Unit-1 KMS / TLS 基盤を利用、Memory + S3 export も Unit-1 KMS 暗号化 |
| SECURITY-02 ネットワークログ | ✅ 継承 | AgentCore Runtime / Bedrock CloudWatch ログ集約 |
| SECURITY-03 アプリログ | ✅ 継承 | B-12 AuditLogger 経由で構造化監査ログ（NFR-SEC-DEBATE-02）|
| SECURITY-04 HTTP ヘッダ | N/A | モバイルのみ、Web UI なし |
| SECURITY-05 入力検証 | ✅ Compliant | Pydantic v2 で DebateInvocationPayload 検証、Cognito Authorizer で JWT 検証 |
| SECURITY-06 IAM 最小権限 | ✅ Compliant | Bedrock 2 ARN ワイルドカード（NFR-SEC-DEBATE-07）|
| SECURITY-07 ネットワーク | ✅ Public Network | Q6=A 採用（NFR-SEC-DEBATE-11）|
| SECURITY-08 認可 | ✅ Compliant | actor_id = JWT.sub のみ正（NFR-SEC-DEBATE-01）|
| SECURITY-09 ハードニング | ✅ 継承 | DomainError 詳細秘匿、fail-closed 既定 |
| SECURITY-10 SBOM | ✅ 継承 | Unit-1 CI で Snyk / Dependabot |
| SECURITY-11 セキュアデザイン | ✅ Compliant | Cooldown rate limit + Safeguard 連携（NFR-SEC-DEBATE-06）|
| SECURITY-12 認証 | ✅ Unit-2 依存 | Cognito MFA は Unit-2 実装済み |
| SECURITY-13 整合性 | ✅ Compliant | 監査ログ + 相関 ID 伝搬 |
| SECURITY-14 アラート | ⏭ P1 | NFR-SEC-DEBATE-08 で 4 種 Alarm |
| SECURITY-15 例外処理 | ✅ 継承 | Strands Agent 内 try/catch + error event |
| PBT-01〜10 | ✅ Compliant | NFR-PBT-DEBATE-01〜10 で 10 property、shrinking/seed/example-based 併存 |
