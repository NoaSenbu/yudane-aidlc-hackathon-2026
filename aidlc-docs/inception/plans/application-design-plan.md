# Application Design Plan (AI-DLC Inception / Application Design)

## 参照ドキュメント

* 要件書: [`requirements.md`](../requirements/requirements.md) [v0.4](../requirements/requirements.md)

* ユーザーストーリー: [`stories.md`](../user-stories/stories.md)（15 本 × 3 コア UC）

* ペルソナ: [`personas.md`](../user-stories/personas.md)（悠介 / 里奈 + 非ターゲット）

* 退化年表: [`persona-journey.md`](../user-stories/persona-journey.md)

* 実行計画: [`execution-plan.md`](./execution-plan.md)（Workflow Planning 承認済み）

## 設計スコープ

* **Mobile 層**: React Native + TypeScript + **AWS SDK v3** + **TanStack Query + Zustand**（Amplify は Auth のみ薄く採用、Data/Functions/CLI は不採用）

* **Backend 層**: **CDK 管理 Lambda（Python 3.13）** + API Gateway (REST)

* **Shared 層**: スキーマ定義、プロトコル、共通ユーティリティ

本ステージでは **高レベルのコンポーネント識別・サービス層設計** に集中する。ビジネスロジックの詳細（例: 論破プロンプトの具体構造）は Construction フェーズの Functional Design（per-unit）で扱う。

## アーキテクチャ前提（確定済み、要件書 v0.6 準拠）

* **モバイル**: React Native 0.76+ (New Architecture) + TypeScript 5.x + AWS SDK v3。状態管理は TanStack Query（サーバー）+ Zustand（クライアント）。Amplify は Auth のみ薄く採用、Data/Functions/CLI は不採用

* **Auth**: Amazon Cognito + TOTP MFA（モバイルから Amplify JavaScript v6 の Auth モジュールで利用、`amazon-cognito-identity-js` は非推奨のため不採用、CDK で User Pool 管理）

* **Data**: REST API（API Gateway + Lambda）+ **生 DynamoDB**（AppSync / GraphQL 不採用）

* **AI / 論破**: Amazon Bedrock（Claude Haiku 4.5 / Sonnet 4.6）+ Titan Embeddings V2 + OpenSearch Serverless

* **Push**: AWS End User Messaging Push + EventBridge Scheduler

* **Amazon 連携**: Creators API（商品メタ）+ Associates Program（Special Link）

* **Extension**: Security Baseline 全面 + Property-Based Testing 全面

## 主要コンポーネント暫定案（設計対象の全体像）

### Mobile 層（RN + TypeScript + AWS SDK v3）

| コンポーネント                         | 責務                                                   |
| ------------------------------- | ---------------------------------------------------- |
| `App Shell`                     | ナビゲーション / Auth ゲート / タブバー                            |
| `Home Screen`                   | AI エージェント稼働 hero / カート監視リスト / カレンダー連動カード / サブダッシュボード |
| `Reel Screen`                   | 縦型リール UI / スワイプ / Amazon 遷移確認オーバーレイ（UC-02）           |
| `Debate Screen`                 | 論破チャット UI / タイピング演出 / 90 秒タイマー（UC-01）                |
| `Cart Intercept Screen`         | Share 到着アニメ / 追撃タイムライン可視化（UC-03）                     |
| `Dame Report Screen`            | 委ね Lv / Before-After 指標 / 行動変容ナラティブ                  |
| `Safeguard Screen`              | 月間上限 / 冷却モード / NG カテゴリ（UC-08）                        |
| `Share Extension Native Module` | iOS Share Extension / Android Share Target（ネイティブ）    |
| `Push Notification Handler`     | APNs / FCM 受信・タップ処理                                  |
| `Calendar Native Module`        | iOS EventKit / Google Calendar 連携（端末ローカルでカテゴリ分類）     |
| `Biometric Bridge`              | 参考: Amazon 側の Face ID に委ねる設計で、YUDANE 内部の生体認証は基本不要    |

### Backend 層（CDK 管理 Lambda）

| コンポーネント                       | 責務                                                                                                  | 実装位置                           |
| ----------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------ |
| `Data Models (DynamoDB Tables)`         | User / Preference / CartWatchItem / AmazonTransition / DebateSession / EventCategory 等のテーブル定義 | CDK                  |
| `Debate LLM Service`          | 論破プロンプト合成 + Bedrock ストリーミング呼び出し                                                                     | CDK 管理 Lambda (Python)         |
| `Reel Recommendation Service` | 嗜好ベクトル × 時刻 × カレンダー × 疲労度から商品推薦                                                                     | CDK 管理 Lambda (Python)         |
| `Cart Intake Handler`         | Share 受信 → ASIN 抽出 → Creators API → DynamoDB 登録                                                     | CDK 管理 Lambda (Python)       |
| `Cart Attack Scheduler`       | EventBridge Scheduler で 30m / 6h / 24h の追撃ジョブ作成                                                     | CDK                         |
| `Notification Dispatcher`     | AWS End User Messaging Push で APNs/FCM 送信                                                           | CDK 管理 Lambda (Python)                  |
| `Calendar Prediction Service` | 予定カテゴリ → 商品カテゴリ推定（LLM）                                                                              | CDK 管理 Lambda (Python)         |
| `Preference Vector Updater`   | 日次バッチで嗜好ベクトル更新                                                                                      | CDK 管理 Lambda (Python)         |
| `Safeguard Rules Engine`      | 月間上限 / 冷却モード / 負債検知の判定                                                                              | CDK 管理 Lambda (Python)          |
| `Associates Link Generator`   | Special Link URL 生成（タグ付け）                                                                           | CDK 管理 Lambda (Python)     |
| `Creators API Client`         | 商品メタ取得 + ElastiCache キャッシュ                                                                          | CDK 管理 Lambda (Python)         |

### Shared 層

| コンポーネント                              | 責務                                               |
| ------------------------------------ | ------------------------------------------------ |
| `Amazon URL Parser / ASIN Extractor` | URL → ASIN 抽出、バリデーション                            |
| `Schema Registry`                    | GraphQL スキーマ / DTO 型定義 (TypeScript + Python スタブ) |
| `Audit Logger`                       | 構造化ログ、相関 ID、PII マスキング                            |
| `Safeguard Policy`                   | 上限・冷却の定数と判定関数（mobile と backend で共有）              |

## 設計の判断ポイント（ユーザー回答必須）

以下の判断ポイントについて \[Answer]: タグに回答してください。推奨案を先に提示します。

### Q1. コンポーネント粒度（Backend Lambda の切り方）

* **A**: UC 単位で太い Lambda（1 UC = 1 Lambda、保守性低め・デプロイ単位大）

* **B**: FR 単位で細かい Lambda（多数の小 Lambda、管理負荷高）

* **C（推奨）**: **ドメインサービス単位**（Debate Service / Reel Service / Cart Service / ... 上記「主要コンポーネント暫定案」と同粒度）

\[Answer]:C

### Q2. API プロトコル

* **A（推奨）**: **Amplify Data (GraphQL / AppSync) を中核**にし、CDK 拡張 Lambda は AppSync Direct Lambda Resolver または別途 API Gateway (REST) で公開

* **B**: Amplify Data は使わず、全部 REST + API Gateway + 生 DynamoDB

* **C**: GraphQL/REST 混在だが、両方とも Amplify Data 経由

Amplify Gen 2 採用決定と Q2=ii（ハイブリッド）から **A 推奨**。

\[Answer]:B。Amplifyを使う必要がなければ、Amplifyを削除してください。

### Q3. Bedrock 呼び出しの実装位置

* **A**: Amplify Functions (Node.js/TS) から呼び出し

* **B（推奨）**: **CDK 拡張 Lambda (Python 3.13)** から呼び出し。PBT（Hypothesis）と LLM ストリーミング制御がしやすい

* **C**: 両方（簡単な要約は TS、論破ストリーミングは Python）

\[Answer]:B

### Q4. カート追撃の時間差トリガー方式

* **A（推奨）**: **EventBridge Scheduler で一発スケジュール**（30m / 6h / 24h の 3 ジョブ登録）→ 各ジョブが Lambda → End User Messaging Push

* **B**: Step Functions ステートマシン（Wait state 3 段）→ Lambda → Push

* **C**: DynamoDB TTL + EventBridge Pipes

A は実装がシンプル、コスト低、スケール容易。B は可視化しやすいが複雑。C は特殊要件向き。

\[Answer]:A

### Q5. Mobile 状態管理

* **A（推奨）**: **Amplify Data の useQuery/useMutation + React Context + Zustand**（軽量、Amplify 統合、学習コスト低）

* **B**: Redux Toolkit + RTK Query（定型だが強力、学習コスト中）

* **C**: Jotai or Recoil（アトミック、新しい）

* **D**: React Context + hooks のみ（規模的にギリギリ）

\[Answer]:A

### Q6. 全体アーキテクチャパターン

* **A**: Clean Architecture（ドメイン/ユースケース/インフラのレイヤ厳格分離）

* **B（推奨）**: **Feature-based + 軽いレイヤード**（機能フォルダ内で UI/hooks/api を同居、Lambda はドメインサービス単位で分離）— 4 名× 3 週間 MVP 向き

* **C**: Hexagonal / Ports & Adapters（テスト容易、初期コスト高）

\[Answer]:B

### Q7. キャッシュ戦略

* **A（推奨）**: **ElastiCache Redis**（Creators API 商品メタ TTL 6 時間、セッション、レート制限）

* **B**: DynamoDB DAX（Creators API メタは DynamoDB に保存しつつ高速化）

* **C**: Amplify Data の組み込みキャッシュのみ

Creators API のレート制限を考慮すると A 推奨。

\[Answer]:A

### Q8. ログ・監査の強度

* **A**: CloudWatch Logs のみ（最小、開発速度優先）

* **B（推奨）**: **CloudWatch Logs + X-Ray + カスタム CloudWatch Metrics（委ね EXP / 論破成功率 / カート介入成約率）**（SECURITY-02/03/14 + 北極星指標の可視化）

* **C**: + Datadog / New Relic 等サードパーティ APM（コスト増）

\[Answer]:B

## 計画チェックリスト

### 計画フェーズ

* [x] Step 1: 要件書 v0.4 / ストーリー / ペルソナ読み込み

* [x] Step 2-5: 本プラン作成（設計スコープ / 前提 / 暫定コンポーネント / 判断ポイント）

* [ ] Step 6-7: ユーザーが Q1〜Q8 の \[Answer]: タグに回答

* [ ] Step 8-9: 回答の曖昧性解析（必要なら追加質問）

* [ ] Step 11-14: 計画の最終承認

### 生成フェーズ

* [x] `aidlc-docs/inception/application-design/components.md` 生成（Mobile / Backend / Shared 各層のコンポーネント定義と責務）
* [x] `aidlc-docs/inception/application-design/component-methods.md` 生成（各コンポーネントのメソッドシグネチャ、入出力型）
* [x] `aidlc-docs/inception/application-design/services.md` 生成（サービス層のオーケストレーションパターン）
* [x] `aidlc-docs/inception/application-design/component-dependency.md` 生成（Mermaid 依存関係図、通信パターン、データフロー）
* [x] `aidlc-docs/inception/application-design/application-design.md` 生成（上記 4 文書の統合ビュー）
* [x] Extension 適合チェック（SECURITY-01〜15 / PBT-01〜10 のうち本ステージで該当する項目）
* [x] INVEST / ドキュメント品質検証（診断エラーなし、リンク整合）
* [ ] 生成物の承認を得る
* [ ] `aidlc-state.md` 更新（Application Design 完了マーク）


## 確定した設計決定サマリ（Step 8-9 回答分析結果）

ユーザー回答を受けて、矛盾解析後に以下で確定（詳細は [audit.md](../../audit.md) 参照）。

| # | 項目 | 確定値 |
|---|---|---|
| Q1 | Backend Lambda の粒度 | **C**: ドメインサービス単位（Debate / Reel / Cart / 他 計 10 個前後） |
| Q2 | API プロトコル | **B**: REST + API Gateway + Lambda + 生 DynamoDB（**Amplify Data 不採用**） |
| Q3 | Bedrock 呼び出し位置 | **B**: CDK 管理 Lambda (Python 3.13)（Hypothesis PBT 親和性） |
| Q4 | カート追撃トリガー | **A**: EventBridge Scheduler で 30m / 6h / 24h の 3 ジョブ登録 |
| Q5 | Mobile 状態管理 | **TanStack Query（サーバー）+ Zustand（クライアント）**（Amplify Data hooks 不採用） |
| Q6 | 全体アーキテクチャ | **B**: Feature-based + 軽レイヤード |
| Q7 | キャッシュ戦略 | **A**: ElastiCache Redis（Creators API キャッシュ TTL 6h） |
| Q8 | ログ・監査 | **B**: CloudWatch Logs + X-Ray + カスタムメトリクス |

追加決定:

- **AWS Amplify Gen 2 を全面削除**（Auth / Data / Functions / CLI すべて不採用）
- 認証は `amazon-cognito-identity-js` でモバイルから Cognito を直接叩く
- IaC は **AWS CDK (TypeScript) 単独**
- 要件書を v0.5 に更新（§7 技術スタック、§8 A-2）
