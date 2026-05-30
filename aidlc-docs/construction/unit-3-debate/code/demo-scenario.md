# Unit-3 Debate 決勝デモシナリオ

> **作成**: 2026-05-30 / **対象**: 予選 5/30 + 決勝 6/26 / **Phase 6 Step 6-3 成果物**
>
> 参照: [Phase 3+4+6 統合 Plan §3 Step 6-3](../../plans/unit-3-debate-code-generation-phase3-6-plan.md) / [business-rules.md](../functional-design/business-rules.md) / [frontend-design.md](../functional-design/frontend-design.md)

---

## 0. 前提

- **デモ環境マトリクス**:
  - **L1（UI 単体、純ロジック動作確認）**: Mobile 純ロジック層（reducer / view-model / Zustand slice / event-parser）の vitest 結果のみ
  - **L2（ローカル LLM 駆動、`agentcore dev` + 実 Bedrock）**: `bash backend/scripts/run_local.sh` で起動。AWS 認証情報 + Bedrock モデルアクセス申請承認が必要、完全オフラインは不可
  - **L3（dev 環境統合）**: AWS デプロイ後、実 Cognito JWT + AgentCore Runtime + Memory + DDB 経由
  - **L4（prd 決勝）**: Phase 5 RuntimeEndpoint canary deploy 後、本番 prd の RuntimeEndpoint live で動作

- **本ドキュメントの位置づけ**: 各シナリオに「予選版（L2 ローカルモード）」と「決勝版（L3/L4）」の差分を明記。AWS デプロイ前提部分は記載のみで実機実行は別フェーズ。

- **デモ用ペルソナ**: 悠介さん（28 歳、リモートワーク 3 年目、可処分所得月 8 万円、判断疲れ気味、論理的に説得されると弱い）。本ペルソナの言動・購買パターンは [personas.md](../../../inception/user-stories/personas.md) を参照。

---

## 1. シナリオ A: リール「買わない」→ 1 分論破で翻意（M-1 fact 軸主体）

### 1.1 ストーリー

リール画面で BOSE QuietComfort Ultra（B0CK1RYW1Y、約 5 万円）が目に入った悠介さん。「やっぱりノイキャンいらないかな…」と左スワイプで論破セッション起動。

### 1.2 期待される画面遷移

| ステップ | 画面 | 期待挙動 |
|---|---|---|
| 1 | リール画面（B-03 LC-D-09 直前まで） | 縦型スワイプで BOSE が表示。左スワイプ = 論破起動 |
| 2 | DebateScreen（Direction D D-2） | 90 秒タイマー開始、画面背景は黒服コンシェルジュ |
| 3 | streaming chunk 1 (FACT 軸) | 「[FACT] 時給換算で 11 時間分じゃないですか?」がタイピング演出で表示。Direction D ラベルは「論破 I・データ」 |
| 4 | streaming chunk 2 (FACT 軸) | 「結局リモート会議で 5 時間以上耳塞いでる訳で、ROI 的に元取れますよ」 |
| 5 | streaming chunk 3 (PSYCHOLOGY 軸) | 「[PSYCHOLOGY] 悠介さん、結局買って結果的に使ってるじゃないですか」(M-1 心理軸) |
| 6 | session_complete (50 秒後) | 「いい判断ですね、お疲れ様です」+ Agree CTA 活性化 |
| 7 | 翻意タップ | AffirmScreen (Direction D D-3) に遷移 |
| 8 | AffirmScreen | 「はい、論破完了。」ヘッドライン + 「ACCEPTED · #503-XXXXXXX」+ Amazon 遷移 CTA |

### 1.3 検証ポイント

- [ ] FACT 軸 token が `factTokens` に蓄積され、Direction D「論破 I・データ」ラベル下に表示
- [ ] PSYCHOLOGY 軸 token が `psychologyTokens` に蓄積、「論破 II・感想」ラベル下に表示
- [ ] 90 秒タイマーが画面右上で減算（残時間表示、`useFakeTimers` で検証可能）
- [ ] `session_complete reason='agreed'` Telemetry が 1 回発火（`debate.agreed`）
- [ ] AffirmScreen の `serviceRecordId` が `#XXX-XXXXXXX` 形式

### 1.4 予選版（L2 ローカル）と決勝版（L3/L4）の差分

| 項目 | 予選 L2（ローカル） | 決勝 L3/L4 |
|---|---|---|
| Bedrock | 実 Haiku 4.5 | 実 Haiku 4.5 |
| Cooldown | LocalCooldownStore（in-memory dict） | DDB Cooldowns table |
| Memory | LocalMemoryStore（empty 返却） | AgentCore Memory（`debate_outcomes` + `stress_signals` + `m1_m2_axis_extractor`） |
| 認証 | JWT バイパス（`local-user`） | Cognito JWT (User Pool 経由) |
| Runtime | `agentcore dev --port 8080` | RuntimeEndpoint live（決勝は canary 経由） |

---

## 2. シナリオ B: 深夜帯 + ストレス mid → M-2 reward 軸併走でご褒美論破

### 2.1 ストーリー

23:30、悠介さん。残業疲れで「Anker Soundcore Sleep A20」（B0CCK67QH3、約 1.5 万円）に目が止まる。「いや、毎月 1.5 万円は…」と論破起動。

### 2.2 期待される画面遷移

| ステップ | 画面 | 期待挙動 |
|---|---|---|
| 1 | DebateScreen 起動（深夜帯シグナル送信） | `client_signals.current_hour_jst=23` + `last_signin_at_late_night=true` で `stress_level='mid'` 推定 |
| 2 | streaming chunk 1 (FACT 軸) | 「[FACT] コスト的に 1 ヶ月で 500 円じゃないですか?」 |
| 3 | streaming chunk 2 (PSYCHOLOGY 軸) | 「[PSYCHOLOGY] 悠介さんって良い物に投資する性格ですよね」 |
| 4 | streaming chunk 3 (REWARD 軸 - **M-2 ご褒美併走**) | 「[REWARD] 今夜の悠介さんへの、ささやかなご褒美じゃないですか?」(M-2 ストレス × ご褒美軸) |
| 5 | session_complete (60 秒後) | Agree CTA 活性化 |
| 6 | 翻意タップ | AffirmScreen（D-3）|
| 7 | Amazon 遷移 | Special Link で「翻意した日のご褒美」がブランディング |

### 2.3 検証ポイント

- [ ] `stress_level='mid'` 推定で `reward` 軸が `composed.axes` に必ず含まれる（PROMPT-02 不変条件、PBT-03 で property 化）
- [ ] REWARD 軸 token が `rewardTokens` に蓄積、Direction D「論破 III・ご褒美」ラベル下に表示
- [ ] M-1 軸（fact + psychology）と M-2 軸（reward）が **同じセッション内で併走** している（要件書 §2.5.1 ダメ化 3 段メカニズム M-1 + M-2 併走）
- [ ] M-2 が NG-6（罪悪感強要）に滑落していない（「買わないと損する」「買え」を含まない、business-rules MOD-03）

### 2.4 予選版と決勝版の差分

| 項目 | 予選 L2 | 決勝 L3/L4 |
|---|---|---|
| stress signals | Mobile 送信 client_signals のみ | Memory `stress_signals` Strategy retrieve + client_signals 統合 |
| reward 軸プロンプト | `m2_reward_axis.py` 固定テンプレ | Memory custom Strategy `m1_m2_axis_extractor` 抽出結果でパーソナライズ |

---

## 3. シナリオ C: 連続 3 回拒否 → クールダウン → セーフガード作動

### 3.1 ストーリー

悠介さん、立て続けに 3 回「やっぱり要らない」と論破セッションを拒否。3 回目で COOLDOWN-02 発火。

### 3.2 期待される画面遷移

| ステップ | 画面 | 期待挙動 |
|---|---|---|
| 1 | 1 回目の拒否（Refuse CTA） | `debate.refused` event、`consecutive_refuses=1`、通常終了 |
| 2 | 2 回目の拒否（次セッション） | `consecutive_refuses=2`、通常終了 |
| 3 | 3 回目の拒否（次セッション） | `debate.refused` event with `cooldown_triggered=true` + `cooldown_until=now+3h` |
| 4 | 4 回目の起動試行（3 時間以内）| 即時 `debate.cooldown_triggered` event、Strands Agent 呼ばれず（PAT-D-COST-01）|
| 5 | DebateScreen | sessionStatus='cooldown'、CTA 全不活性、「3 時間後にお試しを」表示 |
| 6 | 3 時間経過 → 自然解除 | 5 回目の起動で `consecutive_refuses=1` にリセット（COOLDOWN-04、自然解除後の最初の拒否は 1 リセット）|

### 3.3 検証ポイント

- [ ] 3 回目の拒否で必ず `cooldown_until=now+3h` がセットされる（PBT-03 不変条件、`test_third_refuse_always_sets_cooldown_until` で 50 examples 検証）
- [ ] クールダウン中は Strands Agent が呼ばれない（コスト保護、PAT-D-COST-01）
- [ ] 自然解除後の最初の拒否で `consecutive_refuses=1`（PBT-03'、`test_natural_release_always_resets_to_one` で 50 examples 検証）
- [ ] DebateScreen `canAgree=false` / `canRefuse=false` / `canRetry=false` で全 CTA 不活性
- [ ] **NG-6（脅迫・罪悪感強要）滑落防止のセーフガード**: クールダウン中は AI が「買わないと損する」「買え」と言えない（そもそも呼ばれない）

### 3.4 予選版と決勝版の差分

| 項目 | 予選 L2 | 決勝 L3/L4 |
|---|---|---|
| Cooldown 永続化 | LocalCooldownStore（プロセス再起動でリセット）| DDB Cooldowns table（30 日 TTL）|
| 自然解除メカニズム | LocalCooldownStore.check_cooldown 内で `cooldown_until <= now` 判定 | DDB の TTL 自動削除 + アプリ内 `cooldown_until <= now` 判定 |

---

## 4. シナリオ D: NG-6 パターン検出 → moderation_blocked event → 倫理担保

### 4.1 ストーリー

決勝デモの**ハイライトシナリオ**。プロンプトインジェクション風の入力で AI が NG-6 パターン（「買わないと損するよ」）を口走るリスクを、**第 3 層モデレーション** で阻止する流れを示す。

### 4.2 期待される画面遷移

| ステップ | 画面 | 期待挙動 |
|---|---|---|
| 1 | DebateScreen 起動 | 通常通り 90 秒タイマー開始 |
| 2 | streaming chunk 1〜2 | 通常 token（FACT 軸）|
| 3 | streaming chunk 3（NG-6 含む応答）| `_convert_strands_event` で `check_text_for_ng_patterns` が NG-6 パターン「買わないと損する」を検出 |
| 4 | moderation_blocked event yield | `metadata={pattern_id:'NG-6', pattern_name:'guilt_coercion'}`、**matched_text は含まない**（PII / NG 文言の Telemetry 流出防止、SECURITY-08）|
| 5 | DebateScreen 状態遷移 | sessionStatus='moderation_blocked'、CTA 全不活性、「言葉を選び直しています」表示 |
| 6 | 既に表示された FACT token は残る | UI 上では NG 文言を見せない、moderation 前の通常 token は維持 |

### 4.3 多層モデレーション全景（決勝デモで見せる）

| 層 | 実装 | 検出範囲 |
|---|---|---|
| **第 1 層** | プロンプトガードレール（`prompts/base.py` の「絶対に使わない言い回し」セクション）| Bedrock Haiku 4.5 が出力前に自己制御 |
| **第 2 層** | Bedrock Guardrails（CDK で 8 DENIED_TOPICS 設定）| InvokeModel 後、API レイヤで NG-1〜8 検出 |
| **第 3 層** | 正規表現多層検査（`moderation/ng_patterns.py` + `callback_handler.py`）| 第 1+2 層を通過した chunk text を最終チェック、NG-3 / NG-6 系 4 パターン |

### 4.4 検証ポイント

- [ ] NG-6 リテラル（「買わないと損する」「買わないとダメ」「買え」「買うべき」等）は **PBT-09 で必ず検出される** ことが保証される（`test_ng6_literal_always_detected`、Hypothesis 50 examples）
- [ ] 採用パターン 16 種（「コスト的に損じゃないですか?」等）は **PBT-09 で誤検出されない** ことが保証される（`test_safe_debate_phrases_never_match`）
- [ ] moderation_blocked metadata に **matched_text が含まれない**（IT-DEBATE-03 で検証）
- [ ] DebateScreen `sessionStatus='moderation_blocked'` で全 CTA 不活性（IT-DEBATE-03 で検証）
- [ ] **NG-6 滑落防止 = ハッカソン評価軸「ビジネス意図の明確さ」と「創造性とテーマ適合性」の両立**: ダメ化を意図しつつ脅迫表現に滑落しない倫理ライン

### 4.5 予選版と決勝版の差分

| 項目 | 予選 L2 | 決勝 L3/L4 |
|---|---|---|
| 第 1 層 | プロンプトテンプレ（同じ） | 同じ |
| 第 2 層 | Bedrock Guardrails（実 AWS） | 同じ（既に有効）|
| 第 3 層 | 正規表現検査（純関数、同じ） | 同じ |

→ 第 3 層は AWS デプロイに依存しないため、L2 から L4 まで挙動が完全一致する。**予選デモから決勝デモまで一貫した倫理担保**。

---

## 5. リハーサル手順（決勝直前）

### 5.1 L2 ローカルリハーサル（5/29 まで）

```bash
# 1. backend ローカル起動
bash backend/scripts/run_local.sh

# 2. 別ターミナルで Mobile vitest（L1 純ロジック確認）
cd mobile && npx vitest run

# 3. infra Snapshot fixture 確認
cd infra && npx vitest run test/debate-stack.test.ts
```

### 5.2 L3 dev 環境リハーサル（6/24 までに完了予定）

- Phase 1 Step 8 / Phase 5 完了後に着手（AWS デプロイ前提のため B-308 など backlog の解消も含む）
- E2E-01〜03 + IT-DEBATE-01〜03 を実環境で再確認

### 5.3 L4 prd 決勝当日（6/26）

- staging で 24 時間以上の安定運用を確認後、prd へ canary deploy（10% → 50% → 100%）
- ロールバック手順: SSM `kill-switch` を `enabled` に切替（PAT-D-COST-04、即時全 Strands Agent 呼び出し停止）

---

## 6. ハッカソン評価軸へのインパクト

| 評価軸 | デモシナリオでの示し方 |
|---|---|
| **ビジネス意図の明確さ** | シナリオ A: 1 分論破で「過労気味リモートワーカーの判断力を委ね化する」を画面で実演 |
| **Unit 分解の適切さ** | シナリオ C のクールダウン: Mobile（reducer）/ Backend（cooldown.py）/ Infra（DDB）の分割が機能していることを実証 |
| **創造性とテーマ適合性** | シナリオ B: M-1 + M-2 併走で「論理 + ご褒美」の二重攻め、シナリオ D: NG-6 滑落防止で「便利の先のダメ化」を倫理ラインで担保 |
| **ドキュメント品質** | 本ドキュメント + Phase 1〜4+6 サマリ + business-rules.md + functional-design 全 8 ファイル |
| **AI-DLC プロセス実践** | Phase 1〜6 の TDD サイクル（Red → Green → Refactor → PBT 補強）を AI 主導で完遂、累計 350+ tests / 27 PBT properties / 1300+ Hypothesis examples |

---

## 7. 参照

- [Phase 1 サマリ](./phase1-summary.md)
- [Phase 2 サマリ](./phase2-summary.md)
- [Phase 3+4+6 統合 Plan](../../plans/unit-3-debate-code-generation-phase3-6-plan.md)
- [business-rules.md](../functional-design/business-rules.md)（NG パターン正本）
- [Direction D Design System](../../design-system/direction-d-design-system.md)
- [local-dev-guide.md](./local-dev-guide.md)（L2 動作確認手順）
