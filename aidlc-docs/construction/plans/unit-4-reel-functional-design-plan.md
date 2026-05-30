# Unit-4 Reel — Functional Design Plan

> Construction Phase / Per-Unit Loop / Unit-4 Reel（🎬 エージェント型リール UC-02）の機能設計計画。
> 参照: [unit-of-work.md](../../inception/application-design/unit-of-work.md) / [components.md](../../inception/application-design/components.md) / [component-methods.md](../../inception/application-design/component-methods.md) / [services.md](../../inception/application-design/services.md) / [stories.md US-02-01〜05](../../inception/user-stories/stories.md) / [Unit-1 機能設計（前提基盤）](../unit-1-platform/functional-design/) / [API 契約ガバナンス](../../../.kiro/steering/api-contracts.md)
> 作成: 2026-05-30 / ステージ: 🟢 CONSTRUCTION / Functional Design / 担当: Member C

---

## 0. Unit-4 の位置づけ（再確認）

Unit-4 Reel は **コア 3 Unit の 1 つ**（UC-02 エージェント型リール）。縦型スワイプ UI から「嗜好 × 時刻 × カレンダー × 疲労度」の推薦を提示し、Amazon 遷移（M-2 ドーパミン回路強化）へ流す導線を担う。主担当ストーリーは **US-02-01〜05（5 本）**。

本 Functional Design は **技術非依存の業務ロジック設計**（ドメインエンティティ + 業務ルール + アルゴリズム）に集中する。インフラ（OpenSearch / ElastiCache / Lambda 配置 / IAM）と性能目標は後続の NFR Requirements / NFR Design / Infrastructure Design ステージで扱う。Unit-1 Platform が提供する横断基盤（DomainError 体系 / SafeguardPolicy S-03 / AsinExtractor S-01 / ApiClient M-12 / Telemetry / OpenAPI 契約）は **既に確定済みの前提** として利用する。

### Unit-4 スコープ（components.md / unit-of-work.md より）

| 層 | コンポーネント | 機能設計で扱う対象 |
|---|---|---|
| Mobile | M-03 ReelScreen | 縦型スワイプ UI の状態遷移 / 3 ジェスチャー（左=論破 / 右=カート監視 / ダブルタップ=Amazon 遷移）/ 遷移確認オーバーレイ / 無限スクロール |
| Backend | B-03 ReelRecommendationService | 嗜好 × 時刻 × カレンダー × 疲労度 × 使い切れ弾薬 の 5 軸推薦合成 / ベクトル検索による候補生成 / 深夜ブースト / 所有感ラベル生成 |
| Backend | B-10 AssociatesLinkGenerator | Amazon Associates Special Link URL 生成 + タグ付与 / dev・prd の出し分け / NG-8 遵守 |
| Backend | B-11 CreatorsApiClient | Creators API 呼出 + キャッシュ（TTL 6h）/ ダミーカタログ代替（Approved Mobile Application 承認前）|
| Backend | B-13 AmazonTransitionRecorder | 「🛍 Amazon で買う」タップ記録 / EXP 加算 / Safeguard 遷移カウント更新 / 冪等性 |
| Shared | （S-03 SafeguardPolicy 消費）| Unit-1 で確定済み。Reel は遷移前ゲートの consumer |

> **注**: ベクトル検索の物理実装（OpenSearch Serverless）/ Redis キャッシュの TTL 物理設定 / Lambda VPC 配置 / Bedrock モデル選定は技術非依存の Functional Design の対象外。後続ステージで扱う。本ステージでは「どんな入力から、どんなルールで、どんな出力を作るか」を確定する。

### 主担当ストーリーと対応 FR

| ストーリー | 概要 | 主要 FR |
|---|---|---|
| US-02-01 | 深夜 22 時にコンテキスト連動で高単価リールが立ち上がる | FR-REEL-03, FR-FUNNEL-02 |
| US-02-02 | ダブルタップで Amazon へワンタップ遷移（確認オーバーレイ + EXP +1）| FR-REEL-02, FR-REEL-05, FR-CART-04 |
| US-02-03 | 左スワイプで論破モードへ自動遷移 | FR-REEL-02, FR-DEBATE-01 |
| US-02-04 | 右スワイプで「後で見る」→ カート監視登録 | FR-REEL-02, FR-CART-01 |
| US-02-05 | 「確保しておきました」ラベルで所有感を醸成 | FR-REEL-03, FR-PROFILE-02 |

---

## 1. 設計判断のための質問

以下の質問に `[Answer]:` タグで回答してください。各質問には推奨案・背景・選択肢を添えています（推奨は **A**）。回答完了後「done」等でお知らせください。曖昧な回答が残る場合は follow-up clarification を作成します。

### Question 1
B-03 ReelRecommendationService の **推薦スコアリング方式**（5 軸: 嗜好ベクトル × 時刻 × カレンダー予定 × 疲労度/ストレス × 使い切れ弾薬）をどう構成しますか？

A) **2 段方式（候補生成 → 決定論的リランク）**: ① 嗜好ベクトルでベクトル近傍検索して候補 N 件（例 50）を取得 → ② 時刻ブースト / カレンダー一致 / ストレス係数 / 弾薬一致 / 直近表示の減衰 を **重み付き加算スコア**（純関数）で再ランク → 上位を返す。重みは設定値カタログで調整可能、スコアは再現可能（同一入力 → 同一順位）で PBT 可能 — 推奨（テスト容易・説明可能・LLM 非依存で安定）
B) LLM（Bedrock）に候補と全コンテキストを渡して **LLM 自身にランキングさせる**（プロンプトベース）。柔軟だが非決定論的でテスト困難・レイテンシ増
C) ベクトル近傍検索の **類似度スコアのみ**でランキング（時刻/ストレス等のブーストはカードのコピー生成にのみ使い、順位には反映しない）。実装最小だが「深夜高単価ブースト」(US-02-01) が順位に効かない
X) Other（[Answer]: の後に記述）

[Answer]: MVPの段階では過去に購入したものをもとに関連製品を推薦するようにしたいです。

### Question 2
**深夜ブースト（FR-REEL-03 / US-02-01）** の発火条件と挙動をどう確定しますか？

A) **時間帯 + ストレスの複合トリガー**: ① ローカル時刻が 22:00〜02:00 かつ ② 推定ストレスが `mid` 以上のとき発火 → 平均価格帯の **1.5〜3 倍** の高単価カードをフィード先頭に最大 K 件（例 3）挿入し「頑張ったあなたへ」系タグを付与。`quietWeek` または `cooldownOn` が true のときは **ブースト自体を抑止**（NG-6 整合・US-02-01 AC-4）— 推奨
B) 時刻のみで発火（ストレス条件なし）。深夜なら常に高単価を出す（疲労連動の意図 M-2 が薄れる）
C) ストレスのみで発火（時間帯条件なし）。終日いつでも高単価ブースト（深夜帯の脳内報酬系形成という設計意図 US-02-01 から外れる）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 3
推薦に使う **ストレスレベルの取得元**をどうしますか？（Unit-3 Debate の B-02 が `estimate_stress_level()` を持つが、Reel は論破前のフィード生成時点でストレスが必要）

A) **共有ストレス信号を Reel 側で読む**: ストレス推定の入力 `StressSignalsDto`（直近 7 日の会議密度・残業時刻分布・深夜帯利用回数・カレンダー連続予定数）と推定ロジックを **Unit-1/共通の純関数として切り出し**、Reel と Debate の双方が同じ関数で `low/mid/high` を算出する（判定一致・重複実装回避）— 推奨。本 Unit では「Reel はこの共有関数を呼ぶ」前提で設計し、関数の正本配置（shared か platform か）は backlog 化して Member A と確定
B) Reel が独自にストレス推定ロジックを持つ（Debate と別実装。判定がズレるリスク）
C) Reel はストレスを推定せず、クライアント（端末）が算出した `stress_level` をリクエストで受け取る（サーバーが信用できない値に依存、SECURITY 観点で弱い）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 4
**所有感ラベル（「確保しておきました」/「○○ さんのために見つけといた」、US-02-05）** の生成方式をどうしますか？

A) **サーバー側 LLM 生成 + テンプレートフォールバック + 24h 重複防止**: ① 嗜好・購入傾向・カレンダー多忙度を根拠に LLM が 1 文添えのラベルを動的生成（US-02-05 AC-1/2）② LLM 失敗時は決定論的テンプレート集からフォールバック ③ 同一ユーザーへの直近 24h で同一文言の連続表示を禁止しバリエーション担保（AC-3）④ カレンダー多忙度が高い場合「今週もよく戦ってるね」系へ切替（AC-4）— 推奨
B) テンプレートのみ（LLM 不使用）。実装最小だが「固有の根拠を 1 文添える」(AC-2) の個別感が弱い
C) LLM のみ（フォールバックなし）。LLM 障害時にラベルが空 or 遅延でフィードが崩れる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 5
M-03 ReelScreen の **ジェスチャー判定ルールと遷移ガード**をどう確定しますか？（stories.md: 左/右 60px・ダブルタップ 350ms）

A) **明示閾値 + 優先順位 + 確認オーバーレイ**: ① 左スワイプ ≥60px → 0.5s トースト後に論破モード（FR-DEBATE-01 trigger=long-view 相当）② 右スワイプ ≥60px → カート監視登録（楽観 UI + トースト）③ ダブルタップ（2 タップ間隔 ≤350ms）→ **必ず確認オーバーレイ**を挟んでから Amazon 遷移（FR-REEL-05、オーバーレイ削除不可）④ 同時成立時はダブルタップ > 水平スワイプ > 縦スクロールの優先順位 ⑤「論破不要」設定 ON 時は左スワイプで論破せずスキップトースト（US-02-03 AC-3）⑥ 同一カードへの左スワイプ 3 回超でクールダウン（US-02-03 AC-4 / FR-DEBATE-05）— 推奨
B) 閾値・優先順位は実装時に委ねる（本設計では「3 ジェスチャーがある」事実のみ記述）。設計の精度が落ちる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 6
B-13 AmazonTransitionRecorder の **遷移記録・EXP 加算・Safeguard 連携と冪等性**をどう確定しますか？

A) **冪等キー付き記録 + EXP +1 + Safeguard カウント更新を原子的に**: ① 遷移は `(userId, cardId, clientTransitionId)` を冪等キーに記録し、戻る→再タップ等の二重計上を防止（PBT-04）② EXP は 1 遷移につき +1（US-02-02 AC-4）③ 月間遷移カウント（SafeguardStates）を同一トランザクション/条件付き書き込みで更新 ④ 遷移リクエストは事前に Safeguard ゲートを通り、上限到達なら記録せず `safeguard.monthly-limit-exceeded`（409）を返す（reel.yaml と整合）⑤ EXP 加算結果は Unit-2 の B-08/B-13→嗜好ベクトルへ供給（UC-05 連動）— 推奨
B) 冪等性なし（毎タップ記録）。実装単純だが二重 EXP・二重カウントが起きる
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 7
B-11 CreatorsApiClient の **商品カタログ抽象化とダミー代替（FR-REEL-04 / §8 A-10）** をどう設計しますか？

A) **ポート/アダプタで抽象化 + キャッシュラッパ + 環境フラグ切替**: `ProductCatalogPort`（`get_item_by_asin` / `search_items`）を定義し、`CreatorsApiAdapter`（本番）と `DummyCatalogAdapter`（ハッカソン書類審査・予選、代表 1〜2 社の固定カタログ）を差し替え可能にする。キャッシュ（TTL 6h）は両アダプタ共通のデコレータ層。環境変数/設定で切替 — 推奨（承認前後の移行が非破壊・テストでダミー注入が容易）
B) Creators API を直接呼び、未承認時はダミー分岐を関数内に if で埋め込む（責務が混ざりテスト困難）
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 8
B-10 AssociatesLinkGenerator の **Special Link 生成ルールと安全策（FR-REEL-05 / §9 NG-8 / §8 A-10）** をどう確定しますか？

A) **タグ付き正規 URL を純関数生成 + 環境ガード + 短縮禁止**: ① ASIN + Associates タグ（+ commission 計測用の user 単位サブタグ）から Amazon 遷移 URL を生成（純関数、PBT round-trip 可）② Approved Mobile Application 承認前は **dev=仮リンク / prd=遷移ブロック**（US-03-04 AC-4）③ 遷移先が Amazon であることを不明瞭にする短縮は行わない（NG-8 / Associates Operating Agreement）④ 生成 URL は AsinExtractor で逆抽出して同一 ASIN に戻ることを検証可能にする — 推奨
B) URL 生成のみ（環境ガード・NG-8 制約は実装時考慮）。規約違反・本番事故のリスク
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 9
リールフィードの **ページング / 重複抑制モデル**（FR-REEL-01 無限スクロール）をどうしますか？

A) **カーソルベース + 既出抑制（seen-set）**: `GET /v1/reel?cursor=&limit=` のカーソルに「既出カード集合 + ランキング位置」を不透明エンコードし、同一セッションで同じ商品/ラベルの直近再表示を抑制（US-02-05 AC-3 と整合）。`limit` 既定 10。深夜ブースト挿入分はカーソル先頭で 1 回だけ消費 — 推奨
B) オフセットベース（page 番号）。実装単純だが候補が動的に変わると重複/抜けが出やすい
X) Other（[Answer]: の後に記述）

[Answer]: A

### Question 10
カレンダー予定コンテキスト（Unit-6 が `ctx.calendar_category` を供給、US-02-05 AC-4 / FR-CAL-03）への **依存の扱い**をどうしますか？

A) **任意入力 + 優雅な不在許容（スタブ駆動）**: Reel は `calendar_category` を **任意のコンテキスト入力**として受け取り、存在すれば「○○ のためのエージェント提案」タグとスコアブーストに反映、不在なら通常推薦にフォールバック。Unit-6 未完成中は Unit-1 の OpenAPI 契約に基づくスタブ/固定値で先行開発（Q6=A 凍結契約の恩恵）— 推奨
B) Unit-6 完成を待ってから Reel のカレンダー連動を実装（並行開発のメリットを失う）
X) Other（[Answer]: の後に記述）

[Answer]: A

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問（現在地）
- [x] Unit-4 のコンテキスト分析（unit-of-work / components / methods / services / stories US-02 / FR-REEL / Unit-1 前提 / reel.yaml 読込）
- [x] Functional Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q10 に回答（Q2〜Q10=A 確定。Q1=X「MVP は購入履歴ベースの関連商品推薦」で深掘り要）
- [x] 回答の分析・曖昧さ検出 → `unit-4-reel-functional-design-clarification.md` を作成（Q1 由来の CL-1/2/3）
- [x] ユーザーが Clarification 1〜3 に回答（CL-1/2/3=A 確定）

### Part 2: 機能設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/reel/functional-design/domain-entities.md`
  - ReelCard / ReelPage / RecommendationContext / OwnershipLabel / AmazonTransition / ExpAward / SpecialLink / ProductMeta / StressLevel 等のエンティティ定義と関係
- [x] `aidlc-docs/construction/reel/functional-design/business-logic-model.md`
  - ALG-RANK（5 軸スコアリング）/ ALG-BOOST（深夜ブースト）/ ALG-LABEL（所有感ラベル生成）/ ALG-TRANSITION（遷移記録 + EXP + Safeguard）/ ALG-CATALOG（カタログ取得 + キャッシュ + ダミー）/ ALG-LINK（Special Link 生成）の各アルゴリズムを技術非依存で記述
- [x] `aidlc-docs/construction/reel/functional-design/business-rules.md`
  - 推薦・ブースト・ラベル・遷移/EXP・Safeguard 連携・カタログ・リンク生成・ページング・カレンダー連動の各ルールと設定値カタログ（重み・閾値）を表形式で確定
- [x] `aidlc-docs/construction/reel/functional-design/frontend-components.md`
  - M-03 ReelScreen のコンポーネント階層 / props・state / ジェスチャー状態遷移 / 確認オーバーレイ / API 連携点（GET /reel, POST /amazon-transitions）
- [x] 自己レビュー（整合性・要件充足・診断エラー・US-02 受入条件カバレッジ）— diagnostics 0、US-02-01〜05 を ALG/ルールに紐付け、backlog B-203/B-204 追記
- [x] 完了メッセージ提示 + 承認ゲート（次ステージ = NFR Requirements）— 2026-05-30 承認

---

## 3. Extension 適合の予定（Functional Design 段階での該当性）

| Extension ルール | 本ステージでの扱い |
|---|---|
| SECURITY-05（入力検証）| `GET /reel` のクエリ（cursor/limit）と `POST /amazon-transitions` の body を契約スキーマで検証する方針を business-rules に明記 |
| SECURITY-08（認可 / IDOR）| 遷移記録・フィード取得が JWT `sub` とユーザー一致を前提とする旨を明記（Unit-1 REQ-04/05 を踏襲）|
| SECURITY-09（エラー詳細秘匿）| カタログ外部 API 失敗（external-api.*）の詳細を body に出さず Unit-1 DomainError 体系へマッピング |
| SECURITY-11（セキュアデザイン）| Safeguard 判定は遷移前ゲートで S-03 を必ず通す（FR-FUNNEL-05）旨を明記 |
| NG-6 / NG-8 遵守 | 深夜ブースト・所有感ラベルの脅迫/罪悪感強要回避（NG-6）、Special Link の遷移先不明瞭化禁止（NG-8）をルール化 |
| PBT-02（round-trip）| Special Link 生成 ↔ ASIN 逆抽出、ReelCard serialize/deserialize、カーソルエンコード/デコードの round-trip 性質を business-logic に注記（テスト詳細は NFR で確定）|
| PBT-03（invariant）| ランキングスコアの決定性（同一入力→同一順位）、遷移カウントが Safeguard 上限を超えない不変条件を注記 |
| PBT-04（idempotency）| 遷移記録の冪等性（同一 clientTransitionId で EXP/カウント二重計上なし）を注記 |
| その他 SECURITY/PBT の実装詳細 | NFR Requirements / NFR Design ステージで Unit-4 向けに確定（本ステージでは N/A）|
