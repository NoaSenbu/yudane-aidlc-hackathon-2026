# Unit-1 Platform — Functional Design Plan

> Construction Phase / Per-Unit Loop / Unit-1 Platform の機能設計計画。
> 参照: [unit-of-work.md](../../inception/application-design/unit-of-work.md) / [components.md](../../inception/application-design/components.md) / [component-methods.md](../../inception/application-design/component-methods.md) / [services.md](../../inception/application-design/services.md) / [API 契約ガバナンス](../../../.kiro/steering/api-contracts.md)
> 作成: 2026-05-29 / ステージ: 🟢 CONSTRUCTION / Functional Design

---

## 0. Unit-1 の位置づけ（再確認）

Unit-1 Platform は **横断基盤 Unit**。対応 UC・主担当ストーリーはなく、他 7 Unit の開発・デプロイを可能にする「契約・規約・共通ライブラリ・モノレポ構造」を提供する。

そのため本 Functional Design は、通常の業務ロジック設計（ドメインエンティティ + 業務ルール）に加えて、**Unit-1 固有の「契約成果物の機能仕様」**（OpenAPI 凍結方針 / 型生成 / 共通ライブラリの振る舞い）を中心に据える。

### Unit-1 スコープ（components.md / unit-of-work.md より）

| 層 | コンポーネント | 機能設計で扱う対象 |
|---|---|---|
| Mobile | M-01 AppShell | ナビゲーション / Auth ゲート / ディープリンク受付の状態遷移 |
| Mobile | M-12 ApiClient | 認証ヘッダ付与 / 相関 ID / リトライ / エラーマッピング / ストリーミング |
| Mobile | M-13 Telemetry | クライアントイベントのバッファリング / バッチ送信 / バックオフ |
| Backend | B-12 AuditLogger | 構造化ログ / PII マスキング / 相関 ID 伝搬 / EMF メトリクス / X-Ray |
| Backend | B-14 TelemetryIngestionService | テレメトリ受信 → CloudWatch Metrics + S3 Data Lake 投入 |
| Shared | S-01 AsinExtractor | Amazon URL → ASIN 抽出 + バリデーション（TS / Python 両実装） |
| Shared | S-02 SchemaRegistry | OpenAPI 3.1 定義 + 型生成（TS / Python） |
| Shared | S-03 SafeguardPolicy | 月間上限 / 冷却 / 負債のルール定数 + 判定関数 |
| Shared | S-04 TelemetryContracts | メトリクス名 / イベント型 / PII マスキングルール |
| Infra | （CDK 基盤） | NFR / Infrastructure Design ステージで詳細化（本ステージでは責務境界のみ） |

> **注**: Infra（VPC / API Gateway / Cognito / DynamoDB / ElastiCache / OpenSearch / IAM / CDK）は技術非依存の Functional Design の対象外。後続の NFR Design / Infrastructure Design ステージで扱う。

---

## 1. 設計判断のための質問

以下の質問に `[Answer]:` タグで回答してください。各質問には推奨案・背景・選択肢を添えています。回答完了後「done」等でお知らせください。

### Question 1
S-02 SchemaRegistry が凍結する **OpenAPI 3.1 第1版の網羅範囲**をどうしますか？（Unit-1 が OpenAPI を凍結すると、Unit-2〜8 はその契約に従って並行開発する）

A) **全 UC のエンドポイント骨格を第1版で凍結**（auth / debate / reel / cart / calendar / safeguard / report の全パスを定義。詳細フィールドは後続 Unit の契約 PR で省略可能フィールド追加として拡張）— 並行開発の前提が最も強固、推奨
B) Unit-1/2 が直接使うエンドポイント（users / telemetry / auth 系）のみ第1版で凍結し、コア3 UC（debate/reel/cart）以降は各 Unit 着手時に契約 PR で追加
C) 共通コンポーネント（ProblemDetails / 認証 / ページネーション / 共通パラメータ）のみ第1版で凍結し、パスは全 Unit が随時追加
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 2
S-03 SafeguardPolicy の **判定関数 `decideAllow` の評価優先順位**をどう確定しますか？（component-methods.md では allow / block / warn の 3 値、入力は遷移回数・月間上限・予算消化・cooldownOn / quietWeek / hasDebt フラグ）

A) **block 優先 → warn → allow の段階評価**（① cooldownOn or quietWeek なら block、② hasDebt は上限比率を DEBT_MONTHLY_LIMIT_RATIO 0.35 に切替、③ 予算消化が上限超で block、④ 上限の 80% 超で warn、⑤ それ以外 allow）— セーフガード最優先（FR-FUNNEL-05）に整合、推奨
B) フラグ系（cooldown/quietWeek）のみ block、金額系は全て warn に留めてユーザーの最終判断に委ねる
C) 全条件を block 寄りに（warn を使わず allow/block の 2 値）して実装を単純化
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 3
S-01 AsinExtractor の **ASIN 抽出の対応 URL 範囲**をどこまでにしますか？（カート介入 UC-03 で Amazon 共有 URL から ASIN を取り出す中核ロジック）

A) **主要パターンを網羅**（`/dp/ASIN`、`/gp/product/ASIN`、`/gp/aw/d/ASIN`、短縮 `amzn.to`/`amzn.asia`、クエリ `?asin=`、Amazon 各国ドメイン .co.jp/.com 等）+ 10 桁英数字バリデーション — 実運用の取りこぼし最小、推奨
B) 日本 Amazon（amazon.co.jp）の `/dp/` と `/gp/product/` の標準形のみ。短縮 URL や他国ドメインは対象外
C) 正規表現で「10 桁の ASIN らしき文字列」を URL 全体から貪欲抽出（ドメイン・パス構造を問わない）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 4
B-12 AuditLogger の **PII マスキング対象と方式**をどう定義しますか？（SECURITY 全面適用、ログに PII を残さない方針）

A) **キー名ベースの自動マスキング**（`email` / `password` / `token` / `secret` / `apiKey` / `creditCard*` / `address` / `phone` 等の鍵名を検出して値を `***` 化 + メールは部分マスク `a***@example.com`）+ S-04 TelemetryContracts にマスクルールを集約 — 一貫性が高く設定漏れに強い、推奨
B) 各呼び出し側が明示的にマスク済みの値を渡す前提とし、AuditLogger は素通し（ライブラリは軽量化）
C) ログ出力前に正規表現でメール / 電話番号 / カード番号らしき値を本文から検出してマスク（鍵名に依存しない）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 5
M-12 ApiClient の **リトライ・エラーマッピング方針**をどうしますか？（相関 ID 付与・認証ヘッダ・ストリーミングは共通前提）

A) **冪等メソッド（GET）のみ指数バックオフ自動リトライ（最大2回、429/503/ネットワーク断）+ 401 は AuthModule.refresh を1回試行して再送 + 全エラーを ProblemDetails → ドメインエラー型にマッピング** — 推奨
B) リトライは一切せず、エラーをそのまま呼び出し側（TanStack Query 側の retry 設定）に委ねる
C) GET/POST 問わずリトライ（POST は冪等キー `Idempotency-Key` ヘッダ前提）
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 6
M-13 Telemetry / B-14 TelemetryIngestion の **イベント送信のバッファリング戦略**をどうしますか？

A) **クライアントでキューイングし、N件（例 20）到達 or T秒（例 30）経過 or アプリ background 化でバッチ flush。失敗時は AsyncStorage に退避して次回再送（最大保持件数で古いものから破棄）** — オフライン耐性あり、推奨
B) イベント発生ごとに即時送信（バッファなし、実装単純だがリクエスト数増）
C) 一定間隔（例 60 秒）の定期 flush のみ。即時性・background flush は持たない
X) Other（[Answer]: の後に記述）

[Answer]: 

### Question 7
Unit-1 が定義する **共通ドメインエラーモデル（DomainError）の分類体系**をどの粒度にしますか？（component-methods.md は `Result<T, DomainError>` または例外、API は RFC 7807 ProblemDetails）

A) **カテゴリ + コードの2階層**（カテゴリ: validation / auth / safeguard / external-api / rate-limit / not-found / conflict / internal。各カテゴリに具体コード例: safeguard.cooldown / safeguard.monthly-limit-exceeded 等）+ ProblemDetails の `type` URL にコードを対応付け — トレーサビリティが高い、推奨
B) HTTP ステータスコードと1対1の最小分類（400/401/403/404/409/422/429/500 に対応する 8 種のみ）
C) 自由文字列のエラーコード（厳密な体系は設けず、各 Unit が必要に応じて命名）
X) Other（[Answer]: の後に記述）

[Answer]: 

---

## 2. 実行ステップ（チェックボックス）

### Part 1: 計画 + 質問（現在地）
- [x] Unit-1 のコンテキスト分析（unit-of-work / components / methods / services / api-contracts 読込）
- [x] Functional Design Plan の作成（本ファイル）
- [x] ユーザーが Q1〜Q7 に回答（Q2/Q3/Q5/Q6/Q7=A 確定。Q1/Q4 は指摘ありで再検討）
- [x] 回答の分析・曖昧さ検出 → `unit-1-platform-functional-design-clarification.md` を作成（Q1/Q4）
- [ ] ユーザーが Clarification 1/2 に回答

### Part 2: 機能設計成果物の生成（承認後）
- [x] `aidlc-docs/construction/unit-1-platform/functional-design/domain-entities.md`
  - 横断ドメイン型（DomainError, CorrelationContext, TelemetryEvent, AsinResult, SafeguardDecision 等）のエンティティ定義と関係
- [x] `aidlc-docs/construction/unit-1-platform/functional-design/business-logic-model.md`
  - S-01 ASIN 抽出ロジック / S-03 SafeguardPolicy 判定フロー / M-12 ApiClient リトライ・エラーマッピング / M-13・B-14 テレメトリ・パイプライン / B-12 ログ・マスキングの各アルゴリズムを技術非依存で記述
- [x] `aidlc-docs/construction/unit-1-platform/functional-design/business-rules.md`
  - SafeguardPolicy 定数とルール / PII マスキングルール / ASIN バリデーション規則 / リトライ規則 / OpenAPI 契約ガバナンス規則を表形式で確定
- [x] `aidlc-docs/construction/unit-1-platform/functional-design/frontend-components.md`
  - M-01 AppShell のナビゲーション状態遷移・Auth ゲート・ディープリンクルーティング（Mobile を含むため作成）
- [x] 自己レビュー（整合性・要件充足・診断エラー）— 診断エラー 0、SG/PII/ERR の相互整合を確認
- [ ] 完了メッセージ提示 + 承認ゲート

---

## 3. Extension 適合の予定（Functional Design 段階での該当性）

| Extension ルール | 本ステージでの扱い |
|---|---|
| SECURITY-08（認可 / IDOR） | M-12 ApiClient の userId 検証方針、ApiClient が JWT sub とパスの整合を前提化する記述で言及 |
| SECURITY-09（エラー詳細秘匿） | DomainError → ProblemDetails マッピングで 500 系の詳細を body に含めないルールを business-rules に明記 |
| SECURITY-12（認証 / トークン管理） | M-12 の 401 リフレッシュ方針で言及 |
| PII 保護（NG-7 / FR-CAL-05） | B-12 マスキングルール / S-04 TelemetryContracts で明記 |
| PBT-02（round-trip） | S-01 AsinExtractor の抽出 ↔ 正規化、S-04 イベント serialize/deserialize の round-trip 性質を business-logic に記載（テスト詳細は NFR で確定） |
| PBT-07（domain generator） | DomainError / SafeguardDecision の生成器設計余地を domain-entities に注記 |
| その他 SECURITY/PBT の実装詳細 | NFR Requirements / NFR Design ステージで Unit 単位に確定（本ステージでは N/A） |
