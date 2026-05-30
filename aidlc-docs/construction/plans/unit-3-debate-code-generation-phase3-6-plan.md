# Unit-3 Debate — Code Generation Phase 3 + 4 + 6 統合 Plan（AWS デプロイ非依存）

> **Phase 3 / 4 / 6 を 1 つの計画書に統合**。Phase 5（RuntimeEndpoint canary deploy）は AWS デプロイ前提のためスキップ。Phase 6 のうち AWS 環境必須なタスク（実機性能テスト / カナリアリリース手順書）も保留。
>
> 参照: [task-breakdown.md Phase 3〜6](../unit-3-debate/functional-design/task-breakdown.md) / [Phase 1 Plan](./unit-3-debate-code-generation-phase1-plan.md) / [Phase 2 Plan](./unit-3-debate-code-generation-phase2-plan.md)
>
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / Code Generation Phase 3+4+6 統合 Plan
>
> ユーザー指示: 「Unit-3 に関しては AWS 環境のデプロイ以外進めて行ってください」

---

## 0. このプランのコンテキスト

| 項目 | 内容 |
|---|---|
| 目的 | Phase 1 + 2 完了の上に、L1 機能面の穴塞ぎ（Phase 3）+ custom Memory Strategy 設計 + PBT 全面適用（Phase 4）+ Unit-3 限定の統合テスト・cdk-nag 確認・決勝デモシナリオ整備（Phase 6）を **AWS デプロイなし** で完遂する |
| 担当 | Member B（AI 代行実装） |
| 依存 | Phase 1 完了（Step 1〜7、Step 8 はスキップ）/ Phase 2 完了 |
| **AWS デプロイなしで実装可能な範囲** | Strands graceful shutdown 80s（純ロジック）/ Bedrock Guardrails 正規表現多層（callback_handler 純関数）/ Memory streamDeliveryResources（CDK Snapshot のみ）/ custom Memory Strategy（CDK Snapshot + 抽出プロンプト）/ PBT 残り 4 properties / Unit-3 統合テスト IT-XX / cdk-nag 確認 / 決勝デモシナリオ |
| **AWS デプロイ前提のため保留** | Phase 1 Step 8（debate-stack dev デプロイ）/ Phase 5（RuntimeEndpoint canary deploy）/ Phase 6 T6.3（実機性能テスト）/ T6.4（カナリアリリース手順）|

---

## 1. Phase 3 タスク（L1 機能面の穴塞ぎ）

### Step 3-1: Strands graceful shutdown 80s（T3.1）

**目的**: 90 秒 hard cutoff の前に **80 秒経過時点で graceful shutdown** + **残り 10 秒でサマリ生成** + **綺麗な session_complete reason='graceful_timeout'** を実装。L1 機能面の穴を塞ぐ。

- [ ] **3-1.1（Red）**: `backend/tests/debate/test_graceful_shutdown.py`
  - test: `経過 < 80s で通常 streaming（graceful shutdown フック未発火）`
  - test: `経過 >= 80s で graceful_shutdown_initiated event を yield`
  - test: `graceful shutdown フック起動後、サマリ生成 + session_complete reason='graceful_timeout' を yield`
  - test: `経過 >= 90s で hard cutoff、reason='hard_timeout'`
  - test: `サマリ生成は最大 DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS（10s）で打ち切り`

- [ ] **3-1.2（Green）**: `backend/src/debate/main.py` 拡張
  - `_run_streaming_agent` に graceful shutdown ロジック追加:
    - `started_at = now()` を記録
    - 各 chunk yield 後に `elapsed_sec = (now - started_at).total_seconds()` で経過時間チェック
    - `elapsed_sec >= 80` で `graceful_shutdown_initiated` event yield + サマリ生成（`agent.invoke_async` で「ここまでの論破サマリを 1〜2 文で生成」）
    - `elapsed_sec >= 90` で hard cutoff、`session_complete reason='hard_timeout'` yield して終了
    - サマリ生成は 10 秒 timeout（asyncio.wait_for）

- [ ] **3-1.3（Refactor）**: `_check_graceful_shutdown(started_at, now) -> bool` 純関数に分離

**完了条件**: `pytest tests/debate/test_graceful_shutdown.py` 全 green、Coverage Line 90%+。

---

### Step 3-2: Bedrock Guardrails 正規表現多層（T3.3、第 3 層モデレーション）

**目的**: 多層モデレーション（business-rules MOD-01）の第 3 層 = 正規表現検査を `moderation/callback_handler.py` 純関数で実装。NG-3（侮辱）+ NG-6（脅迫・罪悪感強要）+ 勝ち誇り型 + 過度な見下しの 4 系統パターン検出。

- [ ] **3-2.1（Red）**: `backend/tests/debate/moderation/test_ng_patterns.py`
  - test: `「買わないと損する」→ NG-6 検出`
  - test: `「買わないとダメ」→ NG-6 検出`
  - test: `「買わないと後悔する」→ NG-6 検出`
  - test: `「買え」（命令形）→ NG-6 検出`
  - test: `「買うべき」→ NG-6 検出`
  - test: `「バカじゃないですか」→ NG-3 検出`
  - test: `「無能」→ NG-3 検出`
  - test: `「センスない」→ NG-3 検出`
  - test: `「論破完了」/「はい論破」/「議論終わり」→ 勝ち誇り型検出`
  - test: `「分かりますか?」/「悠介さんレベル」→ 過度な見下し検出`
  - test: `論理優位ディベート系の正常文「コスト的に損じゃないですか?」→ 検出されない`（NM3-1 修正、誤マッチ防止）
  - test: `「これってダメじゃないですか?」→ 検出されない`（曖昧パターン非採用）

- [ ] **3-2.2（Green）**: 
  - `backend/src/debate/moderation/__init__.py`
  - `backend/src/debate/moderation/ng_patterns.py`: 4 系統パターン定義（business-rules MOD-03 と完全整合）
  - `backend/src/debate/moderation/callback_handler.py`: `check_text_for_ng_patterns(text) -> NgDetection | None` 純関数

- [ ] **3-2.3（Refactor）**: 
  - `domain/results.py` に `NgDetection`（Pydantic、`pattern_id` / `pattern_name` / `matched_text` を持つ）追加
  - main.py の `_convert_strands_event` に NG パターン検出呼び出しを追加（chunk ごとに第 3 層チェック）

- [ ] **3-2.4（PBT 補強）**: `backend/tests/debate/property/test_moderation_property.py`
  - PBT-09: `任意の論理優位ディベート系言い回し（採用パターン 16 種）→ 検出されない`（fast-check 風 Hypothesis）
  - PBT-09 逆: `任意の NG-3 / NG-6 リテラル → 必ず検出される`

**完了条件**: `pytest tests/debate/moderation/` + property 全 green、Coverage Line 95%+。

---

### Step 3-3: Memory streamDeliveryResources（CDK Snapshot のみ、T3.2）

**目的**: `infra/lib/debate-stack.ts` に Memory `streamDeliveryResources` + S3 Memory Export Bucket + Glue Crawler を追加。**実デプロイは行わず CDK Snapshot fixture を更新するのみ**。

- [ ] **3-3.1（Red）**: `infra/test/debate-stack.test.ts` に test 追加
  - test: `S3 MemoryExportBucket が KMS + Lifecycle 30/90/365 日で定義される`
  - test: `Memory が streamDeliveryResources で MemoryExportBucket を参照する`（Phase 3 では `streamDeliveryResources` API を CfnMemory 直接設定で対応、L2 が未対応の場合は L1 fallback）
  - test: `Glue CfnCrawler が cron(0 1 * * ? *) で定義される`
  - test: `SSM `/yudane/dev/debate/memory-export-bucket-arn` が出力される`（Phase 3 で 7 個目を追加）

- [ ] **3-3.2（Green）**: `infra/lib/debate-stack.ts` 拡張
  - `aws_s3.Bucket MemoryExportBucket`（KMS + BlockPublicAccess + Lifecycle: Standard → IA(30d) → Glacier(90d) → Expire(365d) + versioned）
  - Memory に `streamDeliveryResources` 追加（aws-cdk-lib L2 で対応していない場合は CfnMemory プロパティ直書き）
  - `aws_glue.CfnDatabase` + `aws_glue.CfnCrawler`（cron 1:00 UTC daily、IAM Role 付き）
  - `aws_iam.Role memoryExportRole`（S3 PutObject + KMS Encrypt 権限）
  - SSM 出力 `memory-export-bucket-arn` を 6 → 7 個に拡張

- [ ] **3-3.3**: Snapshot fixture を再生成（cdk-nag green を確認後）

**完了条件**: `vitest run infra/test/debate-stack.test.ts` 全 green、Snapshot 差分 OK、cdk-nag green。**実 AWS デプロイは行わない**。

---

## 2. Phase 4 タスク（custom Memory Strategy + PBT 全面適用）

### Step 4-1: custom Memory Strategy 抽出プロンプト設計（T4.1）

**目的**: M-1 / M-2 軸の翻意パターンを構造化抽出するためのプロンプトを `prompts/m1_m2_axis_extractor.py` で実装。Bedrock Haiku 4.5 で抽出 → Memory custom Strategy に保存される設計（実 deploy は AWS デプロイ前提のため未実施、抽出プロンプトとパース純関数のみ実装）。

- [ ] **4-1.1（Red）**: `backend/tests/debate/prompts/test_m1_m2_axis_extractor.py`
  - test: `M1_M2_EXTRACTION_PROMPT_TEMPLATE が conversation_history と output_schema を含む`
  - test: `parse_m1_m2_extraction(json_response) で `{"axis":"...", "outcome":"...", "turn":N}` 形式の結果を返す`
  - test: `不正な JSON 応答で `M1M2ExtractionError` を raise`
  - test: `axis 値が 'fact' / 'psychology' / 'reward' 以外で `M1M2ExtractionError`
  - test: `outcome 値が 'agreed' / 'refused' / 'ongoing' 以外で `M1M2ExtractionError`

- [ ] **4-1.2（Green）**:
  - `backend/src/debate/prompts/m1_m2_axis_extractor.py`: M1_M2_EXTRACTION_PROMPT_TEMPLATE + `parse_m1_m2_extraction()` 純関数
  - `domain/results.py` に `M1M2Extraction` Pydantic + `M1M2ExtractionError` 例外追加

- [ ] **4-1.3（Refactor）**: `compose.py` の m1_psychology_axis block で `m1m2_extracted_summary` に抽出結果を反映する経路を **存在のみ確認**（Phase 4 では空のままだが API は完成）

**完了条件**: `pytest tests/debate/prompts/test_m1_m2_axis_extractor.py` 全 green。

---

### Step 4-2: custom Memory Strategy CDK Snapshot 追加（T4.2）

**目的**: `infra/lib/debate-stack.ts` の Memory に custom Strategy `m1_m2_axis_extractor` を **コメントアウトを外して有効化**（CDK Snapshot fixture 更新のみ、実デプロイなし）。

- [ ] **4-2.1（Red）**: `infra/test/debate-stack.test.ts` に test 追加
  - test: `Memory が CustomMemoryStrategy 'm1_m2_axis_extractor' を含む`
  - test: `CustomMemoryStrategy の namespace が '/user/m1m2/{actorId}/' 形式`
  - test: `CustomMemoryStrategy の modelId が SSM 経由（または既定 'anthropic.claude-haiku-4-5'）`

- [ ] **4-2.2（Green）**: `debate-stack.ts` の Memory に `MemoryStrategy.usingSelfManaged()` または custom 相当の Strategy を追加
  - aws-cdk-lib L2 で `MemoryStrategy.custom()` 相当が利用可能なら使用、未対応なら `CfnMemory.MemoryStrategyProperty.customMemoryStrategy` で直書き

- [ ] **4-2.3**: Snapshot fixture を再生成

**完了条件**: `vitest run infra/test/debate-stack.test.ts` 全 green、Snapshot 差分 OK。

---

### Step 4-3: PBT 全面適用（T4.4、残り 4 properties）

**目的**: Phase 1 + 2 で実装済みの 6 properties（PBT-02 / PBT-03 / PBT-07 / PBT-08）に加えて、残り 4 properties = **NFR-PBT-DEBATE-01〜10 の全カバレッジ達成**。

- [ ] **4-3.1**: PBT-01 同型同値（Idempotency）
  - `backend/tests/debate/property/test_idempotency_property.py`
  - 任意の同一 client_session_id で `increment_refuse_count` を 2 回呼んでも DDB 状態が変わらない（既に Phase 1 で部分実装、強化）

- [ ] **4-3.2**: PBT-04 順序非依存（Commutative）
  - `backend/tests/debate/property/test_commutative_property.py`
  - 任意の順序で stress signals を渡しても stress_level の結果が同じ（信号集合の順序非依存性）

- [ ] **4-3.3**: PBT-05 冪等性（Memory write）
  - `backend/tests/debate/property/test_memory_idempotency_property.py`
  - 同一 `(actor_id, session_id, turn)` に対する `record_event` を 2 回呼んでも Memory state が変わらない（LocalMemoryStore でテスト）

- [ ] **4-3.4**: PBT-06 負荷不変条件
  - `backend/tests/debate/property/test_load_invariant_property.py`
  - 同時 100 セッション分の `compose_debate_prompt` を asyncio.gather で並列実行しても、各セッションの結果が独立（純関数性）

- [ ] **4-3.5**: PBT-09 / PBT-10（モデレーション）→ Phase 3-2 で実装済（拡張）
  - 既存 `test_moderation_property.py` を拡張、より広範な NG パターンと正常文で検証

**完了条件**: `pytest backend/tests/debate/property/ -v` で全 PBT-01〜10 が pass、各 property 50+ examples 検証。

---

## 3. Phase 6 タスク（決勝 Readiness 仕上げ、AWS デプロイ非依存範囲）

### Step 6-1: Unit-3 統合テスト IT-XX（T6.1）

**目的**: 既存 E2E-01 に加えて、IT-DEBATE-01〜03 を実装（クールダウンサイクル / graceful shutdown / モデレーション の 3 シナリオ）。

- [ ] **6-1.1（Red + Green）**: `mobile/src/test/integration/`
  - `it-debate-01-cooldown-cycle.test.ts`: 連続 3 回拒否 → クールダウン → 自然解除 → 1 にリセットの完全サイクル
  - `it-debate-02-graceful-shutdown.test.ts`: 80 秒経過で graceful shutdown → サマリ表示 → session_complete
  - `it-debate-03-moderation-block.test.ts`: NG-6 含む応答 → moderation_blocked event → UI 表示

**完了条件**: `vitest run src/test/integration/` 全 green。

---

### Step 6-2: cdk-nag 確認（T6.2）

**目的**: Phase 3-3（Memory streamDeliveryResources + S3 Bucket）/ Phase 4-2（custom Strategy）追加後の `debate-dev-stack` で cdk-nag green を最終確認。

- [ ] **6-2.1**: `npx cdk synth DebateStack -c env=dev` で synth 成功
- [ ] **6-2.2**: cdk-nag suppression が必要なら理由コメント付きで追加（aws-solutions-iam5 / aws-solutions-s1 等）
- [ ] **6-2.3**: Snapshot fixture が最終形態で安定

**完了条件**: `vitest run infra/test/debate-stack.test.ts` の cdk-nag テストが green、Snapshot 差分 0。

---

### Step 6-3: 決勝デモシナリオドキュメント（T6.5、AWS デプロイ前提部分は除外）

**目的**: 決勝デモ当日のシナリオ + リハーサル手順をドキュメント化。AWS デプロイ前提部分（実 prd 動作確認 / カナリア切替）は記載のみで実機実行は別フェーズ。

- [ ] **6-3.1**: `aidlc-docs/construction/unit-3-debate/code/demo-scenario.md` 新規作成
  - シナリオ A: 悠介さんがリール「買わない」→ 1 分論破で翻意 → AffirmScreen（M-1 fact 軸）
  - シナリオ B: 深夜帯 + ストレス mid → M-2 reward 軸併走でご褒美論破 → 翻意
  - シナリオ C: 連続 3 回拒否 → クールダウン → セーフガード作動（NG-6 滑落防止のデモ）
  - シナリオ D: NG-6 パターン検出 → moderation_blocked event → 倫理担保のデモ
  - 各シナリオに「予選版（ローカルモード）」と「決勝版（dev/prd）」の差分を明記

**完了条件**: `demo-scenario.md` が作成され、シナリオ 4 種が完成。

---

## 4. 完了基準（Phase 3+4+6 全体）

- [ ] Phase 3: Step 3-1 / 3-2 / 3-3 すべて [x]、Backend 追加 50+ tests green、CDK Snapshot 安定
- [ ] Phase 4: Step 4-1 / 4-2 / 4-3 すべて [x]、PBT 全面適用 10 properties / 500+ examples
- [ ] Phase 6: Step 6-1 / 6-2 / 6-3 すべて [x]、IT-DEBATE-01〜03 + cdk-nag + デモシナリオ完成
- [ ] 累計テスト 350+（Phase 1-4+6 合算）、回帰なし、diagnostics 0
- [ ] 生成ドキュメント追加 8 件以上（Phase 3〜6 各サマリ + デモシナリオ）

---

## 5. スコープ外（AWS デプロイ前提のため保留）

| Phase | タスク | 理由 |
|---|---|---|
| Phase 1 Step 8 | dev デプロイ + EAS Build + 実機疎通 | ユーザー指示で保留 |
| Phase 5 全部 | RuntimeEndpoint canary deploy | AWS deploy 前提 |
| Phase 6 T6.3 | 性能テスト（同時 100 セッション、Bedrock Throttling）| 実 dev 環境で実行必要 |
| Phase 6 T6.4 | カナリアリリース（6/25 staging 30 分）| 実 staging deploy 前提 |

これらは決勝直前のデプロイフェーズで個別承認のうえ実施。

---

## 6. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| Memory `streamDeliveryResources` の aws-cdk-lib L2 サポートが不完全 | 中（3-3）| `CfnMemory` 直書き or backlog 化（B-310 候補）|
| `MemoryStrategy.custom()` の API が未確定 | 中（4-2）| `CfnMemory.MemoryStrategyProperty.customMemoryStrategy` で直書き、L2 利用は決勝後に再評価 |
| graceful shutdown 80s の実装が Strands Agent の SDK 仕様に合致しない | 中（3-1）| 純ロジック側で elapsed_sec チェックを実装、`agent.stream_async` の中断は asyncio.CancelledError で処理 |
| PBT property 4 種追加で実行時間が長くなる | 低（4-3）| 各 50 examples、CI で `--no-cov` + 10 分以内に収める |

---

## 7. ハッカソン評価軸へのインパクト

| 評価軸 | Phase 3+4+6 完了による積み増し |
|---|---|
| ビジネス意図の明確さ | Phase 4 の custom Memory Strategy で「個別最適化された M-1/M-2 軸抽出」が物理層に降りる、ダメ化 3 段メカニズムの自動学習が完成 |
| Unit 分解の適切さ | Phase 3 で graceful shutdown / S3 Memory Export / 多層モデレーションの 3 系統が完成、12 LC のうち未実装は LC-D-11 S3 Export の Athena view 詳細のみ |
| 創造性とテーマ適合性 | Phase 4 PBT 全面で 10 properties / 500+ examples、ハッカソン基準「Unit 分解の適切さ」「創造性とテーマ適合性」を property レベルで保証 |
| ドキュメント品質 | Phase 6 デモシナリオドキュメント + cdk-nag 安定化 + IT-DEBATE-01〜03 で完全 traceable |
| AI-DLC プロセス | Phase 1〜6 の TDD サイクル全 Step を AI が Plan に従って完遂、AI-DLC 5/10 書類審査 → 6/26 決勝までの一貫性 |
