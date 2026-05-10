# Application Design — Services

> 複数コンポーネントを束ねる **サービス層** の設計。オーケストレーションパターン、境界、責務。  
> 参照: [Components](./components.md) / [Component Methods](./component-methods.md) / [Dependencies](./component-dependency.md)

## 設計方針

本プロジェクトの「サービス」は **ドメイン横断のユースケース実行単位** を指す。Lambda 単位のコンポーネント（B-01〜B-13）を束ね、UC と 1 対 1 に近い形で責務を定義する。

- **Orchestrator の置き場所**: 主にフロント（Mobile 層）側のクライアントオーケストレーション + API Gateway の直接 Lambda 呼出を基本とする
- **Step Functions は採用しない**: 時間差追撃は EventBridge Scheduler 単独で実装可能で、Step Functions を入れるとコストと運用負荷が増えるため
- **非同期境界**: カート監視登録時のみ EventBridge に書き出す。論破・リール・遷移はすべて同期 REST

---

## サービス一覧

| # | サービス | 対応 UC | 主な役割 |
|---|---|---|---|
| SVC-01 | **Debate Orchestration Service** | UC-01 | 論破セッションのライフサイクル（開始・ストリーミング・終了・EXP 加算） |
| SVC-02 | **Reel Orchestration Service** | UC-02 | リール生成・スワイプ処理・Amazon 遷移導線 |
| SVC-03 | **Cart Intercept Orchestration Service** | UC-03 | Share 受信・追撃スケジュール・通知・論破遷移 |
| SVC-04 | **Calendar-driven Recommendation Service** | UC-04 / FR-CAL | カレンダー予定 → 商品カテゴリ → リール挿入・論破材料供給 |
| SVC-05 | **User Profile & Preference Service** | UC-05 / UC-07 | オンボーディング / 嗜好ベクトル管理 / EXP / 称号 / 称号付与 |
| SVC-06 | **Safeguard Service** | UC-08 / §9 NG | 月間上限・冷却モード・負債検知・データ削除 |
| SVC-07 | **Notification Service** | 横断 | 通知戦略の統一窓口、配信結果集計 |

---

## SVC-01 Debate Orchestration Service

### 責務

- 論破セッションの開始、ストリーミング配信、タイマー監視、終了判定
- **M-1（判断力の弱体化）と M-2（購買快楽のストレス解消剤化）の併走プロンプト合成**（FR-DEBATE-02 / FR-DEBATE-09）
- Amazon 遷移後の肯定フィードバック発火（M-2 ドーパミン回路強化 / FR-DEBATE-09）
- 論破成功時の EXP 加算、嗜好ベクトル学習データ投入
- セーフガード発動時のクールダウン適用

### コンポーネント構成

- **Entry point**: M-04 DebateScreen ↔ `POST /debate-sessions`（B-02）
- **Core**: B-02 DebateLlmService（Bedrock ストリーミング）
- **Context 供給**:
  - 嗜好ベクトル: B-03 ReelRecommendationService
  - 予定カテゴリ: B-07 CalendarPredictionService
  - 商品メタ: B-11 CreatorsApiClient
  - **ストレスレベル推定**: B-02 DebateLlmService 内の `estimate_stress_level()` が B-12 AuditLogger の直近 7 日ログ（会議密度・残業時刻分布・深夜帯利用回数）とカレンダー連続予定数から算出（FR-DEBATE-09 / M-2）
- **Safeguard**: B-09 SafeguardRulesEngine（前段 middleware）
- **Persistence**: DynamoDB `DebateSessions` テーブル
- **Downstream**: 論破成功で B-13 AmazonTransitionRecorder → B-10 AssociatesLinkGenerator

### オーケストレーションパターン

```
[M-04 DebateScreen]
    ↓ POST /debate-sessions (M-1 事実/心理 + M-2 ご褒美軸の併走プロンプト生成)
[API Gateway] → [B-09 SafeguardRulesEngine] → [B-02 DebateLlmService]
    → [B-03 getPreferenceVector] → [B-11 getProductMeta] → [B-07 getEvents]
    → [B-02 estimateStressLevel] ← [B-12 AuditLogger 直近 7 日ログ]
    → Bedrock Invoke (streaming, Claude Haiku 4.5 / Sonnet 4.6)
    → SSE stream to client
    → [M-04 onAgree] → POST /amazon-transitions → [B-13 AmazonTransitionRecorder]
        → [B-10 AssociatesLinkGenerator] → Deep Link → Amazon App
    → M-04 に「今日もいい選択だったね」肯定フィードバックトースト (FR-DEBATE-09)
```

### 品質要件

- 初回トークン 300ms 以下（FR-DEBATE-03）
- 90 秒タイマー（FR-DEBATE-06）
- 3 回連続拒否でクールダウン（FR-DEBATE-05 / SVC-06 連動）
- ストレスレベルが mid 以上ではプロンプトに M-2 のご褒美軸コピーが必ず併走する（FR-DEBATE-09）
- Amazon 遷移後は 1.2 秒以内に肯定フィードバックトーストが発火する（FR-DEBATE-09 / M-2）

---

## SVC-02 Reel Orchestration Service

### 責務

- 嗜好 × 時刻 × カレンダー × 疲労度 の 5 軸でリール生成
- スワイプ（左=論破、右=カート監視、ダブルタップ=Amazon 遷移）のディスパッチ
- 所有感ラベル（「確保しておきました」）の動的生成

### コンポーネント構成

- **Entry**: M-03 ReelScreen ↔ `GET /reel`（B-03）
- **Core**: B-03 ReelRecommendationService
- **Embedding**: Titan Embeddings + OpenSearch Serverless
- **Context**: B-07 CalendarPredictionService の予定カテゴリ
- **Persistence**: DynamoDB `ReelImpressions`（閲覧ログ、A/B テスト用）
- **Downstream**: 左スワイプ → SVC-01 へ、右スワイプ → SVC-03 へ、ダブルタップ → SVC-01 または直接 B-13 → Amazon

### オーケストレーションパターン

```
[M-03 ReelScreen] ──GET /reel──> [B-03 ReelRecommendationService]
    ↓                                   ↓
    swipe events                  [OpenSearch Serverless] → vector search
                                        ↓
                                    候補商品 × 所有感ラベル生成
    ↓ onSwipeLeft → 論破モード遷移 (SVC-01)
    ↓ onSwipeRight → カート監視登録 (SVC-03)
    ↓ onDoubleTap → 確認オーバーレイ → Amazon 遷移 (B-13)
```

---

## SVC-03 Cart Intercept Orchestration Service

### 責務

- Share Extension 受信から追撃スケジューリング、通知配信、論破導線までの一貫した UX
- 3 段階追撃（30m / 6h / 24h）

### コンポーネント構成

- **Entry**: M-08 ShareExtensionNativeModule → M-12 ApiClient → `POST /cart-items`（B-04）
- **Core**: B-04 CartIntakeHandler + B-05 CartAttackScheduler
- **Product meta**: B-11 CreatorsApiClient（キャッシュ経由）
- **Notification**: B-06 NotificationDispatcher（EventBridge Scheduler → Lambda → End User Messaging Push）
- **Persistence**: DynamoDB `CartWatchItems` + EventBridge Scheduler jobs

### オーケストレーションパターン

```
Amazon Shopping App
    ↓ Share → YUDANE
[iOS Share Extension / Android Share Target] (M-08)
    ↓ Platform Channel (ASIN)
[M-12 ApiClient] ──POST /cart-items──> [B-04 CartIntakeHandler]
    ↓                                           ↓
    登録 response                        [S-01 extractAsin]
                                                ↓
                                        [B-11 CreatorsApiClient] (cached)
                                                ↓
                                        DynamoDB put CartWatchItem
                                                ↓
                                        [B-05 CartAttackScheduler]
                                                ↓
                                        EventBridge Scheduler (3 jobs)

[EventBridge Scheduler firing]
    ↓ each job invokes
[B-06 NotificationDispatcher]
    ↓ AWS End User Messaging Push
[APNs / FCM]
    ↓
[M-09 PushNotificationHandler]
    ↓ user tap
[M-01 AppShell.onDeepLink] → [M-05 CartInterceptScreen or M-04 DebateScreen]
```

### 品質要件

- Share 受信 → 登録完了: 2 秒以内（FR-CART-01 / §6.2）
- 初回追撃配信遅延: 30 秒以内（§6.2）
- 通知開封率 45%+（§6.1 北極星補助指標）

---

## SVC-04 Calendar-driven Recommendation Service

### 責務

- 予定タイトル・場所・参加者数から商品カテゴリ推定（端末ローカル → 確定カテゴリのみバックエンド）
- SVC-02 のリールと SVC-01 の論破プロンプトに予定コンテキストを供給

### コンポーネント構成

- **Entry**: M-10 CalendarNativeModule（端末ローカル分類）
- **Backend**: B-07 CalendarPredictionService（カテゴリ → 商品カテゴリへの変換）
- **Privacy**: 予定本文は送信しない（FR-CAL-05 / §9 NG-7）

### オーケストレーションパターン

```
[M-10 CalendarNativeModule]
    ↓ fetch 14 days (端末ローカル)
    ↓ 事前埋め込みルールでカテゴリ分類
    ↓ カテゴリ + 日付 + 参加者数（本文抜き）のみ送信
[POST /calendar-categories] → [B-07 CalendarPredictionService]
    ↓ LLM or ルールで商品カテゴリ推定
    ↓ User 嗜好ベクトルと組合せ
    ↓ SVC-02 Reel の推薦に「予定由来」タグ付きで挿入
    ↓ SVC-01 Debate の論破プロンプト context に予定情報を注入
```

---

## SVC-05 User Profile & Preference Service

### 責務

- オンボーディングでの予算感 / 趣味タグ / NG カテゴリ / 負債有無を収集
- Amazon 遷移履歴 / スキップ / 論破成功率 / カレンダーパターンを日次集計して嗜好ベクトル更新
- 委ね EXP / Lv / 称号 / Streak / ダメ化ポートフォリオ編集

### コンポーネント構成

- **Entry**: M-06 DameReportScreen / M-07 SafeguardScreen / M-11 AuthModule（初回オンボーディング）
- **Core**: B-08 PreferenceVectorUpdater（日次バッチ）
- **Persistence**: DynamoDB `Users`, `PreferenceVectors`, `AmazonTransitions`, `Achievements`

### オーケストレーションパターン

```
Cognito Post Confirmation Trigger (B-01)
    ↓ Init User, PreferenceVector (empty)
Onboarding Flow (Mobile)
    ↓ set budget, tags, NG cats, debt flag
    ↓ POST /users/{id}/profile
DailyBatch (EventBridge cron)
    ↓ invoke [B-08 PreferenceVectorUpdater]
    ↓ aggregate transitions, skips, debate outcomes, calendar patterns
    ↓ update vector
Amazon Transition (B-13)
    ↓ EXP 加算 → Lv.↑ 判定 → 称号付与
```

---

## SVC-06 Safeguard Service

### 責務

- 月間 Amazon 遷移上限の判定と阻止
- 冷却モード（手動 / 自動）の適用
- 負債保有者・未成年・上限到達時のセーフガード発動
- データエクスポート / アカウント削除

### コンポーネント構成

- **Core**: B-09 SafeguardRulesEngine（全 API Lambda の前段 authorizer）
- **Policy**: S-03 SafeguardPolicy（モバイル側でも同じ判定を走らせる UX 整合）
- **Persistence**: DynamoDB `SafeguardStates`（ユーザーごとの使用状況）

### オーケストレーションパターン

```
[任意の Amazon 遷移リクエスト / 論破開始リクエスト]
    ↓ API Gateway
[Authorizer or middleware] → [B-09 SafeguardRulesEngine]
    ↓ S-03 SafeguardPolicy.decideAllow
    ↓ allow → 通常処理継続
    ↓ block → 冷却モード画面 or セーフガード画面に誘導
    ↓ warn → 確認ダイアログ（M-07 から手動解除のログ保持）
```

---

## SVC-07 Notification Service

### 責務

- カート追撃、カレンダー予定前日通知、ダメ化レポート週次配信、セーフガード発動通知の **統一窓口**
- コピー生成ルールの集中管理（友達系トーン）

### コンポーネント構成

- **Core**: B-06 NotificationDispatcher
- **Delivery**: AWS End User Messaging Push（APNs / FCM）
- **Persistence**: DynamoDB `NotificationLogs`（配信履歴、開封率計測）

### 通知タイプ

| type | タイミング | SVC |
|---|---|---|
| `cart-attack-30m` | 登録 30 分後 | SVC-03 |
| `cart-attack-6h` | 登録 6 時間後 | SVC-03 |
| `cart-attack-24h` | 登録 24 時間後 | SVC-03 |
| `calendar-eve` | 予定前日夜 | SVC-04 |
| `report-weekly` | 毎週日曜 22 時 | SVC-05 |
| `safeguard-info` | 冷却発動 | SVC-06 |

---

## サービス相関マトリクス

|  | SVC-01 論破 | SVC-02 リール | SVC-03 カート | SVC-04 予定 | SVC-05 嗜好 | SVC-06 セーフ | SVC-07 通知 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| SVC-01 | — | ← swipe | ← tap | ← ctx | read/write EXP | check | — |
| SVC-02 | → swipe | — | → stash | ← ctx | read vec | check | — |
| SVC-03 | → tap | — | — | — | — | check | → push |
| SVC-04 | → ctx | → ctx | — | — | — | — | → push |
| SVC-05 | R/W | R | R | R | — | R | — |
| SVC-06 | gate | gate | gate | — | R | — | → push |
| SVC-07 | — | — | ← | ← | ← | ← | — |

`→` = 主体から呼び出す / `←` = 受け取る / `R/W` = 読み書き / `gate` = 認可判定

---

## FR-FUNNEL（購入導線 UX）の具現化マッピング

要件書 §5.10 の FR-FUNNEL は横断原則のため、どのサービス / コンポーネントで具現化されるかを明示する。

| FR-FUNNEL 項目 | 実装箇所（サービス / コンポーネント） |
|---|---|
| FR-FUNNEL-01 タッチポイント 4 種 | Share 受動 = **SVC-03** / 予定駆動 = **SVC-04** / 通知駆動 = **SVC-07** / 自発リール = **SVC-02** |
| FR-FUNNEL-02 介入タイミング最適化 | 時刻ブースト = **B-03 ReelRecommendationService** / 予定直前 = **SVC-04** / カート停滞 = **B-05 CartAttackScheduler** / セール・入荷 = **B-11 CreatorsApiClient** + **B-03** |
| FR-FUNNEL-03 2-3 タップ摩擦 | ダブルタップ決済 = **M-03 ReelScreen** / Share→YUDANE→Amazon 直通 = **SVC-03** / Authorizer 前段 Safeguard = **B-09** |
| FR-FUNNEL-04 個別最適化ループ | **B-08 PreferenceVectorUpdater** の日次バッチ（論破成功パターンを嗜好ベクトルに反映） |
| FR-FUNNEL-05 セーフガード最優先 | **SVC-06 Safeguard** が全 Amazon 遷移前に評価（gate パターン） |

---

## 北極星指標の集計経路

要件書 §6.1 の北極星指標「論破介入あたりの Amazon 遷移率」とその補助指標は、以下の経路で集計・可視化される。

1. **計測点**: M-13 Telemetry（クライアント側）と Backend の各 Lambda が `B-12 AuditLogger.metric()` で EMF 形式で CloudWatch Metrics に直接出力
2. **集計**: **B-08 PreferenceVectorUpdater** が日次バッチで CloudWatch Metrics API と DynamoDB から週次サマリを作成し、`WeeklyReports` テーブルに保存
3. **配信**:
   - M-06 DameReportScreen が `GET /report` で取得・表示
   - SVC-07 Notification の `report-weekly` 通知でプッシュ配信
4. **長期分析**: B-14 TelemetryIngestionService から S3 Data Lake（Parquet）に蓄積、将来 Athena / QuickSight 接続

これにより、論破 → Amazon 遷移率、カート介入成約率、深夜帯利用比率等の指標が **リアルタイム + 週次** の 2 段で可視化される。
