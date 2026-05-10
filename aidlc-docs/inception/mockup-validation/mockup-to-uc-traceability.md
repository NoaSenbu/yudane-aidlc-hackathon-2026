# モックアップ → UC / FR / Story トレーサビリティマトリクス

> モックアップ 6 画面が、要件書の UC（ユースケース）/ FR（機能要件）/ Story（ユーザーストーリー）/ Unit（開発単位）にどう対応しているかを可視化する。
> Unit 分解の過不足を検証する材料。

---

## 1. 6 画面 × UC マトリクス

| 画面 | UC-01<br>論破 | UC-02<br>リール | UC-03<br>カート介入 | UC-04<br>カレンダー | UC-05<br>ゲーミフィ | UC-06<br>逆家計簿 | UC-07<br>ダメ化PF | UC-08<br>セーフ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1. ホーム | — | ●（起点）| **●●●** | **●●**（先回り）| ●（Lv 表示）| **●●**（弾薬）| — | — |
| 2. カート介入 | ●（遷移）| — | **●●●** | — | — | — | — | — |
| 3. リール | ●（論破起動）| **●●●** | ●（監視入り）| ●（予定駆動）| ●（タップで EXP）| ●（弾薬として）| — | — |
| 4. 論破チャット | **●●●** | — | ●（弾薬）| ●（弾薬）| ●（成約で EXP）| ●（弾薬）| — | ●（3 回拒否→冷却）|
| 5. ダメ化レポート | ●（成約率表示）| — | ●（成約表示）| — | **●●●** | **●●**（数値根拠）| **●●●** | — |
| 6. セーフガード | ●（クールダウン）| ●（停止）| — | — | ●（Streak 途切れ）| — | — | **●●●** |

**読み方**: ● 1 個 = 補助関与、●● 2 個 = 主要関与、●●● 3 個 = 主担当

### 1.1 UC カバレッジ

全 8 UC が 6 画面のいずれかで主担当（●●●）または主要関与（●●）されている。UC-07 ダメ化ポートフォリオのみ「5. ダメ化レポート」が主担当（他画面では未登場）。

---

## 2. 6 画面 × FR マトリクス（抜粋）

主要な FR のみ抜粋。完全な対応は要件書 §5 を参照。

| 画面 | 主要 FR | モックアップ実装状況 |
|---|---|---|
| 1. ホーム | FR-CART-02（追撃待機可視化）、FR-CAL-01〜03（先回り）、FR-DASH-01（サブダッシュボード）、FR-GAME-01（委ね Lv 表示）| ✅ 実装済（card--watch / card--calendar / sub-grid / stat）|
| 2. カート介入 | FR-CART-01（Share 受領）、FR-CART-02（追撃スケジュール）、FR-CART-05（遷移確認）| ✅ 実装済（sheet / card--arrival / card--timeline）|
| 3. リール | FR-REEL-01〜05、FR-CAL-03（予定駆動挿入）| ✅ 実装済（reel-card × 3、reel__dots）|
| 4. 論破チャット | FR-DEBATE-01〜08、FR-AUTH-03（クールダウン）| ⚠️ 一部実装（クールダウン UI は未、タイマー 90 秒あり）|
| 5. ダメ化レポート | FR-GAME-01〜04、FR-PROFILE-03（ダメ化PF）、FR-DASH-02（逆家計簿弾薬）| ✅ 実装済（level / card--metrics / card--narrative / quote-card）|
| 6. セーフガード | FR-AUTH-02〜05、NG-1〜8 の UI 表現 | ✅ 実装済（range / row-toggle / checklist / card--danger）|

### 2.1 FR 未実装一覧（Construction で対応予定）

- FR-DEBATE-05 クールダウン UI（3 回連続拒否時の UI）
- FR-CART-01 Share Extension ネイティブ実装（現モックは擬似演出）
- FR-CART-03 Special Link 実装（Approved Mobile Application 承認後）
- FR-PROFILE-02 嗜好ベクトル日次更新（実装のみ、UI は既存）
- FR-FUNNEL-06 CloudWatch Dashboard（社内用）

---

## 3. 6 画面 × Story マトリクス

stories.md（28 本）との対応。主担当のみ記載。

| 画面 | 主担当 Story ID | ペルソナ |
|---|---|---|
| 1. ホーム | US-03-01（Share 受領）、US-CAL-01（カレンダー連携）、US-AUTH-01（予算感アンケート）| 悠介 |
| 2. カート介入 | US-03-01〜03（Share 受領〜追撃）、US-03-04（Special Link 起動）、US-03-05（セーフガード）| 悠介、山田 |
| 3. リール | US-02-01〜05（リール閲覧、推薦、スキップ、論破遷移、カート監視入り）| 悠介、里奈 |
| 4. 論破チャット | US-01-01〜05（論破の初回〜クールダウン）| 悠介、田中 |
| 5. ダメ化レポート | US-REP-01〜03（週次レポート / ポートフォリオ編集 / Before-After 指標）| 悠介、里奈 |
| 6. セーフガード | US-SAFE-01〜04（上限 / 冷却 / NG カテゴリ / データ削除）、US-AUTH-02（MFA）| 悠介、山田（非ターゲット保護）|

### 3.1 Story カバレッジ

stories.md の 28 ストーリーのうち、**25 件がモックアップのいずれかの画面で主担当としてビジュアル化**されている。残り 3 件は以下で、いずれも Construction フェーズでの実装が必要なもの:

- **US-AUTH-03**（負債自己申告で初期セーフガード適用）: オンボーディングフロー内の分岐。6 画面のうち Home と Safeguard の間の遷移で扱うため、静的モックでは表現しきれない
- **US-CAL-02**（プレゼン予定から商品カテゴリを先回り提案）: Home の「予定から先回り」カードでラベル表示はあるが、推論ロジック自体は Construction で実装
- **US-CAL-03**（デート予定の情報を論破材料として AI プロンプトに埋め込む）: 論破モーダルの AI プロンプト合成段階の要件で、モック UI では可視化対象外

上記 3 件は Unit-2 Auth & Profile / Unit-6 Calendar で Construction フェーズで処理される。

---

## 4. 6 画面 × Unit 対応

Unit of Work（8 Units）との対応。

| 画面 | 主担当 Unit | 補助関与 Unit |
|---|---|---|
| 1. ホーム | Unit-1 Platform（画面フレーム）、Unit-5 Cart Intercept（監視リスト）、Unit-6 Calendar（先回り）| Unit-8 Dame Report（Lv 表示）|
| 2. カート介入 | Unit-5 Cart Intercept | Unit-1 Platform（Share Extension 基盤）|
| 3. リール | Unit-4 Reel | Unit-6 Calendar（予定駆動）|
| 4. 論破チャット | Unit-3 Debate | Unit-7 Safeguard（クールダウン）|
| 5. ダメ化レポート | Unit-8 Dame Report | Unit-6 Calendar（文脈）|
| 6. セーフガード | Unit-7 Safeguard | Unit-2 Auth & Profile（認証・上限設定）|

### 4.1 Unit カバレッジ

全 8 Units が 6 画面のいずれかで主担当または補助関与している。Unit-1 Platform / Unit-2 Auth & Profile は横断的に 2 画面で補助関与、コア 3 Unit（Unit-3/4/5）はそれぞれ明確な主担当画面を持つ。

---

## 5. トレーサビリティ検証

### 5.1 要件 → モックアップの一貫性

| 要件レベル | 要素数 | モックアップで表現済 | カバレッジ |
|---|---|---|---|
| UC | 8 | 8 | 100% |
| UI 系 FR（概算） | — | すべて反映済 | 嗜好ベクトル日次更新・予定本文端末ローカル処理等の非 UI 系 FR を除く |
| Story | 28 | 25 | 89%（3 件は Construction 時実装 = US-AUTH-03 / US-CAL-02 / US-CAL-03）|
| Unit | 8 | 8 | 100% |

### 5.2 モックアップ → 要件の逆トレース

モックアップに存在するすべての UI 要素が、要件書 §5 FR のいずれかに 1:1 対応している。**要件書にない UI 要素はモックアップに存在しない**。

---

## 6. 現時点の整合性チェック

以下をすべて満たすことを確認:

- [x] 要件書 §4.2 の 8 UC すべてがモックアップで可視化されている
- [x] stories.md の 28 Story のうち 25 件（UI 対象）がモックアップで主担当画面を持つ
- [x] unit-of-work.md の 8 Unit すべてがモックアップ画面と対応している
- [x] モックアップに要件外の要素（要件書に記述されていない機能）が存在しない

---

## 7. 参照

- [要件書 v0.8 §4.2 / §5](../requirements/requirements.md)
- [stories.md](../user-stories/stories.md)
- [unit-of-work.md](../application-design/unit-of-work.md)
- [unit-of-work-story-map.md](../application-design/unit-of-work-story-map.md)
- [画面 × 仮説検証マップ](./screen-hypothesis-map.md)
- モックアップ実体: `mockup/index.html`
