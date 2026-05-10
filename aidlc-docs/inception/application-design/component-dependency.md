# Application Design — Component Dependencies

> コンポーネント間の依存関係、通信パターン、主要データフロー。Mermaid で可視化。  
> 参照: [Components](./components.md) / [Services](./services.md) / [Component Methods](./component-methods.md)

## 全体コンポーネント依存図

```mermaid
graph LR
    subgraph Mobile["📱 Mobile (RN + TypeScript)"]
        AppShell[M-01 AppShell]
        Home[M-02 HomeScreen]
        Reel[M-03 ReelScreen]
        Debate[M-04 DebateScreen]
        Cart[M-05 CartInterceptScreen]
        Report[M-06 DameReportScreen]
        Safe[M-07 SafeguardScreen]
        ShareExt[M-08 ShareExtension]
        Push[M-09 PushHandler]
        Cal[M-10 CalendarNative]
        Auth[M-11 AuthModule]
        ApiCli[M-12 ApiClient]
        Tel[M-13 Telemetry]
    end

    subgraph Gateway["🚪 API Gateway + Authorizer"]
        APIGW[API Gateway REST]
        Authz[Cognito Authorizer]
    end

    subgraph Backend["☁️ Backend Lambdas"]
        AuthEdge[B-01 AuthEdge]
        Debate2[B-02 DebateLLM]
        Reel2[B-03 ReelRecommend]
        Intake[B-04 CartIntake]
        Sched[B-05 CartAttackSched]
        Notify[B-06 NotifDispatch]
        CalSvc[B-07 CalendarPredict]
        PrefUp[B-08 PreferenceUpdate]
        Safeguard[B-09 SafeguardRules]
        Link[B-10 AssociatesLink]
        Creators[B-11 CreatorsApiCli]
        Audit[B-12 AuditLogger]
        Trans[B-13 AmazonTransition]
        TelIn[B-14 TelemetryIngestion]
    end

    subgraph Stores["🗄️ Data Stores"]
        DDB[(DynamoDB)]
        Redis[(ElastiCache Redis)]
        S3[(S3)]
        OS[(OpenSearch Serverless)]
    end

    subgraph External["🌐 External"]
        Cognito[Amazon Cognito]
        Bedrock[Bedrock Claude + Titan]
        EUM[AWS End User Messaging]
        EventBridge[EventBridge Scheduler]
        AmazonAPI[Amazon Creators API]
        AmazonApp[Amazon App]
    end

    AppShell --> Home
    AppShell --> Reel
    AppShell --> Debate
    AppShell --> Cart
    AppShell --> Report
    AppShell --> Safe

    Home --> ApiCli
    Reel --> ApiCli
    Debate --> ApiCli
    Cart --> ApiCli
    Report --> ApiCli
    Safe --> ApiCli

    Auth --> Cognito
    ShareExt --> ApiCli
    Push --> AppShell
    Cal --> ApiCli

    ApiCli --> APIGW
    ApiCli --> Tel

    APIGW --> Authz
    Authz --> Cognito
    APIGW --> Debate2
    APIGW --> Reel2
    APIGW --> Intake
    APIGW --> Safeguard
    APIGW --> CalSvc
    APIGW --> Trans
    APIGW --> Safe
    APIGW --> TelIn

    Cognito --> AuthEdge

    Debate2 --> Bedrock
    Debate2 --> PrefUp
    Debate2 --> Creators
    Reel2 --> OS
    Reel2 --> PrefUp
    Reel2 --> Creators
    Intake --> Creators
    Intake --> Sched
    Sched --> EventBridge
    EventBridge --> Notify
    Notify --> EUM
    EUM --> Push
    CalSvc --> Bedrock

    PrefUp --> DDB
    Trans --> Link
    Link --> AmazonApp
    Safeguard --> DDB

    Creators --> Redis
    Creators --> AmazonAPI

    Debate2 --> DDB
    Reel2 --> DDB
    Intake --> DDB
    Trans --> DDB
    AuthEdge --> DDB

    Debate2 --> Audit
    Reel2 --> Audit
    Intake --> Audit
    Notify --> Audit
    Safeguard --> Audit
    Trans --> Audit
```

---

## 主要データフロー 1: UC-03 カート介入 + UC-01 論破（Share → 追撃 → 論破 → Amazon 遷移）

> 注: 本図では Share Extension から ApiClient への流れを簡略化。実際は Platform Channel 経由で RN 側の `registerAsCartWatchItem(asin)` メソッド（`M-08` と `M-12` の協調）を経由する。

```mermaid
sequenceDiagram
    autonumber
    actor User as 悠介
    participant AmApp as Amazon Shopping
    participant ShareExt as M-08 ShareExt
    participant ApiCli as M-12 ApiClient
    participant APIGW as API Gateway
    participant Intake as B-04 CartIntake
    participant Creators as B-11 CreatorsAPI
    participant Redis as ElastiCache
    participant CreatorsAPI as Amazon Creators API
    participant DDB as DynamoDB
    participant Sched as B-05 AttackSched
    participant EB as EventBridge Scheduler
    participant Notify as B-06 NotifDispatch
    participant EUM as End User Messaging
    participant Device as 端末 APNs/FCM
    participant Debate as B-02 DebateLLM
    participant Bedrock as Amazon Bedrock
    participant Safe as B-09 Safeguard
    participant Trans as B-13 AmazonTransition
    participant Link as B-10 AssociatesLink

    User->>AmApp: 商品をカートに入れる、迷う
    User->>ShareExt: 共有 → YUDANE
    ShareExt->>ApiCli: ASIN 付きで登録リクエスト
    ApiCli->>APIGW: POST /cart-items
    APIGW->>Intake: invoke
    Intake->>Creators: getItemByAsin(asin)
    Creators->>Redis: GET cache
    alt cache miss
        Creators->>CreatorsAPI: fetch product
        CreatorsAPI-->>Creators: ProductMeta
        Creators->>Redis: SET TTL 6h
    end
    Creators-->>Intake: ProductMeta
    Intake->>DDB: put CartWatchItem
    Intake->>Sched: schedule_attacks(userId, itemId)
    Sched->>EB: create 3 schedules (30m/6h/24h)
    Intake-->>APIGW: 2xx CartWatchItemDto
    APIGW-->>ApiCli: response
    ApiCli-->>User: トースト「監視リストに追加」

    Note over EB: 30 分経過
    EB->>Notify: invoke (step=30m)
    Notify->>EUM: send push (friend tone copy)
    EUM->>Device: APNs/FCM
    Device->>User: 「さっきのイヤホン 3 回目だよね。1 分話そう」

    User->>Device: 通知タップ
    Device->>ApiCli: deep link with itemId
    ApiCli->>APIGW: POST /debate-sessions (trigger=cart-attack)
    APIGW->>Safe: evaluate(userId, "debate-start")
    Safe-->>APIGW: allow
    APIGW->>Debate: invoke
    Debate->>Bedrock: stream prompt (fact+psychology)
    Bedrock-->>Debate: stream tokens
    Debate-->>APIGW: SSE
    APIGW-->>ApiCli: SSE
    ApiCli-->>User: 論破テキスト表示

    User->>ApiCli: 「🛍 Amazon で買う」
    ApiCli->>APIGW: POST /amazon-transitions
    APIGW->>Safe: evaluate(userId, "amazon-transition")
    Safe-->>APIGW: allow
    APIGW->>Trans: invoke
    Trans->>Link: generate_special_link(asin, userId)
    Link-->>Trans: SpecialLinkDto
    Trans->>DDB: write AmazonTransition + EXP
    Trans-->>APIGW: { url }
    APIGW-->>ApiCli: { url }
    ApiCli->>AmApp: Deep Link open
    AmApp->>User: 商品ページ（カート入り状態）
    Note over User,AmApp: 決済は Amazon 側で完結
```

---

## 主要データフロー 2: UC-02 リール + 論破 / Amazon 遷移

```mermaid
sequenceDiagram
    autonumber
    actor User as 悠介
    participant Reel as M-03 ReelScreen
    participant ApiCli as M-12 ApiClient
    participant APIGW as API Gateway
    participant ReelSvc as B-03 ReelRecommend
    participant OS as OpenSearch
    participant PrefUp as B-08 PreferenceVector
    participant CalSvc as B-07 CalendarPredict
    participant Creators as B-11 CreatorsAPI
    participant Debate as B-02 DebateLLM
    participant Trans as B-13 AmazonTransition

    User->>Reel: 画面オープン
    Reel->>ApiCli: GET /reel
    ApiCli->>APIGW: request
    APIGW->>ReelSvc: invoke
    ReelSvc->>PrefUp: get vector
    ReelSvc->>CalSvc: get upcoming categories
    ReelSvc->>OS: vector search (嗜好 × 時刻 × 予定)
    OS-->>ReelSvc: candidate ASINs
    ReelSvc->>Creators: batch get meta
    Creators-->>ReelSvc: ProductMetas
    ReelSvc-->>APIGW: ReelPage
    APIGW-->>User: カード表示

    alt 左スワイプ（買わない）
        User->>Reel: swipe left
        Reel->>ApiCli: POST /debate-sessions (trigger=reel-refuse)
        ApiCli->>Debate: (SSE stream)
    else ダブルタップ（即 Amazon）
        User->>Reel: double tap
        Reel->>ApiCli: POST /amazon-transitions
        ApiCli->>Trans: Special Link 生成
    else 右スワイプ（後で見る）
        User->>Reel: swipe right
        Reel->>ApiCli: POST /cart-items (originTrigger=reel)
    end
```

---

## 主要データフロー 3: UC-04 カレンダー連動

```mermaid
sequenceDiagram
    autonumber
    participant Cal as M-10 CalendarNative
    participant ApiCli as M-12 ApiClient
    participant CalSvc as B-07 CalendarPredict
    participant Bedrock as Bedrock
    participant ReelSvc as B-03 ReelRecommend
    participant Debate as B-02 DebateLLM

    Note over Cal: 端末ローカルで 14 日先まで取得
    Cal->>Cal: 予定本文をローカルでカテゴリ分類
    Note right of Cal: 本文は送らない (FR-CAL-05)
    Cal->>ApiCli: POST /calendar-categories (カテゴリのみ)
    ApiCli->>CalSvc: invoke
    CalSvc->>Bedrock: カテゴリ → 商品カテゴリ推定
    Bedrock-->>CalSvc: 商品カテゴリリスト
    CalSvc->>CalSvc: 嗜好ベクトルと組合せ
    CalSvc-->>ApiCli: EventCategoryPrediction

    Note over ReelSvc: 次回リール生成時に
    ReelSvc->>CalSvc: get upcoming categories
    CalSvc-->>ReelSvc: ctx
    ReelSvc->>ReelSvc: 「○○ のためのエージェント提案」タグ挿入

    Note over Debate: 論破時に
    Debate->>CalSvc: get context for this product
    CalSvc-->>Debate: 予定情報
    Debate->>Debate: 「来週月曜のプレゼン、印象を決める場面」プロンプト合成
```

---

## 主要データフロー 4: 認証（サインアップ → MFA → サインイン → トークンリフレッシュ）

```mermaid
sequenceDiagram
    autonumber
    actor User as 悠介
    participant Auth as M-11 AuthModule
    participant Cognito as Amazon Cognito
    participant Edge as B-01 AuthEdgeLambda
    participant DDB as DynamoDB

    Note over User,DDB: サインアップ
    User->>Auth: email + password 入力
    Auth->>Cognito: SignUp
    Cognito-->>Auth: userSub + 確認コード送信
    User->>Auth: 確認コード入力
    Auth->>Cognito: ConfirmSignUp
    Cognito->>Edge: Post Confirmation Trigger
    Edge->>DDB: User / PreferenceVector / SafeguardState 初期化
    Edge-->>Cognito: OK
    Cognito-->>Auth: confirmed

    Note over User,DDB: サインイン + TOTP MFA
    User->>Auth: email + password 入力
    Auth->>Cognito: InitiateAuth (USER_PASSWORD_AUTH)
    Cognito-->>Auth: SOFTWARE_TOKEN_MFA Challenge
    User->>Auth: TOTP コード入力
    Auth->>Cognito: RespondToAuthChallenge
    Cognito->>Edge: Pre Token Generation Trigger
    Edge-->>Cognito: 委ね Lv / 月間上限を claim に付与
    Cognito-->>Auth: IdToken + AccessToken + RefreshToken
    Auth->>Auth: SecureStore に保存

    Note over Auth,Cognito: アクセストークン期限切れ時
    Auth->>Cognito: InitiateAuth (REFRESH_TOKEN_AUTH)
    Cognito-->>Auth: 新 AccessToken
```

---

## 通信パターン

| パターン | 使用箇所 | 根拠 |
|---|---|---|
| **Sync REST (HTTPS)** | Mobile ↔ Backend 全般 | 認証のみ Amplify Auth を介し、データ通信は AWS SDK v3 で直接叩くシンプル構成 |
| **SSE (Server-Sent Events)** | Debate ストリーミング | LLM トークン逐次表示、WebSocket より軽量 |
| **非同期 EventBridge Scheduler** | Cart 追撃 (30m/6h/24h) | 時間遅延ジョブ。Step Functions より軽量 |
| **EventBridge（日次 cron）** | PreferenceVectorUpdater | バッチジョブ |
| **ネイティブ Platform Channel** | Share / Push / Calendar | RN の JS で扱えない OS 固有機能 |
| **Deep Link (custom scheme / Universal Link)** | YUDANE → Amazon App | Amazon 遷移 |
| **Cognito JWT** | 全 API 認証 | SECURITY-08/12 |

---

## データストア配置ポリシー

| ストア | 用途 | データ |
|---|---|---|
| **DynamoDB** | メインデータストア | `Users` / `PreferenceVectors` / `CartWatchItems` / `DebateSessions` / `DebateMessages` / `AmazonTransitions` / `Achievements` / `SafeguardStates` / `NotificationLogs` / `ReelImpressions` |
| **S3** | 大型オブジェクト | 商品画像キャッシュ / データエクスポート用 dump / ユーザーアバター |
| **ElastiCache Redis** | 低レイテンシ読み取り / レート制限 | Creators API 商品メタ（TTL 6h）/ セッションスロットル / 論破レート制限 |
| **OpenSearch Serverless** | ベクトル検索 | 商品埋め込み / 嗜好埋め込みマッチング |

PII を含むユーザー特定データはすべて DynamoDB（KMS CMEK 暗号化、SECURITY-01）。S3 は画像のみ。

---

## 依存方向の制約（循環禁止）

- Mobile → Backend への一方通行（Push 通知は非同期、Mobile は handler で受けるのみ）
- Backend 内でのクロスサービス呼出は **最小限**。SVC-01 論破は SVC-02/03/04 から直接呼ばれることはなく、各 SVC から論破トリガー API を叩くのみ
- `S-03 SafeguardPolicy` は Mobile と Backend 両方で import（同じ判定を走らせる）

---

## 障害時フォールバック

| 障害 | フォールバック |
|---|---|
| Bedrock 応答なし | 論破は「すみません、今回は見送りますか？」の定型文 / 事前生成テンプレート |
| Creators API レート制限 | Redis キャッシュで応答、TTL 延長、新規登録は一時拒否 |
| OpenSearch 応答遅延 | 静的推薦カタログへ切替（§6.7） |
| EventBridge Scheduler 失敗 | DynamoDB に TTL 予約も設定しておき、TTL トリガーで救済 |
| End User Messaging 配信失敗 | 次回アプリ起動時に「見逃した通知」として In-App で再表示 |
