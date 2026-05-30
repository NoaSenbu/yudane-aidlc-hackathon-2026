# Backlog（後回し・見送り・将来検討の集約）

> AI-DLC ワークフロー外のチーム運用ドキュメント。`aidlc-docs/` は AI-DLC 公式成果物専用、本ファイルを含む `doc/` 配下はチーム運用情報専用。
>
> 並列開発前提の決定（[parallel-dev-prerequisites.md](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md)）/ Per-Unit 設計 / Inception 時に「後回し」「見送り」「将来検討」と判断した項目を集約する。
>
> **記載ルール（必須 4 項目）**: 各エントリは以下を必ず含む:
>
> 1. **項目名**: 何を議論したか
> 2. **出典**: どの議論・ドキュメント・ステージで判断したか（相対リンク）
> 3. **後付け導入トリガー**: どんな条件・指標が満たされたら再評価するか
> 4. **優先度**: 高 / 中 / 低（再評価の緊急度）
>
> 詳細ルールは [.kiro/steering/structure.md](../.kiro/steering/structure.md) §6 Backlog 運用ルール を参照。

---

## 1. Construction Phase 並列開発前提（2026-05-27 確定）

### B-001. ログ・監視スタック（観測性基盤）

| 項目 | 内容 |
|---|---|
| **項目名** | AWS Lambda Powertools / X-Ray / EMF / CloudWatch Dashboard の全面導入 |
| **出典** | [parallel-dev-prerequisites.md §I-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) 回答 = C（一旦見送り） |
| **当初推奨案** | Powertools 構造化ログ + X-Ray 全 Lambda トレース + EMF カスタムメトリクス + Dashboard IaC 化 |
| **見送り理由** | 予選 5/30 まで実装範囲を最小化、構築コストを Unit-1〜5 のコア機能に集中させるため |
| **暫定運用** | CloudWatch Logs raw のみ（Lambda 標準出力）。構造化なし、トレースなし、カスタムメトリクスなし |
| **後付け導入トリガー** | 以下のいずれか 1 つで導入検討開始<br>1. 予選デモで Lambda 障害が発生し、原因特定が raw ログで困難だった場合<br>2. 北極星指標（論破 → Amazon 遷移率）の可視化が決勝までに必要となった場合<br>3. 決勝 6/26 に向けて AWS デプロイ時の SLA / SLO 提示が必要となった場合 |
| **優先度** | **中**（予選では不要、決勝の AWS 上動作デモで価値が出る可能性あり） |
| **概算工数** | Powertools 導入 = 0.5d / X-Ray 有効化 = 0.5d / EMF + Dashboard = 1d、合計 2d（Member A） |

---

### B-002. Bedrock Sonnet 4.6 の後付けエスカレーション機能

| 項目 | 内容 |
|---|---|
| **項目名** | Bedrock Claude Sonnet 4.6（Global CRIS 経由）を高品質モデルとして導入 |
| **出典** | [parallel-dev-prerequisites.md §C-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) 回答 = B（Haiku 4.5 全面採用 + 留保） |
| **当初推奨案** | Haiku 4.5（apne1 native）= ストリーミング論破 + Sonnet 4.6（Global CRIS）= 日次バッチでプロンプト最適化 |
| **見送り理由** | 4 名 / 3 日（予選まで）の制約下で、エスカレーション UI / 課金モニタリング / Cross-Region Inference の運用までは作り込めない。Haiku 4.5 単独で要件書 §6.3 の合意率目標を満たせるベンチマーク見込みあり |
| **暫定運用** | 全論破 / 推薦 / プロンプト合成を Haiku 4.5 で実装。SSM Parameter Store には Haiku 4.5 + Embeddings V2 のみ先行登録、Sonnet 4.6 用 Parameter は未作成 |
| **後付け導入トリガー** | 以下のいずれか 1 つで Sonnet 4.6 検討開始<br>1. PBT-08 論破合意率 < 70% が連続 1 週間継続<br>2. MVP デモ視聴者の体感評価で「論破が浅い」フィードバックが過半<br>3. Haiku 4.5 のストリーミングが要件書 §6.3 のレイテンシ要件（初回トークン 3 秒以内）に届かない場合（この場合は Nova Lite 等の軽量モデル fallback も検討） |
| **優先度** | **中**（Haiku 4.5 で要件未達が顕在化した時点で即時検討） |
| **概算工数** | Sonnet 4.6 SSM Parameter 追加 + DebateLlmService の model_id 切替実装 + Cross-Region Inference 設定 = 1.5d（Member A or Member B） |

---

## 2. Per-Unit 内の見送り / 後付け検討（2026-05-27 確定）

### B-201. Telemetry 投入経路の C 案（SQS 介在型）への移行

| 項目 | 内容 |
|---|---|
| **項目名** | B-14 TelemetryIngestionService の Firehose 投入を SQS Consumer Lambda 経由に変更（C 案） |
| **出典** | [Unit-1 Platform Functional Design Plan §Q3](../aidlc-docs/construction/unit-1-platform/functional-design/functional-design-plan.md) 回答 = B + 安全装置 3 点 |
| **当初推奨案（B）** | Mobile 5 件バッファ + B-14 Lambda 内で Firehose 同期呼び出し |
| **見送り理由** | ハッカソン規模（10〜10K DAU）で性能限界は 100K DAU 以降にしか出ない。C 案は実装工数 +1d / 運用複雑度増のため、安全装置 3 点（Idempotency Key + Lambda DLQ + 移行トリガー記録）でリスクを緩和して B で開始 |
| **暫定運用** | B-14 Lambda が Firehose を同期呼び出し。失敗時は Lambda DLQ に自動退避、Idempotency Key で重複防止 |
| **後付け導入トリガー** | 以下のいずれか 1 つで C 移行検討開始<br>1. 平均 events/sec > **100**（〜50K DAU 相当）が連続 1 週間継続<br>2. Telemetry 欠損率 > **0.1%** が観測された<br>3. Firehose 一時障害が 1 回でも顕在化した<br>4. 決勝後にプロダクト化判断が下された |
| **優先度** | **中**（性能 / 欠損問題が顕在化した時点で即時検討） |
| **概算工数** | B-14 Lambda の Firehose → SQS 切替（5-10 行）+ SQS Consumer Lambda 新設（30-50 行）+ DLQ 設定 + CDK スタック追加 = **0.5〜1d**（Member A）。Mobile 側変更ゼロ、API 契約変更ゼロ、ダウンタイムほぼゼロ |

---

### B-202. B-02 DebateLlmService の Provisioned Concurrency 追加

| 項目 | 内容 |
|---|---|
| **項目名** | B-02 DebateLlmService に Provisioned Concurrency 1 並列を追加して論破ストリーミングのコールドスタートを完全にゼロ化 |
| **出典** | [Unit-1 Platform Functional Design Plan §Q5](../aidlc-docs/construction/unit-1-platform/functional-design/functional-design-plan.md) 回答 = B + B-02 DDB 化 + SnapStart |
| **当初推奨案（採用済み）** | A 採用（B-02 DDB 化）+ SnapStart 有効化（追加料金ゼロ、cold start 〜300-400ms に短縮） |
| **見送り理由** | 月額 $11-15 のコスト発生 / SnapStart 単独でも要件「初回トークン 3 秒以内」を 13% 程度の余裕で達成 / SnapStart + DDB 化 + VPC 外で ENI 新規作成リスクも回避済み |
| **暫定運用** | SnapStart 単独（追加料金ゼロ）で B-02 を運用。ENI 新規作成リスクは VPC 外配置で完全回避 |
| **後付け導入トリガー** | 以下のいずれかで Provisioned Concurrency 追加検討<br>1. 決勝デモ（2026-06-26）の前 1 週間（6/15 以降）の総合判断で「並列 2 以上の同時アクセスでデモ事故が起きうる」と判断された場合<br>2. PBT-08 / E2E テストで cold start が 500ms を超えるケースが連続観測された場合<br>3. MVP デモ視聴者の体感評価で「論破の最初の応答が遅い」フィードバックが過半 |
| **優先度** | **低**（SnapStart で要件達成済み、決勝向けの保険） |
| **概算工数** | CDK 5 行追加 = **5 分**（Member A）。`addAutoScaling` で `minCapacity: 1, maxCapacity: 10` 設定、cost monitor を CloudWatch Dashboard に追加（要 I-2 の B-001 backlog の解消が前提）|
| **想定追加コスト** | 月額 $11-15（apne1 / Python 3.13 / 1024MB / 1 並列）|

---

### B-203. ストレス推定共有関数の正本配置（shared / platform）

| 項目 | 内容 |
|---|---|
| **項目名** | Reel（B-03）と Debate（B-02）が共有する `estimate_stress_level()` の正本配置と切り出し先の確定 |
| **出典** | [Unit-4 Reel Functional Design Plan §Q3](../aidlc-docs/construction/plans/unit-4-reel-functional-design-plan.md) 回答 = A（共有純関数化） |
| **当初推奨案** | ストレス推定ロジックを Unit-1/共通の純関数として切り出し、Reel と Debate が同一関数で `low/mid/high` を算出（判定一致・重複実装回避） |
| **見送り理由（保留理由）** | 正本を `shared/`（TS/Python 両実装）に置くか `backend` 共通（Python のみ）に置くかは、Reel が論破前のフィード生成でサーバー算出する前提（Q3=A / REEL-STRESS-04）と Debate の利用箇所を突き合わせて Member A と確定する必要がある。Unit-4 の Functional Design 時点では「同一関数を呼ぶ」前提のみ固定し、物理配置は保留 |
| **暫定運用** | Unit-4 は `StressLevel` を共有関数から得る前提で設計（domain-entities §2.1 / REEL-STRESS-01〜05）。実装着手時は backend 内の共通モジュールに仮置きし、Debate 着手と同期して正本化 |
| **後付け導入トリガー** | 以下のいずれかで確定<br>1. Unit-3 Debate の Functional Design / Code Generation で `estimate_stress_level()` の入出力が確定したとき<br>2. Reel と Debate のストレス判定差異が観測されたとき<br>3. Mobile 側でもストレス表示が必要になり TS 実装が要るとき（shared 化が必須化） |
| **優先度** | **中**（Unit-3 と Unit-4 の実装合流前に確定が必要） |
| **概算工数** | 共通関数の切り出し + 配置 + 両 Unit からの参照差し替え = 0.5〜1d（Member A + Member B/C 調整） |

---

### B-204. Reel 推薦のベクトル検索（Titan Embeddings + OpenSearch）導入
| 項目 | 内容 |
|---|---|
| **項目名** | B-03 ReelRecommendationService の候補生成を購入履歴ヒューリスティックから Titan Embeddings V2 + OpenSearch Serverless のベクトル近傍検索へ拡張 |
| **出典** | [Unit-4 Reel Functional Design Clarification CL-1](../aidlc-docs/construction/plans/unit-4-reel-functional-design-clarification.md) 回答 = A（MVP は購入履歴ベース、ベクトル検索は決勝で導入） |
| **当初推奨案** | components.md の B-03 当初設計どおり、嗜好ベクトルを埋め込みクエリにして OpenSearch で近傍商品を候補化 |
| **見送り理由** | 予選 5/30 までの実装・インフラ負荷を抑えるため、MVP は購入履歴のカテゴリ/ブランド一致 + 共購買ヒューリスティック（CL-1=A）で候補生成。OpenSearch Serverless 依存と埋め込みパイプラインを予選から外して軽量化・テスト容易化 |
| **暫定運用** | MVP は ALG-RANK の候補生成段をカテゴリ/ブランド一致 + 共購買で実装（REEL-RANK-01）。リランク（決定論的スコアリング）は MVP から適用（CL-2=A）。OpenSearch は使わない |
| **後付け導入トリガー** | 以下のいずれかで導入検討<br>1. 決勝 6/26 に向けて推薦精度の差別化が必要と判断されたとき<br>2. MVP デモで「推薦が浅い/関連性が弱い」フィードバックが過半<br>3. 購入履歴が十分蓄積し、ヒューリスティックの上限が見えたとき |
| **優先度** | **中**（決勝の完成度・ビジネス価値で効く可能性） |
| **概算工数** | Titan Embeddings 埋め込みパイプライン + OpenSearch Serverless インデックス + B-03 候補生成差し替え = 2〜3d（Member C + Member A インフラ支援） |

---

### B-205. Reel ラベル/コピーの非同期後追い生成（プレースホルダ → 差し替え）

| 項目 | 内容 |
|---|---|
| **項目名** | リールカードの所有感ラベル/推薦コメント（ALG-PITCH/LABEL）を同期生成からプレースホルダ即返し → 非同期後追い差し替えに変更 |
| **出典** | [Unit-4 Reel NFR Design Plan §Q3 / 矛盾解消3](../aidlc-docs/construction/plans/unit-4-reel-nfr-design-plan.md)（後追いは FD ドメインモデルと未整合のため MVP では不採用） |
| **当初推奨案（採用済み = 同期）** | MVP は同期生成に統一。ソフト期限 350ms 内にテンプレートフォールバックで必ず非空ラベルを返す（FD: `ReelCard.ownershipLabel`/`pitch` は必須・同期） |
| **見送り理由** | 後追い差し替えには `ownershipLabel`/`pitch` の nullable 化 + 差し替えチャネル（再取得 or SSE）+ クライアント UI の差し替え対応が必要で、FD ドメインモデル・`GET /v1/reel` レスポンス契約の変更を伴う。MVP のレイテンシ予算は同期 + フォールバックで達成可能なため、複雑化を避けて見送り |
| **暫定運用** | 同期生成 + 350ms ソフト期限 + テンプレートフォールバック（R-PAT-LLM-01）。LLM ハードタイムアウト 1.5s |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. 決勝でフィード初回描画 p95 が目標（500ms）を LLM ラベルが律速して超過<br>2. LLM ラベルの品質を上げるため生成時間を延ばしたい（後追いなら初回描画を阻害しない）<br>3. 事前生成キャッシュ（人気商品）でも吸収しきれない場合 |
| **優先度** | **低**（同期 + フォールバックで MVP・決勝の予算を達成見込み） |
| **概算工数** | ドメインモデル nullable 化 + 差し替えチャネル（SSE or ポーリング）+ Mobile UI 差し替え = 1.5〜2d（Member C） |

---

### B-501. B-06 NotificationDispatcher の通知コピー LLM 動的生成

| 項目 | 内容 |
|---|---|
| **項目名** | 追撃通知（30m / 6h / 24h）のコピーを Bedrock Claude Haiku 4.5 で動的生成し、商品メタ + ユーザー嗜好 + ステップ情報からパーソナライズする |
| **出典** | [Unit-5 Cart Intercept Functional Design Plan §Q3](../aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design-plan.md) 回答 = A（MVP テンプレート → 決勝 LLM） |
| **当初推奨案（採用済み）** | A（MVP）：30m / 6h / 24h の各ステップに 5〜10 パターンの「友達系トーン」テンプレートを用意し、商品名・価格・ユーザー名を埋め込む |
| **見送り理由** | 予選 5/30 までの工数制約で LLM 通知コピー生成 + NG-6（脅迫禁止）モデレーションパイプラインは +2d。テンプレート 10 パターンで予選デモのバリエーションは確保可能 |
| **暫定運用** | `backend/src/cart/notification_templates.py` に 30 パターン（10 × 3 ステップ）を静的定義。商品名・価格・残時間をプレースホルダで差し込む |
| **後付け導入トリガー** | 以下のいずれかで導入検討<br>1. 決勝 6/26 に向けて M-2（ストレス × ご褒美軸の個別最適化）強化が必要となった場合<br>2. MVP デモ後のフィードバックで「通知が定型的」「もっとパーソナル感が欲しい」が過半<br>3. ストーリー US-03-02 AC-2 の「軽い論破 / 記憶想起 / 最終通告のトーン使い分け」がテンプレートでは不十分と判定された場合 |
| **優先度** | **中**（決勝向けの差別化要素、M-2 の核心） |
| **概算工数** | Bedrock Haiku 4.5 呼出 + プロンプトテンプレート + NG-6 出力モデレーション + Hypothesis PBT = **2d**（Member D / Member B 後半） |
| **想定追加コスト** | Haiku 4.5 入力 1K tokens × 通知 1 件 ≒ $0.0001、月 1 万通知で $1 程度 |

---

### B-502. クリップボード検知（US-03-03）の MVP 実装

| 項目 | 内容 |
|---|---|
| **項目名** | フォアグラウンド復帰時にクリップボードを読み取り Amazon URL があればサジェストする機能（US-03-03） |
| **出典** | [Unit-5 Cart Intercept Functional Design Plan §Q6](../aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design-plan.md) 回答 = B（MVP 見送り、決勝で実装） |
| **当初推奨案（採用済み）** | B：MVP では Share Extension（US-03-01）が UC-03 の主導線として十分機能するため見送り、決勝で UIPasteControl（iOS）対応含めて実装 |
| **見送り理由** | (1) US-03-01 Share Extension が UC-03 の核心動作であり予選デモで十分なインパクト、(2) iOS 16+ の paste 許可ダイアログが毎回出る UX 問題、(3) UIPasteControl（ボタン型）の Expo / RN 対応状況が不明確で要調査、(4) 工数 -1d で他のストーリーに集中 |
| **暫定運用** | クリップボード検知機能は実装しない。Share Extension のみで UC-03 を完結。US-03-03 は「決勝で実装予定」として stories.md にもマーキングは不要（既に「サブ機能」位置づけ） |
| **後付け導入トリガー** | 以下のいずれかで実装<br>1. 決勝 6/26 に向けて UC-03 の進化アピールが必要となった場合<br>2. UIPasteControl の Expo SDK 52+ 公式対応が確認できた場合<br>3. ユーザーテストで「Share Extension の操作が面倒」フィードバックが過半<br>4. 里奈ペルソナ（B）の「Share Extension すら面倒」体験を実装で示したい場合 |
| **優先度** | **低**（決勝向けの差別化要素、Share Extension で代替可能） |
| **概算工数** | iOS UIPasteControl 対応調査 + Native Module 拡張 + Android 通常 Clipboard API + サジェスト UI + 24h 拒否記録 = **1.5〜2d**（Member D） |

---

### B-503. ダミーカタログ（`backend/src/cart/_dummy_catalog.py`）の削除

| 項目 | 内容 |
|---|---|
| **項目名** | Amazon Approved Mobile Application 申請承認後のダミーカタログ削除と Creators API 本接続への完全移行 |
| **出典** | [Unit-5 Cart Intercept Functional Design §3.4 ダミーカタログ仕様](../aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md) / 要件書 §8 A-10 |
| **当初推奨案（採用済み）** | Approved 承認前は `backend/src/cart/_dummy_catalog.py` で 10 商品の固定データを返却、`USE_DUMMY_CATALOG` 環境変数で B-11 CreatorsApiClient と切替 |
| **見送り理由** | Amazon Approved Mobile Application 申請が決勝（2026-06-26）前に必須だが、申請承認には数週間〜1 ヶ月を要する見込み。書類審査・予選（5/30）期間中はダミーで代替する |
| **暫定運用** | dev 環境 / prd 環境とも 6/15 までは `USE_DUMMY_CATALOG=true`、Creators API 本接続は 6/15 以降に有効化判定 |
| **後付け導入トリガー** | 以下のいずれかで削除実施<br>1. Amazon Approved Mobile Application 承認通知（要件書 §8 A-10 申請完了後）<br>2. Creators API の本番接続テストが green（IT-08 の dummy 版 → 実 API 版で同等動作）<br>3. 決勝後のプロダクト化判断 |
| **優先度** | **中**（Amazon Approved 承認次第、決勝デモはダミーで実行可能） |
| **概算工数** | `_dummy_catalog.py` 削除 + B-11 CreatorsApiClient の本実装テスト + USE_DUMMY_CATALOG 環境変数フラグ削除 + ダミー商品 4 件の S3 SVG ホスティング解除 = **0.5d**（Member D） |
| **削除と同時に実施する確認事項** | (1) すべての E2E テスト（E2E-03 / E2E-03b）が実 Creators API 経由で pass、(2) Cache hit 率が 95% 以上で安定、(3) Creators API レート制限超過アラームが新規セットされている |

---

### B-504. APNs Production Certificate 取得（Apple Developer Program 登録）

| 項目 | 内容 |
|---|---|
| **項目名** | prd 環境の Push 通知配信用 APNs Production Certificate 取得 + Apple Developer Program 登録（$99/年） |
| **出典** | [Unit-5 Cart Intercept Infrastructure Design Plan §3 Q5 v3 改訂](../aidlc-docs/construction/plans/unit-5-cart-intercept-infrastructure-design-plan.md) / [requirements.md §6.1 リージョン](../aidlc-docs/inception/requirements/requirements.md) |
| **当初推奨案（採用済み）** | dev = APNs Sandbox cert（Apple Developer 不要）+ prd = APNs Production cert（Apple Developer Program 必須）、SSM パス `/yudane/{env}/cart/eum-application-id` で別 Application 管理 |
| **見送り理由** | Apple Developer Program は年間契約 $99 USD で経費承認必須、書類審査（2026-05-10）/ 予選（2026-05-30）期間中は dev cert のみで Sandbox 配信を実機検証する。prd cert は決勝デモ（2026-06-26）の直前に整備 |
| **暫定運用** | 予選 MVP は dev 環境 + Sandbox cert + 個人開発者の Apple ID で実機検証、prd デモは Apple Developer Program 登録完了後に APNs Production cert を取得し End User Messaging に登録 |
| **後付け導入トリガー** | 以下のすべてが揃った時点で実施<br>1. Member A が経費承認（$99 × 1 年）<br>2. Member D が Apple Developer Program 登録 → Keys タブで `.p8` Authentication Key 生成<br>3. End User Messaging Push の APNs Channel に Production Cert を登録（CDK で `CfnAPNSChannel` 設定）<br>4. 決勝デモ 2 週間前（2026-06-12）までに完了 |
| **優先度** | **高**（決勝デモのコア体験 = Push 通知配信に必須、登録遅延でブロッカー化リスク） |
| **概算工数** | Apple Developer Program 登録（オンライン申請、Apple 審査 24-48h）+ `.p8` Key 生成 + CDK `CfnAPNSChannel` 統合 + APNs Production への送信動作確認 = **0.5d**（Member D） |
| **ブロッカー判定** | 2026-06-12 までに登録未完了の場合は Member A が緊急エスカレーション（[AGENTS.md §11.5](../.kiro/steering/AGENTS.md)）、決勝デモシナリオから Push 通知パートを縮退（dev cert で Sandbox 配信のみ表示する代替プラン） |

---

### B-506. PlatformStack の cdk-nag 7 件 error 抑制または修正

| 項目 | 内容 |
|---|---|
| **項目名** | Unit-1 PlatformStack の cdk-nag が 7 件の未抑制 error を出力し、`infra/test/platform-stack.test.ts` の "cdk-nag の未抑制エラーがない" テストが fail |
| **出典** | [Unit-5 Code Generation Build and Test 検証 2026-05-30](../aidlc-docs/audit.md) — `npm test --workspace infra` 実行時に検出 |
| **検出した 7 件 error** | (1) Redis: AwsSolutions-AEC4 Multi-AZ なし<br>(2) Redis: AwsSolutions-AEC5 デフォルトポート使用<br>(3) Redis: AwsSolutions-AEC6 Redis AUTH なし<br>(4) PlatformVpc: AwsSolutions-VPC7 VPC Flow Log なし<br>(5) UserPool: AwsSolutions-COG1 パスワードポリシー不十分<br>(6) UserPool: AwsSolutions-COG8 プラスティアでない<br>(7) DataLakeBucket: AwsSolutions-S1 S3 サーバーアクセスログなし |
| **当初推奨案** | 各 error について以下のいずれかで対応する: (a) 設定変更で解消（VPC Flow Log 追加、S3 Access Logs 追加、UserPool パスワードポリシー強化）/ (b) NagSuppressions で正当な理由付きで抑制（dev 環境で Multi-AZ 不要 / Redis AUTH は IAM 認証で代替 等） |
| **見送り理由（Unit-5 視点）** | Unit-5 Cart Intercept のレビュー範囲外。Unit-1 PlatformStack の責務であり Member A 側で対応する。Unit-5 の `cart-stack.ts` は cdk-nag 抑制を完備しており、`infra/test/cart-stack.test.ts` 11/11 pass している |
| **暫定運用** | `infra/test/platform-stack.test.ts` の "cdk-nag の未抑制エラーがない" テストは現在 fail。`bin/app.ts` 経由で PlatformStack を依存に含むスタック（CartStack 等）の `cdk synth` 時にも synth は通るが、cdk-nag warning が混在する状態 |
| **後付け導入トリガー** | 以下のいずれかで対応開始<br>1. Member A の Unit-1 Platform Stack 完成 PR `#platform-additions-001` に組み込み（最有力）<br>2. dev 環境への CDK deploy 前に必須化（cdk-nag は deploy 時に検査されるため）<br>3. 決勝向け prd 環境構築時（要件書 §7 SECURITY-15 cdk-nag green 必須） |
| **優先度** | **高**（Unit-1 完成 PR に組み込む必要があり、Member A の Stage 3 完了条件） |
| **概算工数** | 設定変更（VPC Flow Log + S3 Access Logs + UserPool パスワードポリシー強化）= 1d / NagSuppressions 7 件 + 理由コメント = 0.5d、合計 1〜1.5d（Member A） |

---

### B-507. PlatformStack の TypeScript exactOptionalPropertyTypes 違反修正

| 項目 | 内容 |
|---|---|
| **項目名** | Unit-1 PlatformStack の TypeScript コンパイルエラー 3 件（`cdk synth` 実行時の ts-node コンパイルで失敗） |
| **出典** | [Unit-5 Code Generation Build and Test 検証 2026-05-30](../aidlc-docs/audit.md) — `npx cdk synth cart-dev-stack` 実行時に検出 |
| **検出したエラー** | (1) `lib/platform-stack.ts:69` TS2375: `Vpc` を `IVpc` に渡せない（`vpnGatewayId: string \| undefined` が `string` に assignable でない、`exactOptionalPropertyTypes: true` 起因）<br>(2) `lib/platform-stack.ts:106` TS2375: 上と同じ Vpc → IVpc 違反<br>(3) `lib/platform-stack.ts:89` TS6133: `dataLake` 変数が未使用 |
| **影響** | `tsconfig.base.json` で `exactOptionalPropertyTypes: true` が設定されているため、AWS CDK 内部型（`IVpc.vpnGatewayId?: string`）と衝突。**`vitest run test/platform-stack.test.ts` は通るが、`cdk synth` の ts-node モードでは fail**。これは vitest が Vite の transformer 経由でコンパイルする一方、`cdk synth` は ts-node で厳密にコンパイルするため判定が異なる |
| **当初推奨案** | (a) `vpnGatewayId: undefined` を spread 条件分岐で省略（`...(opts.vpnGatewayId !== undefined ? { vpnGatewayId: opts.vpnGatewayId } : {})`）/ (b) `infra/tsconfig.json` で `exactOptionalPropertyTypes: false` に override（CDK との相性悪い設定の見直し）/ (c) `dataLake` を `_dataLake` にリネーム（未使用 → ignored 扱い） |
| **見送り理由（Unit-5 視点）** | Unit-5 Cart Intercept のレビュー範囲外。`bin/app.ts` 経由で PlatformStack を import する関係で `cdk synth cart-dev-stack` 時にも露出するが、CartStack 自体のコードは `exactOptionalPropertyTypes: true` 環境で全 TS エラーを修正済み（`developerInitial` の spread 条件分岐 + `lambdaCommonProps: satisfies Pick<...>` パターン） |
| **暫定運用** | Unit-5 単独テスト（`vitest run test/cart-stack.test.ts`）は 11/11 pass。`cdk synth cart-dev-stack` は PlatformStack の TS エラーで blocked、Member A の修正待ち |
| **後付け導入トリガー** | Member A の Unit-1 Platform Stack 完成 PR `#platform-additions-001` に組み込み（B-506 と同じタイミング） |
| **優先度** | **高**（B-506 と合わせて Member A の Stage 3 完了条件） |
| **概算工数** | 推奨案 (a) + (c) で 0.5d（Member A） |

---

### B-505. Lambda packaging 統一方針（asset path / Layer / vendored shared）

| 項目 | 内容 |
|---|---|
| **項目名** | Backend Lambda の packaging 統一（`backend.src.*` 絶対 import + `shared/*/python/` の vendoring 戦略） |
| **出典** | [Unit-5 Code Generation 2 巡目セルフレビュー Issue W7 / W2-2](../aidlc-docs/construction/unit-5-cart-intercept/code/unit-5-code-summary.md) |
| **当初推奨案** | (1) `lambda.Code.fromAsset` の対象を **リポジトリルート** にし、handler を `backend.src.cart.handlers.cart_intake.lambda_handler` 形式で指定 + `shared/*/python/` を Lambda Layer として packaging（または bundling 時に `vendor/` へコピー）<br>(2) Member A が Unit-1 の Telemetry Lambda で同じ問題を抱えているため、**Unit-1 packaging 方針**を先行確立し、Unit-5 / Unit-3 / Unit-4 等が追従する |
| **見送り理由** | Code Generation 当初は handler パスを `handlers.xxx.handler` の単純形で書き、`backend.src.cart.repository` import が runtime で解決できない packaging 問題が顕在化。Unit-1 telemetry/handler.py も同パターンで未動作のため、**Unit-5 単独で先行解決すると Unit-1 の方針と齟齬が生じ書き直し**になる。Unit-1 で方針確立後に Unit-5 を追従修正するのが整合的 |
| **暫定運用** | (1) cart-stack.ts と各 Lambda handler 冒頭に `TODO(unit-1-packaging-001): Member A の Unit-1 packaging 方針確立後に修正` コメントを残置<br>(2) ローカルテスト（pytest）は `backend/conftest.py` の sys.path = リポジトリルート で動作するため import 健全性は担保済み<br>(3) `shared/asin-extractor/python/asin_extractor.py` の `try/except ImportError` フォールバックは **dev 環境ローカル動作のため**のセーフネット、本番 Lambda 環境では packaging 修正後に削除予定 |
| **後付け導入トリガー** | 以下のいずれかで実装開始<br>1. Member A が Unit-1 Telemetry Lambda の dev 環境デプロイで packaging エラーに直面した時点（**最有力、2026-05-29〜5/30 想定**）<br>2. Unit-1 / Unit-5 のいずれかで `cdk deploy` 後の Lambda 起動テストで `ImportError` が顕在化した時点<br>3. CI に `cdk synth` + `lambda invoke` の dry-run job を追加した時点 |
| **優先度** | **高**（Unit-1 / Unit-3 / Unit-4 / Unit-5 すべての Backend Lambda が動作するための必須条件、決勝デプロイ前にブロッカー化） |
| **概算工数** | (1) Unit-1 packaging 方針決定（asset = リポジトリルート + handler = 完全修飾形 + Layer 戦略）= **0.5d**（Member A）<br>(2) Unit-5 の cart-stack.ts asset path + handler 文字列書換 + asin_extractor.py の `try/except ImportError` 削除 = **0.3d**（Member D） |
| **検討すべき選択肢** | A: asset = リポジトリルート + handler 完全修飾（最小工数、bundle サイズ大）<br>B: Lambda Layer に `shared/*/python/` を分離（bundle 効率最適、CDK 構成複雑化）<br>C: bundling 時に `shared/*/python/` を asset 配下にコピー（中庸、Layer なし） |

---

## 3. Nice to have（決定不要、将来検討）

> [parallel-dev-prerequisites.md §3](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) で「決定不要、参考」と判断した項目のうち、再評価の余地があるものを記録。
> N-1（Figma 化）はスキップ判断を撤回し、議論再開のため本 backlog からは除外（同 §3 で active 議論中）。

### B-101. 多言語化（i18n）対応

| 項目 | 内容 |
|---|---|
| **項目名** | アプリ全体を日本語以外の言語に対応させる |
| **出典** | [parallel-dev-prerequisites.md §3 N-2](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | YUDANE のターゲットペルソナ（悠介・里奈）は日本のリモートワーカー。ハッカソン提出範囲は日本語のみで十分 |
| **暫定運用** | 全 UI コピー・通知・論破プロンプトは日本語ハードコード。`react-native-localize` 等の i18n 基盤は導入しない |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. ハッカソン後にプロダクト化を検討する場合<br>2. 海外向け展開を意思決定した場合<br>3. 審査員から多言語対応の質問が出た場合（プレゼン Q&A の事前準備として） |
| **優先度** | **低**（ハッカソン期間中は不要） |
| **概算工数** | i18n 基盤導入 + 日本語以外 1 言語 = 3d（チーム全体） |

---

### B-102. Storybook によるコンポーネントカタログ

| 項目 | 内容 |
|---|---|
| **項目名** | Storybook（または Storybook for React Native）で UI コンポーネントを単体プレビュー可能にする |
| **出典** | [parallel-dev-prerequisites.md §3 N-3](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | UI コンポーネントは `mobile/src/features/<unit>/` 配下に直接配置する方針。Storybook の構築・運用コストは 4 名 / 1 ヶ月では割に合わない |
| **暫定運用** | コンポーネントのプレビューは Expo Dev Client 上の screen で確認、Figma（B-103 の検討結果に依存）と並列でビジュアル管理 |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. UI コンポーネントが 30 個以上に肥大化した場合<br>2. デザイナーがチームに加入した場合<br>3. ハッカソン後の継続開発で複数アプリ間でデザインシステム共有が必要となった場合 |
| **優先度** | **低**（決勝までは不要） |
| **概算工数** | Storybook 導入 + 主要コンポーネント 10 個カタログ化 = 2d（Member A） |

---

### B-103. ダークモード切替（ライトモード追加）

| 項目 | 内容 |
|---|---|
| **項目名** | ライトモード対応の追加（OS 設定連動の自動切替を含む） |
| **出典** | [parallel-dev-prerequisites.md §3 N-5](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) |
| **見送り理由** | YUDANE のモックアップが既にダーク基調（Indigo×cold rose×cyan）で、深夜帯利用と背徳感の演出に直結。ライトモードはコンセプトと相反する |
| **暫定運用** | ダークモード固定。`tailwind.config.js` のトークンも単一テーマで管理 |
| **後付け導入トリガー** | 以下のいずれかで検討<br>1. ハッカソン後にプロダクト化する場合（A11y / WCAG 観点で必要になる可能性）<br>2. ユーザーテストでダーク基調が拒否された場合 |
| **優先度** | **低**（ハッカソン期間中は採用しない設計判断そのもの） |
| **概算工数** | ライトモードトークン整備 + 全画面確認 = 3d（Member A） |

---

## 4. ドキュメント編集ルール

- 新たに「後回し」「見送り」「将来検討」と判断した項目は、判断と同じ作業ターンで本ファイルに追記する
- エントリ ID は領域ごとに分離（B-001 系 = Construction 並列開発前提 / B-101 系 = Nice to have / B-201 系 = Per-Unit 内の見送り）
- 後付け導入が決定された項目は、本ファイルから削除せず「**ステータス: 採用済み（YYYY-MM-DD）**」を末尾に追記して履歴を残す
- 採用判断ロジックの変更を `aidlc-docs/audit.md` に必ず追記する

---

## 5. 関連リンク

- [.kiro/steering/structure.md](../.kiro/steering/structure.md) §6 Backlog 運用ルール
- [aidlc-docs/construction/plans/parallel-dev-prerequisites.md](../aidlc-docs/construction/plans/parallel-dev-prerequisites.md) — 並列開発前提の決定
- [aidlc-docs/aidlc-state.md](../aidlc-docs/aidlc-state.md) — AI-DLC 各ステージの進捗
- [aidlc-docs/audit.md](../aidlc-docs/audit.md) — 対話履歴と判断証跡


## 3. Unit-3 Debate v3.2 通常運用版全採用（2026-05-29 確定）

### B-303. AgentCore Memory custom Strategy 採用検討 → MVP 採用済

| 項目 | 内容 |
|---|---|
| **項目名** | AgentCore Memory の custom Strategy（M-1 / M-2 メカニズム特化のカスタム抽出プロンプト）の採用検討 |
| **出典** | [Unit-3 Functional Design Plan v3 Q16](../aidlc-docs/construction/unit-3-debate/functional-design/functional-design-plan.md) で v3 当時は backlog 化推奨、v3.2 で MVP 採用に格上げ |
| **当初推奨案（v3）** | MVP は組み込み 2 種（userPreference + semantic）のみ、custom Strategy は決勝前再評価 |
| **後付け導入トリガー（v3 当時）** | (1) 決勝前に組み込み Strategy で論破成功率が伸び悩んだ場合 / (2) ハッカソン創造性軸「ダメ化メカニズム特化 AI」アピール材料の必要性 |
| **優先度（v3 当時）** | 中 |
| **概算工数（v3 当時）** | 0.5d（カスタム抽出プロンプト設計 + Strategy CDK 設定） |
| **ステータス: 採用済み（2026-05-29）** | v3.2 オプション C（通常運用版全採用）採用に伴い、MVP 段階で `m1_m2_axis_extractor` という custom Strategy を新設して採用。Q1 = C / Q10 = B / Q16 = B と整合。実装は task-breakdown.md Phase 4 で実施（P1 タスク）。本エントリは履歴として保持（structure.md §6.1 ルール準拠、削除しない） |

---

### B-304. AgentCore Online Evaluation 導入

| 項目 | 内容 |
|---|---|
| **項目名** | AgentCore Online Evaluation を Unit-3 Debate に導入し、論破成功率 / プロンプト品質 / 個別最適化精度を継続計測 |
| **出典** | [Unit-3 Functional Design Plan v3.2 §6.4](../aidlc-docs/construction/unit-3-debate/functional-design/functional-design-plan.md#64-backlog-追加項目v32-で確定) Q16 v3 推奨案、v3.2 で「決勝後の運用評価」に降格 |
| **当初推奨案** | AgentCore Online Evaluation で論破ターン履歴を継続的に評価、抽出精度 / 翻意成功率 / NG-6 違反率を CloudWatch Dashboard に表示 |
| **見送り理由** | 決勝 6/26 までの実装に Phase 1〜6 のメインタスクで手一杯。Online Evaluation の評価プロンプト設計と CloudWatch 連携は決勝後の余裕がある時期に適切 |
| **暫定運用** | Phase 4 で custom Strategy 抽出結果を 100 セッション分定性評価（手動）で代替。CloudWatch Logs Insights で論破成功率を SQL 集計（簡易版） |
| **後付け導入トリガー** | 以下のいずれかで導入検討<br>1. 決勝後の運用フェーズ（プロダクト化判断）<br>2. 論破成功率の改善余地を継続計測する必要が出た<br>3. AgentCore Online Evaluation の正式 GA + 価格確定 |
| **優先度** | **中**（決勝後のプロダクト化向け） |
| **概算工数** | 評価プロンプト設計 + CloudWatch 連携 = 1.5d（Member B） |

---

### B-305. Sonnet 4.6 切替（プロンプト合成側）

| 項目 | 内容 |
|---|---|
| **項目名** | Unit-3 Debate のプロンプト合成 / 論破ストリーミングを Haiku 4.5 → Sonnet 4.6 切替 |
| **出典** | [Unit-3 Functional Design Plan v3.2 Q4](../aidlc-docs/construction/unit-3-debate/functional-design/functional-design-plan.md) Q4 = A + SSM model_id 切替（v3.2 で SSM 切替の仕組みのみ MVP 採用） |
| **当初推奨案** | parallel-dev-prerequisites C-2 = B Haiku 4.5 単独確定。Sonnet 4.6 は backlog B-002 で記録済み |
| **見送り理由** | B-002 と同じ理由（4 名 / 3 日制約 + Haiku 4.5 で要件達成）。v3.2 では SSM 切替の仕組み（`/yudane/<env>/debate/model-id`）だけ MVP に組み込み、切替はトリガー条件で実施 |
| **暫定運用** | SSM Parameter `/yudane/<env>/debate/model-id` の既定値 `anthropic.claude-haiku-4-5` で運用。Sonnet 4.6 への切替は SSM 値変更 + Lambda 再起動で対応可能（Stack 再デプロイ不要） |
| **後付け導入トリガー** | 以下のいずれかで切替検討<br>1. 決勝後にユーザー数 1000 超 + Haiku 4.5 のレート制限 / 品質制約検出<br>2. PBT-08 論破合意率 < 70% が連続 1 週間継続（B-002 と同じ）<br>3. ユーザー体感評価で「論破が浅い」が過半（B-002 と同じ） |
| **優先度** | **中**（B-002 と同じ。SSM 切替の仕組みは MVP 採用済なので工数低い） |
| **概算工数** | SSM 値変更（1 コマンド）+ Lambda 再起動 + 動作確認 = 0.5d（Member A or B） |

---

### B-306. Memory custom Strategy のプロンプト改善版

| 項目 | 内容 |
|---|---|
| **項目名** | Q1 / Q10 / Q16 で MVP 採用した custom Strategy（`m1_m2_axis_extractor`）のプロンプト改善 |
| **出典** | [Unit-3 Functional Design Plan v3.2 Q16](../aidlc-docs/construction/unit-3-debate/functional-design/functional-design-plan.md) v3.2 で MVP 採用 |
| **当初推奨案** | Phase 4 で custom Strategy 第 1 版を実装。決勝後に 100 セッション以上の論破ログから抽出精度を計測し、プロンプト改善版（v2）に置換 |
| **見送り理由** | MVP では「組み込み 2 種 + custom 1 種」で創造性軸をアピール、抽出精度の継続改善は決勝後の運用フェーズに適切 |
| **暫定運用** | Phase 4 の第 1 版プロンプトで運用、定性評価のみ実施 |
| **後付け導入トリガー** | 以下のいずれかで改善版作成<br>1. 決勝後の論破成功率分析で「翻意した軸」の抽出精度が組み込み Strategy より低い<br>2. Online Evaluation（B-304）の指標で改善余地が明確 |
| **優先度** | **中**（決勝後の継続改善項目） |
| **概算工数** | プロンプト v2 設計 + A/B テスト + デプロイ = 1.0d（Member B） |

---

### B-307. RuntimeEndpoint Auto-Pause 設定

| 項目 | 内容 |
|---|---|
| **項目名** | dev / staging RuntimeEndpoint の Auto-Pause 設定（コスト最適化） |
| **出典** | [Unit-3 Functional Design Plan v3.2 Q17](../aidlc-docs/construction/unit-3-debate/functional-design/functional-design-plan.md) Q17 = B（dev/staging/prd 3 endpoint） |
| **当初推奨案** | dev / staging endpoint は Auto-Pause（一定時間アクセスがなければ自動停止）でコスト抑制 |
| **見送り理由** | RuntimeEndpoint の追加料金は要確認、デモ期間中は Auto-Pause 不要、決勝後の運用最適化フェーズで適切 |
| **暫定運用** | dev / staging endpoint も常時稼働。実コスト発生 |
| **後付け導入トリガー** | 以下のいずれかで導入<br>1. dev/staging endpoint の月額が $X 超え（要確認）<br>2. 決勝後の運用最適化フェーズ |
| **優先度** | **低**（決勝後のコスト最適化） |
| **概算工数** | CDK 5 行追加 = 0.3d（Member B） |

---

## 4. UI SSOT 切替に伴う旧アセット整理（2026-05-30 確定）

### B-301. Direction D 移行に伴う旧 `mockup/index.html` (v0.4) のアセット整理

| 項目 | 内容 |
|---|---|
| **項目名** | Construction Phase 着手後、Direction D（黒服のコンシェルジュ）が UI SSOT に確定したため、旧 `mockup/index.html` v0.4（Indigo × cold rose × cyan、6 画面）の最終的なアーカイブ位置・命名・README 整合の確認 |
| **出典** | [.kiro/steering/tech.md §2 デザインツール行](../.kiro/steering/tech.md)（2026-05-30 SSOT 切替）/ [aidlc-docs/construction/design-system/direction-d-design-system.md](../aidlc-docs/construction/design-system/direction-d-design-system.md) §1（旧 v0.4 を Inception 期参考資料として残置）/ [mockup/README.md](./README.md)（v0.4 を「Inception 期の参考資料」と明記済） |
| **当初推奨案** | 旧 v0.4 を `mockup/` 配下にそのまま残置（書類審査の Inception 成果物として `git log` 含めて履歴を保つ）。tech.md / mockup/README.md / Direction D 設計システムの 3 ファイルで「v0.4 = Inception 期参考、Construction 以降は Direction D」と相互リンクで明示 |
| **暫定運用** | 上記 3 ファイル + 本 backlog エントリで「v0.4 は Construction 実装の参照対象ではない」と読み手に伝える文言を確保。`mockup/` ディレクトリそのものの移動・名称変更（`mockup-v0.4-inception/` 等）は **未実施**（書類審査リンクが切れるリスクを避ける）|
| **後付け導入トリガー** | 以下のいずれか 1 つで再評価<br>1. 決勝（2026-06-26）後にプロダクト化判断が下され、リポジトリ整理が必要になった場合<br>2. ハッカソン後に新規メンバーが参加し、`mockup/` を本実装と誤認するインシデントが起きた場合<br>3. README / Inception ドキュメント側のリンクが Direction D へ完全移行され、旧 v0.4 への流入導線が ≤ 0 となった場合 |
| **優先度** | **低**（v0.4 は審査時の歴史的資料、放置でも実害は出ない見込み） |
| **概算工数** | ディレクトリ rename + リンク追従修正 = 0.5d（Member A）。書類審査リンク切れの恐れがあるためアーカイブ判断は慎重に |


---

## 5. Unit-1 Platform / Unit-3 Debate Phase 1 着手時に検出した既存技術債務（2026-05-30 確定）

### B-302. `infra/test/platform-stack.test.ts > cdk-nag の未抑制エラーがない` の fail 解消

| 項目 | 内容 |
|---|---|
| **項目名** | Unit-1 platform-stack のテスト 1 件（cdk-nag 未抑制エラーがない）が fail している問題の解消 |
| **出典** | [Unit-3 Phase 1 Step 1 完了サマリ §6 既知の問題](../aidlc-docs/construction/unit-3-debate/code/debate-stack-summary.md) / 検出は 2026-05-30、stash 検証で Step 1 着手前から既に fail していたことを確認 |
| **当初推奨案** | 7 件の cdk-nag エラー（`AwsSolutions-*`）を個別に分類し、(a) 直接修正可能なもの（cdk-nag ルール準拠で再実装）、(b) 正当な Suppression を理由コメント付きで追加するもの、(c) ルール抑制を runtime-role 等の単位で適用、の 3 段で対処 |
| **見送り理由** | Unit-3 Phase 1 Step 1 の作業範囲外。Unit-1 担当（Member A）の責務領域、または cdk-nag バージョンアップに伴う既存 Stack の再点検作業。Unit-3 の進行を止めない判断 |
| **暫定運用** | Unit-3 debate-stack のテストは独立した cdk-nag suppression 設定で green を維持。CI（`.github/workflows/ci.yml`）で `vitest run` 全体を実行している場合は本問題で red となる可能性があり、必要に応じ CI で `--exclude '**/platform-stack.test.ts'` 等の暫定回避を入れる |
| **後付け導入トリガー** | 以下のいずれか 1 つで再評価<br>1. CI が無視できない Red のまま 1 週間以上継続した場合<br>2. Member A が Unit-1 後続改善（Unit-2 完了時点の追加 cdk-nag ルール対応）に着手するタイミング<br>3. 決勝 6/26 前の cdk-nag 全クリア要件達成時に対処必須化 |
| **優先度** | **中**（Unit-3 進行はブロックしないが、決勝前の cdk-nag 全クリアには必須対応） |
| **概算工数** | 7 件のエラー内訳調査 = 0.5d / 個別対処 = 1〜1.5d、合計 1.5〜2d（Member A） |

---

### B-303. `infra/lib/auth-stack.ts` 等で `pointInTimeRecovery` deprecation Warning の解消

| 項目 | 内容 |
|---|---|
| **項目名** | aws-cdk-lib v2.170+ 系で `aws_dynamodb.TableOptions#pointInTimeRecovery is deprecated` の警告を `pointInTimeRecoverySpecification` への移行で解消 |
| **出典** | [Unit-3 Phase 1 Step 1 完了サマリ §6 既知の問題](../aidlc-docs/construction/unit-3-debate/code/debate-stack-summary.md) / vitest 実行時に platform-stack / auth-stack / debate-stack（auth + 暫定の Cooldowns）で同警告を確認 |
| **当初推奨案** | 全スタックの `dynamodb.Table` 定義を `pointInTimeRecovery: true` から `pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true }` に置換 |
| **見送り理由** | Warning であり Snapshot fixture や cdk-nag green に影響しない。Unit-3 Phase 1 着手の優先度が高い |
| **暫定運用** | 既存通り `pointInTimeRecovery: true` を全スタックで使用（debate-stack でも踏襲） |
| **後付け導入トリガー** | 以下のいずれか 1 つで対処<br>1. aws-cdk-lib メジャーバージョンアップで `pointInTimeRecovery` が削除された場合<br>2. 警告を抑制したいタイミング（CI ログのノイズ削減目的）<br>3. 決勝前の依存ライブラリ最新化作業のタイミング |
| **優先度** | **低**（警告のみで動作に影響なし） |
| **概算工数** | 全 Stack の置換 + Snapshot 再生成 + 各 PR レビュー = 0.5d（Member A、または各 Unit 担当の小作業） |


---

### B-308. AgentCore Memory `streamDeliveryResources` の Memory ↔ S3 直結

| 項目 | 内容 |
|---|---|
| **項目名** | AgentCore Memory の `streamDeliveryResources` を S3 Memory Export Bucket に紐付け、Memory イベント / 抽出済み軸データを S3 へストリーミング配信する経路の構築 |
| **出典** | [Unit-3 Phase 3+4+6 統合 Plan §1 Step 3-3 / §6 リスク表](../aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md) / 検出は 2026-05-30、aws-cdk-lib v2 系の L1 `CfnMemory.StreamDeliveryResourcesProperty` が **Kinesis Data Streams 経由のみ**サポートで S3 直結を未対応であることを実装着手時に確認 |
| **当初推奨案** | Memory `streamDeliveryResources` に `kinesis: { dataStreamArn, contentConfigurations }` を設定し、Kinesis Firehose で S3 MemoryExportBucket へ delivery（CFN 仕様準拠の正攻法経路）|
| **見送り理由** | Phase 3-3 で「Memory が直接 S3 を参照する」設計を Plan に書いていたが、CFN 仕様上不可能であることが判明。Kinesis Firehose 連鎖実装は Phase 3 工数を 2d 以上膨張させ、決勝までの優先度（PBT 全面 / 統合テスト IT-DEBATE-01〜03 / デモシナリオ）を圧迫するため見送り。S3 Memory Export Bucket / Glue Crawler / IAM Role / SSM 7 個目は **Phase 3-3 で先行整備**し、Memory ↔ S3 のデータ流入経路だけ後付けする方針 |
| **暫定運用** | 1) Phase 3-3 で S3 MemoryExportBucket（KMS + Lifecycle 30/90/365 日 + versioned）+ Glue Crawler を CDK Snapshot で整備し SSM 7 個目（`memory-export-bucket-arn`）を出力<br>2) Year 1 退化レポート（FR-REPORT-04）の「ダメ化ポートフォリオ」可視化が必要になるまでは Memory `Get*` API 経由でのデータ抽出を採用<br>3) Memory → S3 連結のためのデータ移送は Strands Agent 内で `s3:PutObject` を呼ぶ簡易バッチで代替（Phase 4 検討） |
| **後付け導入トリガー** | 以下のいずれか 1 つで Kinesis Firehose 連鎖実装を再評価<br>1. 決勝デモで「ダメ化ポートフォリオ」を Athena view 経由で見せる要件が確定した場合<br>2. Memory イベント量が `Get*` API レスポンス上限（1MB or list 上限）を超え、bulk 抽出が必要になった場合<br>3. AWS CDK L2 の `agentcore.Memory` が将来 `streamDeliveryResources` をサポートし、L1 直書きの workaround が不要になった場合 |
| **優先度** | **中**（決勝 Year 1 退化レポートのデータソースとして必要、5 月時点での L1 直書き工数は重い） |
| **概算工数** | Kinesis Data Stream + Firehose + Memory `streamDeliveryResources` L1 直書き + cdk-nag suppression + Snapshot 再生成 + 接続テスト = 2d（Member B + Member A の確認）|

---

### B-309. Unit-3 Debate React Native コンポーネント本体（Direction D 実装）

| 項目 | 内容 |
|---|---|
| **項目名** | `<DebateScreen>` / `<DSeal>` / `<AffirmScreen>` / Direction D 黒服コンシェルジュトーンの React Native コンポーネント本体実装 |
| **出典** | [Unit-3 Phase 2 Plan §0](../aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md) / [Unit-3 Functional Design frontend-design.md](../aidlc-docs/construction/unit-3-debate/functional-design/frontend-design.md) / 検出は 2026-05-30、Phase 2 範囲外として明示 |
| **当初推奨案** | Direction D HTML（`YUDANE Concierge (Direction D) (offline).html`）の 3 画面を React Native + NativeWind v4 + Reanimated でコンポーネント化し、Phase 2 で完成済みの `direction-d-labels` / `debate-view-model` / `affirm-view-model` / `debate-store` / `event-parser` / `agentcore-client` を結線して論破 → 翻意 → 受付の動作確認まで完了 |
| **見送り理由** | Mobile Outside-In TDD の純ロジック層（reducer / view-model / Zustand slice）と Backend Strands Agent + ローカル開発モードの結線確認を Phase 2 の優先範囲とした。React Native コンポーネント本体は実機ビルド + EAS Build + iOS/Android シミュレータ検証が必要で、Phase 2 期間（4 日）には収まらない |
| **暫定運用** | Phase 2 までの実装で「ロジック面の動作確認」は L1（純関数 unit）/ L2（`agentcore dev` + 実 Bedrock）レベルで可能。決勝デモは Direction D HTML プロトタイプ（offline）+ Backend ストリーミングの組み合わせで成立する |
| **後付け導入トリガー** | 以下のいずれか 1 つで着手<br>1. Phase 1 Step 8 完了（dev デプロイ + EAS Build 環境整備）<br>2. 予選 5/30 デモで Direction D HTML プロトタイプの限界（実機操作感の差）が顕在化した場合<br>3. 決勝 6/26 前の実機 E2E（E2E-01〜03）が必要となった場合 |
| **優先度** | **高**（決勝までに少なくとも `<DebateScreen>` `<AffirmScreen>` の 2 画面は実機で操作可能にする必要あり） |
| **概算工数** | 3 画面 × Direction D トーン適用 = 2.5d（Member B、Phase 2 完成済の純ロジックを差し込むだけなのでロジック開発は不要）|

