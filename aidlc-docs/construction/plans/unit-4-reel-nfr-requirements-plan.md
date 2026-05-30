# Unit-4 Reel — NFR Requirements Plan

> Construction Phase / Per-Unit Loop / Unit-4 Reel の非機能要件（NFR）計画。Unit-4 固有の品質目標と、Unit-1 から継承する横断 NFR 基盤への適合を確定する。
> 参照: [Functional Design](../reel/functional-design/) / [要件書 §6](../../inception/requirements/requirements.md) / [Unit-1 NFR Requirements](../unit-1-platform/nfr-requirements/) / [tech.md](../../../.kiro/steering/tech.md) / [api-contracts.md](../../../.kiro/steering/api-contracts.md)
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / NFR Requirements / 担当: Member C

---

## 0. 位置づけ（Unit-4 の NFR スコープ）

Unit-4 Reel は **コア 3 Unit の 1 つ**（UC-02）。本ステージでは Functional Design で確定した 7 アルゴリズム（ALG-RANK / BOOST / PITCH・LABEL / CATALOG / TRANSITION / LINK / GESTURE）に対し、性能・スケール・可用性・セキュリティ・テスタビリティ・観測・A11y の非機能目標を確定する。

技術スタックの大枠は要件書 §7 / tech.md で確定済み、横断 NFR 基盤（ApiClient タイムアウト・PII マスキング・EMF 観測・カバレッジ規約・SECURITY 基盤）は **Unit-1 で確定済み**。本ステージは「Unit-4 が継承する基盤 + Unit-4 固有で上乗せする NFR」を確定する。

### 要件書 §6 由来の Unit-4 関連目標（既定の出発点）

| 出典 | 目標 | 関連 ALG |
|---|---|---|
| §6.2 | リール描画 60fps 維持 | M-03 / frontend |
| §6.2 | Share 受領 → 商品メタ表示 2 秒以下（Creators ウォームキャッシュ前提）| ALG-CATALOG |
| §6.1 | エージェント推薦（リール経由）の Amazon 遷移率（北極星補助指標）| ALG-TRANSITION テレメトリ |
| §6.5 | PBT-02/03/04（round-trip / invariant / idempotency）| ALG-LINK / ALG-RANK / ALG-TRANSITION |

---

## 1. 設計判断のための質問

以下の質問に `[Answer]:` タグで回答してください（推奨は **A**）。回答完了後「done」等でお知らせください。曖昧な回答が残る場合は follow-up clarification を作成します。

### Question 1
リール推薦（`GET /v1/reel`）の **性能目標（レイテンシ）** をどう確定しますか？（ALG-RANK は MVP で購入履歴ベース + 決定論リランク、OpenSearch なし = CL-1 確定）

A) **MVP は p95 800ms / 初回ページ 1s 以内、決勝は p95 500ms 目標**: フィード API のサーバー処理を MVP で p95 800ms（ダミーカタログ + DynamoDB + キャッシュ前提）、UI 初回描画 1s 以内。深夜ブースト挿入・リランクはインメモリ純関数のため誤差。決勝でベクトル検索導入時も p95 500ms を維持目標 — 推奨（§6.2 60fps と整合、現実的）
B) より厳しく MVP から p95 300ms（高負荷チューニング前提、予選までの実装コスト増）
C) 数値目標を置かず「体感スムーズ」を定性目標にする（計測・回帰防止が弱い）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 2
**Amazon 遷移記録（`POST /v1/amazon-transitions`）の性能・整合性目標**をどうしますか？（ALG-TRANSITION = 冪等 + EXP + Safeguard ゲート、Q6=A 確定）

A) **p95 400ms / 強整合の冪等書き込み / Safeguard ゲート同期**: 遷移記録は p95 400ms 以内。冪等キー `(userId, clientTransitionId)` で条件付き書き込み（DynamoDB 条件式）、月間カウントと EXP を原子的に更新。Safeguard 判定は同期（遷移前ゲート）。EXP の嗜好ベクトル供給（B-08）は非同期で可 — 推奨
B) 遷移記録を非同期化（キュー経由）してレイテンシ最小化（実装複雑・EXP 即時反映が難しく US-02-02 AC-4 の即時トーストとズレる）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3
Unit-4 の **スケーラビリティ前提（負荷・同時実行）** をどう置きますか？（ハッカソン規模、Unit-1 と整合）

A) **ハッカソン規模（〜10K DAU、ピーク数十 req/s）を MVP 前提、決勝もスパイクは深夜帯集中を想定**: Lambda 同時実行は AWS 既定の範囲内、DynamoDB は On-Demand（PAY_PER_REQUEST）、カタログは Redis キャッシュ TTL 6h で Creators API レート制限を吸収。本格的なオートスケール設計は将来プロダクト化時（backlog）— 推奨
B) 予選/決勝デモ（数ユーザー同時）のみを前提に capacity 設計しない（デモ事故リスクをQ別で許容）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4
Unit-4 の **可用性・フォールバック方針**をどうしますか？（Unit-1 は Q6=B で共通フォールバック土台を持たず、各 Unit が縮退を実装）

A) **依存別の優雅な縮退（graceful degradation）**: ① カタログ外部 API / Creators 失敗 → ダミー/キャッシュ済みカタログにフォールバック（ALG-CATALOG）② カレンダー ctx 不在 → 通常推薦（Q10=A）③ LLM ラベル生成失敗 → テンプレートフォールバック（Q4=A）④ ストレス推定不可 → `low` 扱いでブースト抑止（安全側）⑤ Safeguard 状態取得失敗 → fail-closed（遷移をブロック、SECURITY-09）— 推奨
B) フォールバックは最小限（外部 API 失敗時はエラー表示のみ、縮退しない）。実装は軽いがデモ耐性が低い
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5
Unit-4 の **カバレッジ目標**をどう設定しますか？（tech.md 全体目標 Line 80%+ / Branch 70%+、Unit-1 は純ロジック 95%/90%）

A) **ロジック層を高め・UI 層を全体目標**: ① B-03 推薦・リランク（ALG-RANK/BOOST）と B-13 遷移（ALG-TRANSITION）と B-10 リンク（ALG-LINK）は純ロジック中心のため Line 90%+ / Branch 85%+ ② B-11 カタログ（アダプタ/キャッシュ）Line 85%+ ③ M-03 ReelScreen（UI）は tech.md 全体目標（Line 80%+ / Branch 70%+）で E2E 補完 — 推奨
B) 全層一律 tech.md 目標（80%/70%）。推薦・遷移の重要ロジックのバグ検出力が落ちる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6
Unit-4 の **PBT（Property-Based Testing）対象と性質**をどう割り当てますか？（PBT-01〜10 全面適用、Functional Design で性質候補は記載済み）

A) **ALG ごとに性質を割当 + example 併存**: ① ALG-LINK = round-trip（PBT-02、Special Link ↔ ASIN 逆抽出）② ALG-RANK = invariant（PBT-03、決定論・score=Σcomponents・NG 除外）③ ALG-TRANSITION = idempotency（PBT-04、同一 clientTransitionId で EXP 二重加算なし・上限超過なし）④ ALG-BOOST = 発火条件の真理値表（メタモルフィック）⑤ カーソル encode/decode = round-trip ⑥ ドメインジェネレータ（PBT-07、購入履歴/価格/ストレス/時刻の現実的生成器）。fast-check（TS）+ Hypothesis（Py）、shrinking + seed ログ必須（PBT-08）、example-based 併存（PBT-10）— 推奨
B) 主要 1〜2 個（ALG-LINK round-trip と ALG-TRANSITION idempotency）のみに絞る（網羅性は落ちるが工数最小）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 7
Unit-4 の **観測（メトリクス・テレメトリ）** で何を計測しますか？（Unit-1 は EMF 土台 + 命名規約のみ提供、メトリクスカタログは各 Unit が定義 = Q3=B）

A) **北極星補助指標 + Reel 固有メトリクスを S-04 カタログに追記**: ① `reel.viewed` / `reel.swiped`（left/right）/ `reel.double_tap` / `reel.amazon_tap`（北極星: リール経由 Amazon 遷移率）/ `reel.boost_shown`（深夜ブースト表示）/ `reel.label_fallback`（LLM フォールバック率）② サーバーメトリクス: フィード生成レイテンシ / カタログキャッシュヒット率 / 遷移 409（Safeguard block）率。命名は `reel.<verb>`（api-contracts §12.2）、PII を次元・properties に含めない — 推奨
B) 北極星（`reel.amazon_tap`）のみ計測、その他は決勝で追加（初期の可視化が薄い）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 8
Unit-4 固有の **セキュリティ NFR の重点**をどう確定しますか？（SECURITY-01〜15 は Unit-1 基盤を継承、Unit-4 固有の上乗せ）

A) **認可・遷移ゲート・外部 API・モデレーションに重点**: ① SECURITY-08（遷移/フィードで JWT sub 一致、ストレス値はクライアント非信用）② SECURITY-11（遷移前 Safeguard ゲート必須、fail-closed）③ SECURITY-05（cursor/limit/body の契約検証）④ SECURITY-09（Creators API 失敗の詳細秘匿）⑤ NG-6/NG-8（ラベル/コピーのモデレーション、Special Link 短縮禁止）⑥ Creators API 認証情報は Secrets Manager（ハードコード禁止）— 推奨
B) Unit-1 基盤の継承のみで Unit-4 固有の上乗せはしない（遷移ゲート・モデレーションの重点が薄れる）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 9
Unit-4 の **マイルストーン別達成目標（MVP 5/30 / 決勝 6/26）** の切り分けをどうしますか？

A) **MVP 必須 / 決勝最適化の段階達成**（Unit-1 Q7=A と整合）:
- MVP 必須: 推薦（購入履歴ベース + リランク）/ 3 ジェスチャー / 確認オーバーレイ / 遷移記録（冪等 + EXP + Safeguard ゲート）/ Special Link（dev 仮リンク）/ ダミーカタログ / 主要 PBT（ALG-LINK/RANK/TRANSITION）/ 北極星テレメトリ / 60fps / フィード p95 800ms
- 決勝最適化: ベクトル検索（B-204）/ Creators API 本番接続（Approved Mobile App 承認後）/ フィード p95 500ms / 全 PBT・全メトリクス / A11y（SR・動的フォント）
— 推奨
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 10
Unit-4 の **A11y（アクセシビリティ）目標**をどうしますか？（縦型スワイプ + ジェスチャー中心 UI のため操作代替が論点）

A) **ジェスチャー操作にボタン代替 + コントラスト AA + SR ラベル**: ① 左/右スワイプ・ダブルタップに**ボタン等の代替操作**を用意（スワイプ不能ユーザー向け）② Unit-1 のテーマトークン（WCAG 2.2 AA 相当）を継承 ③ カード画像・ラベルにスクリーンリーダー用テキスト。MVP はコントラスト + ボタン代替、決勝で SR フル対応 — 推奨
B) コントラスト（AA）のみ、ジェスチャー代替や SR は決勝以降（スワイプ専用 UI は操作代替が乏しくなる）
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問（現在地）
- [x] Functional Design 成果物の分析（domain-entities / business-logic-model / business-rules / frontend-components 読込）
- [x] NFR Requirements Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q10 に回答（全 A 確定、曖昧さなし）
- [x] 回答の分析・曖昧さ検出 → clarification 不要（全 A）
- [x] ユーザーが Clarification に回答（曖昧さがある場合）— N/A

### Part 2: NFR 成果物の生成（承認後）
- [x] `aidlc-docs/construction/reel/nfr-requirements/nfr-requirements.md`
  - 性能 / カバレッジ / セキュリティ / テスタビリティ(PBT) / 可用性 / 観測 / A11y / マイルストーン別達成目標
- [x] `aidlc-docs/construction/reel/nfr-requirements/tech-stack-decisions.md`
  - Unit-1 確定スタックの Unit-4 における実体化（OpenSearch MVP 見送り / Bedrock ラベル生成 / DynamoDB テーブル前提 / Redis キャッシュ / Secrets Manager）
- [x] 自己レビュー（整合性・要件充足・診断エラー）— diagnostics 0、FD/要件書 §6/Unit-1 基盤と整合
- [x] 完了メッセージ提示 + 承認ゲート（次ステージ = NFR Design）— 2026-05-30 承認（再レビュー 5 件修正後）

---

## 3. Extension 適合の予定（NFR Requirements 段階での該当性）

| Extension | 本ステージでの扱い |
|---|---|
| SECURITY-05/08/09/11 | Unit-4 固有の重点（遷移ゲート・認可・外部 API 秘匿・入力検証）を NFR-SEC として明文化 |
| SECURITY-01/02/03/06/10/15 | Unit-1 基盤を継承（Unit-4 で再実装しない、継承を明記） |
| NG-6 / NG-8 | ラベル/コピーモデレーション・Special Link 短縮禁止を NFR として担保 |
| PBT-02/03/04/07/08/10 | §1 Q6 で ALG ごとに性質割当、ジェネレータ・shrinking・example 併存を規定 |
| SECURITY-07（VPC）| Infrastructure Design で確定（本ステージでは N/A） |
| SECURITY-12（認証）| Unit-2 の責務（本 Unit では N/A） |
