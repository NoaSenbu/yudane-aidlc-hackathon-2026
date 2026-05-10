# Application Design — Components

> YUDANE のコンポーネント定義（Mobile / Backend / Shared 3 層）  
> 参照: [要件書 v0.5](../requirements/requirements.md) / [設計プラン](../plans/application-design-plan.md) / [統合ビュー](./application-design.md)

## 設計原則

- **Feature-based + 軽レイヤード**: 機能フォルダ内に UI / hooks / API 呼び出しを同居。Backend はドメインサービス単位で Lambda 分割
- **Amplify 不採用**: React Native + AWS SDK v3 直接利用、Auth は `amazon-cognito-identity-js`
- **IaC 単独**: AWS CDK (TypeScript) でインフラを 1 つの手段で管理
- **ハードウェア前提**: iOS 15+ / Android API 29+ / ナローバンド対応

---

## Mobile 層（React Native + TypeScript）

| # | コンポーネント | 責務 | インターフェース |
|---|---|---|---|
| M-01 | `AppShell` | ナビゲーション / Auth ゲート / タブバー / ディープリンク受付 | React Navigation / `useAuthSession` hook |
| M-02 | `HomeScreen` | エージェント稼働 hero / カート監視リスト / カレンダー連動カード / サブダッシュボード（UC-03/04/06） | `useHomeSnapshot` hook（TanStack Query） |
| M-03 | `ReelScreen` | 縦型スワイプ UI / 論破遷移 / Amazon 遷移確認オーバーレイ（UC-02） | `useReelFeed`, `useAmazonRedirect` |
| M-04 | `DebateScreen` | 論破チャット UI / タイピング演出 / 90 秒タイマー（UC-01） | `useDebateSession` (SSE or polling) |
| M-05 | `CartInterceptScreen` | Share 到着アニメ / 商品取込カード / 3 段追撃タイムライン可視化（UC-03） | `useCartWatchItem` |
| M-06 | `DameReportScreen` | 委ね Lv / Before-After 指標 / 行動変容ナラティブ / 引用カード | `useDameReport` |
| M-07 | `SafeguardScreen` | 月間上限 / 冷却モード / NG カテゴリ / データエクスポート（UC-08） | `useSafeguardSettings` |
| M-08 | `ShareExtensionNativeModule` | iOS Share Extension（Swift）/ Android Share Target（Kotlin）。共有URL の受け取りとアプリへの引き渡し | Platform Channel（JSI）経由で RN に ASIN を渡す |
| M-09 | `PushNotificationHandler` | APNs / FCM トークン登録 / 受信 / タップ時の deep link ルーティング | `react-native-firebase` / `@react-native-community/push-notification-ios` |
| M-10 | `CalendarNativeModule` | iOS EventKit / Google Calendar 読み取り。端末ローカルで予定カテゴリ分類 | Platform Channel 経由、分類結果のみ RN へ |
| M-11 | `AuthModule` | Cognito User Pool 認証（サインアップ / ログイン / MFA / トークン管理） | `amazon-cognito-identity-js` |
| M-12 | `ApiClient` | REST API 呼び出しのラッパー、認証ヘッダ付与、エラーハンドリング、相関 ID 付与 | `fetch` + TanStack Query |
| M-13 | `Telemetry` | クライアントイベント計測（画面遷移 / タップ / スワイプ / Amazon 遷移） | CloudWatch カスタムメトリクス REST エンドポイント経由 |

### Mobile 層の状態管理

- **サーバー状態**: TanStack Query（キャッシュ / 再取得 / optimistic updates / useQuery / useMutation）
- **クライアント状態**: Zustand（UI 状態 / モーダル / トースト / ユーザー設定ドラフト）
- **永続化**: `@react-native-async-storage/async-storage`（Zustand の persist ミドルウェア）

---

## Backend 層（AWS Lambda / Python 3.12、CDK 管理）

| # | コンポーネント | 責務 | トリガー |
|---|---|---|---|
| B-01 | `AuthEdgeLambda` | Cognito トリガーのカスタマイズ（サインアップ後処理、トークン clam 付与） | Cognito User Pool トリガー |
| B-02 | `DebateLlmService` | 論破プロンプト合成（商品メタ + 嗜好 + 時刻 + 予定 + 達成率） + Bedrock ストリーミング | API Gateway → Lambda（REST ストリーミング） |
| B-03 | `ReelRecommendationService` | 嗜好ベクトル × コンテキストから商品候補生成、OpenSearch でベクトル検索 | API Gateway |
| B-04 | `CartIntakeHandler` | Share 経由の URL 受取、ASIN 抽出、Creators API 呼出、カート監視登録 | API Gateway |
| B-05 | `CartAttackScheduler` | 登録商品に対する 30m / 6h / 24h 追撃ジョブ作成（EventBridge Scheduler） | Cart 登録イベント（B-04 から同期呼出） |
| B-06 | `NotificationDispatcher` | AWS End User Messaging Push で APNs/FCM に通知配信、コピー生成 | EventBridge Scheduler 発火 |
| B-07 | `CalendarPredictionService` | カレンダー予定カテゴリ → 商品カテゴリ推定（LLM / ルールベース混合） | API Gateway |
| B-08 | `PreferenceVectorUpdater` | 購買履歴 / スキップ / 論破成功率から嗜好ベクトル更新 | EventBridge（日次 cron） |
| B-09 | `SafeguardRulesEngine` | 月間上限 / 冷却モード / 負債検知の判定、遷移阻止 | 各 API Lambda の前段 middleware、または API Gateway Authorizer |
| B-10 | `AssociatesLinkGenerator` | Amazon Associates Special Link URL 生成、タグ付与 | 他 Lambda から内部呼出 |
| B-11 | `CreatorsApiClient` | Amazon Creators API 呼出、ElastiCache Redis でキャッシュ（TTL 6h）、レート制限管理 | 他 Lambda から内部呼出 |
| B-12 | `AuditLogger` | 構造化ログ、相関 ID、PII マスキング、CloudWatch Logs / X-Ray 統合 | ライブラリ |
| B-13 | `AmazonTransitionRecorder` | 「🛍 Amazon で買う」タップ記録、EXP 加算、Associates レポートとの突合 | API Gateway |
| B-14 | `TelemetryIngestionService` | フロントからの計測イベントを受け取り、CloudWatch Metrics (EMF) と S3 Data Lake へ投入。北極星指標の可視化基盤 | API Gateway |

### Backend 層の API 仕様

- **プロトコル**: REST over HTTPS（TLS 1.2+）
- **認証**: Cognito JWT / API Gateway Authorizer
- **スキーマ**: OpenAPI 3.1（[shared/schema](#shared-%E5%B1%A4) 参照）
- **Lambda ランタイム**: Python 3.12 + AWS Lambda Powertools（log / trace / metrics）
- **主要エンドポイント**:
  - `POST /cart-items` — Share 受信（B-04）
  - `GET /reel` — リール生成（B-03）
  - `POST /debate-sessions` — 論破開始（B-02、ストリーミング）
  - `POST /debate-sessions/{id}/messages` — 論破続行
  - `POST /amazon-transitions` — Amazon 遷移記録（B-13）
  - `GET /safeguard` / `PATCH /safeguard` — セーフガード設定（B-09）
  - `GET /report` — ダメ化レポート
  - `POST /users/{id}/profile` — オンボーディング情報登録（SVC-05）
  - `GET /users/{id}` / `PATCH /users/{id}` — ユーザー情報取得・更新
  - `DELETE /users/{id}` — アカウント削除（FR-AUTH-06）
  - `POST /calendar-categories` — 予定カテゴリ送信（端末ローカル分類後、B-07）
  - `POST /telemetry` — クライアントテレメトリ（B-14）

---

## Shared 層（TypeScript + Python 両対応）

| # | コンポーネント | 責務 |
|---|---|---|
| S-01 | `AsinExtractor` | Amazon URL から ASIN を正規表現抽出 + バリデーション。TypeScript と Python 両実装 |
| S-02 | `SchemaRegistry` | OpenAPI 3.1 スキーマ定義。TypeScript 型（`openapi-typescript`）と Python 型（`datamodel-code-generator`）を自動生成 |
| S-03 | `SafeguardPolicy` | 月間上限・冷却モード・負債検出の **ルール定数 + 判定関数**。Mobile と Backend で同じ判定が走る |
| S-04 | `TelemetryContracts` | カスタムメトリクス名、イベント型定義、PII マスキングルール |

### Shared 層の運用方針

- モノレポ構成で `shared/` を `mobile/` と `backend/` から import 可能にする（npm workspaces + Python editable install）
- TypeScript を正本とし、Python 型はコード生成で同期
- CI でスキーマ変更を検知して型再生成 → 双方のビルドで差分が出る場合は PR に警告

---

## コンポーネント数サマリ

- **Mobile**: 13
- **Backend**: 14
- **Shared**: 4
- **合計**: 31

---

## Extension 適合のハイレベルマッピング

| 層 | 主な適用 Extension ルール |
|---|---|
| Mobile | SECURITY-04 (HTTP ヘッダ、将来 Web 版向け)、SECURITY-08 (認可)、SECURITY-12 (認証 / トークン管理)、SECURITY-13 (SRI / 署名)、PBT-02 (round-trip: ローカルキャッシュ serialize) |
| Backend | SECURITY-01〜15 全面 / PBT-01〜10 全面（詳細は NFR Requirements と NFR Design で Unit ごとに定義） |
| Shared | PBT-07 (domain generator) / PBT-10 (example-based test 併存)、SECURITY-10 (SBOM) |
