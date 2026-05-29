# Unit-5 Cart Intercept — Sequence Diagrams

> Q1〜Q8 確定に基づく主要シーケンス。Mermaid 記法で記述、Unit-1 [sequence-diagrams.md](../../unit-1-platform/functional-design/sequence-diagrams.md) の表記規則に整合。
>
> 参照: [functional-design.md](./functional-design.md) / [data-model.md](./data-model.md)

---

## 1. Share Extension → カート監視リスト登録（US-03-01）

Q1 = A（Expo Config Plugin + App Group）/ Q2 = A（Mobile 即時抽出 + Backend 再検証）反映。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant Amazon as Amazon Shopping<br/>アプリ
    participant ShareExt as YUDANE Share<br/>Extension (iOS/Swift)
    participant AppGroup as App Group<br/>UserDefaults
    participant Main as YUDANE メインアプリ<br/>(RN)
    participant ASIN as S-01<br/>AsinExtractor
    participant API as API Gateway<br/>(Cognito Authorizer)
    participant B04 as B-04<br/>CartIntakeHandler
    participant DDB as CartWatchItems<br/>(DDB)
    participant B11 as B-11<br/>CreatorsApiClient
    participant Redis as ElastiCache<br/>(6h cache)
    participant B05 as B-05<br/>schedule_attacks()
    participant Sched as EventBridge<br/>Scheduler

    User->>Amazon: 商品ページで「共有」→ YUDANE 選択
    Amazon->>ShareExt: 商品 URL を渡す（別プロセス起動）
    ShareExt->>ShareExt: Activation Rule で Amazon URL 確認
    ShareExt->>AppGroup: pendingShareUrls に URL を append
    ShareExt-->>User: Extension UI 即閉じる
    ShareExt->>Main: URL Scheme yudane://share で起動
    
    Main->>AppGroup: consumePendingUrl()
    AppGroup-->>Main: { url, receivedAt }
    Main->>ASIN: extractAsin(url)
    ASIN-->>Main: asin (10 文字)
    
    alt asin が null
        Main-->>User: Toast「商品として認識できなかったよ」<br/>(US-03-01 AC-5)
    else asin が有効
        Main->>API: POST /v1/cart-watch-items<br/>Idempotency-Key: uuid7<br/>{ url, asin }
        API->>API: Cognito JWT 検証
        API->>B04: invoke
        
        B04->>B04: with_idempotency middleware<br/>(Unit-1 §3.2)
        B04->>ASIN: extract_asin(url) で再検証<br/>(SECURITY-05)
        ASIN-->>B04: backend_asin
        
        alt mobile_asin ≠ backend_asin
            B04-->>API: 400 asin-mismatch
            API-->>Main: 400 ProblemDetails
            Main-->>User: Toast「URL がおかしいよ」+ 監査ログ
        else 一致
            B04->>DDB: GetItem(USER#u, CART#asin)
            DDB-->>B04: existing or null
            
            alt existing.status == watching
                B04-->>API: 200 + isNewlyCreated=false
            else 新規 or dismissed
                B04->>B11: get_item_by_asin(asin)
                B11->>Redis: GET asin:{asin}
                
                alt キャッシュヒット
                    Redis-->>B11: productMeta
                else キャッシュミス
                    B11->>B11: Creators API 呼出<br/>(承認前はダミー §8 A-10)
                    B11->>Redis: SETEX 6h
                end
                
                B11-->>B04: productMeta
                B04->>DDB: PutItem<br/>status=watching<br/>GSI1PK=STATUS#watching
                B04->>B05: schedule_attacks(<br/>userId, itemId, asin, now)
                
                par 30m / 6h / 24h ジョブ並列作成
                    B05->>Sched: CreateSchedule(name=cart-attack-..-30m)
                and
                    B05->>Sched: CreateSchedule(name=cart-attack-..-6h)
                and
                    B05->>Sched: CreateSchedule(name=cart-attack-..-24h)
                end
                
                B05-->>B04: AttackSchedule { 30m, 6h, 24h }
                B04->>DDB: UpdateItem attackSchedule=...
                B04-->>API: 201 + isNewlyCreated=true
            end
            
            API-->>Main: CartIntakeResponse
            Main-->>User: 取込アニメ + Toast「監視中だよ」<br/>(2 秒以内、US-03-01 AC-3)
        end
    end
```

---

## 2. 30m / 6h / 24h 追撃通知の発火（US-03-02）

Q3 = A（テンプレートベース）/ Q4 = A（One-time Schedule）/ Q5 = C（End User Messaging Endpoint）反映。
**2 巡目セルフレビュー後修正**: Scheduler Input に `asin` を追加（B-06 が CartWatchItems を `CART#asin` SK で直接 GetItem する）。

```mermaid
sequenceDiagram
    autonumber
    participant Sched as EventBridge<br/>Scheduler
    participant B06 as B-06<br/>NotificationDispatcher
    participant DDB_Cart as CartWatchItems
    participant DDB_User as Users
    participant DDB_Safe as SafeguardStates
    participant S03 as S-03<br/>SafeguardPolicy
    participant Tpl as notification_<br/>templates.py
    participant EUM as End User<br/>Messaging Push
    participant DDB_Log as NotificationLogs
    actor User as ユーザー (端末)

    Sched->>B06: 発火 { userId, itemId, asin, step }<br/>(at 時刻精度)

    B06->>DDB_Cart: GetItem(USER#u, CART#asin)<br/>(asin で直接アクセス)
    DDB_Cart-->>B06: item { status, productMeta, ... }

    alt status in (dismissed, purchased)
        B06-->>Sched: skip + log info<br/>(配信せず終了)
    else watching / notified-*
        B06->>DDB_User: GetItem(USER#u, PROFILE)
        DDB_User-->>B06: user { pushEndpointId, displayName, safeguard.* }

        B06->>DDB_Safe: GetItem(USER#u, SAFEGUARD#yyyy-mm)
        DDB_Safe-->>B06: state { spent, limit, cooldownUntil, cooldownOn, quietWeekOn }

        B06->>S03: evaluate_notification(<br/>cooldown_on, cooldown_until,<br/>quiet_week_on, monthly_used, monthly_limit)
        S03-->>B06: decision: allow | block

        alt decision == block
            Note over B06,DDB_Log: Property 5 遵守
            B06->>DDB_Log: PutItem<br/>status=suppressed_by_safeguard
            B06-->>Sched: end
        else decision == allow
            B06->>Tpl: TEMPLATES[step]
            Tpl-->>B06: 10 patterns
            B06->>B06: random.choice + format<br/>(商品名/価格/ユーザー名<br/>displayName 空時は「あなた」)

            B06->>EUM: SendMessages<br/>Address: pushEndpointId<br/>Deep Link: yudane://cart-attack/{asin}?step=...
            Note over Sched,EUM: 配信失敗時は EventBridge<br/>RetryPolicy で 2 回再試行<br/>(MaximumEventAgeInSeconds=600)

            alt 配信成功
                EUM-->>B06: MessageResponse
                B06->>DDB_Cart: transition_status<br/>watching → notified-{step}<br/>(ConditionExpression)
                B06->>DDB_Log: PutItem<br/>status=sent, copy=...
                EUM-->>User: APNs / FCM 通知到達
            else 配信失敗
                EUM-->>B06: error
                B06->>DDB_Log: PutItem<br/>status=failed
            end
        end
    end
```

---

## 3. 通知タップ → 論破モード遷移（US-03-02 AC-3 / Q7 = A）

Q7 = A（CartInterceptScreen 経由 → 論破ボタン → DebateScreen）反映。
**2 巡目セルフレビュー後修正**: Deep Link / API パスを `asin` ベースに統一。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant OS as 端末 OS<br/>(APNs/FCM)
    participant Main as YUDANE メインアプリ<br/>(M-09)
    participant Cart as M-05<br/>CartInterceptScreen
    participant API as API Gateway<br/>(Lambda Authorizer)
    participant LA as Lambda Authorizer<br/>(Unit-7 / S-03 直接)
    participant DDB_Cart as CartWatchItems
    participant DDB_Safe as SafeguardStates
    participant B02 as B-02<br/>DebateLlmService
    participant Bedrock as Bedrock<br/>Claude Haiku 4.5
    participant Debate as M-04<br/>DebateScreen

    OS->>User: 通知表示<br/>「{product}、まだ気になってる？」
    User->>OS: 通知タップ
    OS->>Main: Deep Link: yudane://cart-attack/{asin}?step=6h

    Main->>Main: onNotificationTap(payload)
    Main->>Main: payload.productId 検証

    alt productId 不正 / 欠落
        Main->>Cart: navigate(mode=list)<br/>(Property 3 fallback)
    else productId 正常
        Main->>Cart: navigate(mode=detail, asin=productId, currentStep=6h)

        Cart->>API: GET /v1/cart-watch-items/{asin}
        API->>DDB_Cart: GetItem(USER#u, CART#asin)
        DDB_Cart-->>API: item
        API-->>Cart: CartWatchItemDto

        Cart-->>User: 商品カード + 追撃タイムライン<br/>(30m ✓, 6h ◀ 現在, 24h)<br/>「論破する」「いらない」「Amazon で買う」

        User->>Cart: 「論破する」タップ
        Cart->>API: POST /v1/debate-sessions<br/>{ trigger: "cart-attack", productId: asin }<br/>Idempotency-Key: uuid7

        API->>LA: Lambda Authorizer 起動<br/>(Q2 = C ハイブリッド、Unit-1 §4)
        LA->>DDB_Safe: GetItem(USER#u, SAFEGUARD#yyyy-mm)
        DDB_Safe-->>LA: safeguardState
        LA->>LA: S-03 evaluate_cooldown<br/>(VPC 外、直接 import)

        alt block
            LA-->>API: 403 Forbidden
            API-->>Cart: 409 ProblemDetails<br/>(safeguard block)
            Cart-->>User: Toast「今日は静かな日にしたじゃん」<br/>+ SafeguardScreen 誘導
        else allow / warn
            LA-->>API: Allow + context.safeguard
            API->>B02: invoke (VPC 外, SnapStart)
            B02->>B02: ストレスレベル推定<br/>+ M-1 + M-2 併走プロンプト合成
            B02->>Bedrock: InvokeModelWithResponseStream
            Bedrock-->>B02: SSE token stream
            B02-->>API: SSE
            API-->>Cart: SSE
            Cart->>Debate: navigate(sessionId, stream)
            Debate-->>User: タイピング演出<br/>(初回トークン 300ms 以内)
        end
    end
```

---

## 4. 「いらない」で監視解除 + 残追撃ジョブ取消（US-03-02 AC-4）

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant Cart as M-05<br/>CartInterceptScreen
    participant API as API Gateway
    participant B04 as B-04<br/>(dismiss handler)
    participant DDB as CartWatchItems
    participant Sched as EventBridge<br/>Scheduler

    User->>Cart: 「いらない」タップ
    Cart->>Cart: 楽観的更新<br/>(リストから即除去)
    Cart->>API: DELETE /v1/cart-watch-items/{asin}
    API->>B04: invoke (dismiss_lambda_handler)

    B04->>DDB: GetItem(USER#u, CART#asin)
    DDB-->>B04: item { attackSchedule, status }
    
    alt status in (purchased, dismissed)
        B04-->>API: 204 (idempotent)
    else watching / notified-*
        par 残ジョブを並列キャンセル
            B04->>Sched: DeleteSchedule(schedule_30m)
            alt 既に発火 / 削除済
                Sched-->>B04: ResourceNotFoundException<br/>(無視)
            else
                Sched-->>B04: ok
            end
        and
            B04->>Sched: DeleteSchedule(schedule_6h)
        and
            B04->>Sched: DeleteSchedule(schedule_24h)
        end
        
        B04->>DDB: transition_status<br/>* → dismissed<br/>SET ttl = now + 7d<br/>REMOVE GSI1PK, GSI1SK<br/>(Sparse 化)
        B04-->>API: 204
    end
    
    API-->>Cart: 204
    Cart-->>User: Toast「了解、忘れとくね」
```

---

## 5. Push 通知トークン登録 / 更新（Q5 = C 反映）

```mermaid
sequenceDiagram
    autonumber
    participant App as M-09<br/>PushNotificationHandler
    participant OS as 端末 OS<br/>(APNs/FCM)
    participant API as API Gateway
    participant PT as POST /v1/push-tokens<br/>(B-04 内 or 別 handler)
    participant DDB_User as Users
    participant EUM as End User Messaging<br/>Push API

    App->>OS: requestPermissionsAsync()
    OS-->>App: granted | denied
    
    alt denied
        App->>App: Telemetry: push.permission_denied
        App-->>App: end (登録なし)
    else granted
        App->>OS: getDevicePushTokenAsync()
        OS-->>App: { token, type: APNS|GCM }

        App->>App: idempotencyKey = uuidv5(token.data,<br/>PUSH_TOKEN_NAMESPACE)
        App->>API: POST /v1/push-tokens<br/>Idempotency-Key: idempotencyKey (UUID v5)<br/>{ token, platform }
        API->>PT: invoke
        
        PT->>DDB_User: GetItem(USER#u, PROFILE)
        DDB_User-->>PT: user { pushEndpointId? }
        
        alt 既存 endpointId あり（トークン更新）
            PT->>EUM: UpdateEndpoint<br/>(endpointId, address=token)
            EUM-->>PT: ok
        else 新規
            PT->>EUM: UpdateEndpoint<br/>(endpointId=ulid, address=token, channelType)
            EUM-->>PT: { endpointId }
            PT->>DDB_User: UpdateItem<br/>SET pushEndpointId, pushPlatform, pushTokenUpdatedAt
        end
        
        PT-->>API: 201 { endpointId }
        API-->>App: { endpointId }
    end
```

---

## 6. CartInterceptScreen から Amazon 遷移（US-03-04）

US-03-04（Special Link で Amazon アプリを Deep Link 起動）対応。Safeguard の月間上限到達時は遷移阻止、許可時は B-10 経由で Special Link 生成 + B-13 で遷移ログ + EXP 加算。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant Cart as M-05<br/>CartInterceptScreen
    participant API as API Gateway<br/>(Lambda Authorizer)
    participant LA as Lambda Authorizer<br/>(Unit-7 / S-03 直接)
    participant DDB_Safe as SafeguardStates
    participant B13 as B-13<br/>AmazonTransitionRecorder
    participant B10 as B-10<br/>AssociatesLinkGenerator
    participant DDB_Cart as CartWatchItems
    participant DDB_Trans as AmazonTransitions
    participant Amazon as Amazon Shopping アプリ

    User->>Cart: 「Amazon で買う」タップ
    Cart->>API: POST /v1/amazon-transitions<br/>{ context: "cart-attack",<br/>  productId: asin,<br/>  cartWatchItemId: itemId }<br/>Idempotency-Key: uuid7

    API->>LA: Lambda Authorizer 起動
    LA->>DDB_Safe: GetItem(USER#u, SAFEGUARD#yyyy-mm)
    DDB_Safe-->>LA: state
    LA->>LA: S-03 evaluate_monthly_limit(<br/>monthlyUsed, monthlyLimit)

    alt block (上限到達、US-03-05)
        LA-->>API: 403 Forbidden
        API-->>Cart: 409 ProblemDetails<br/>(safeguard-monthly-limit)
        Cart-->>User: Toast「今月はもう Amazon に飛ばせないよ」<br/>+ SafeguardScreen 誘導
    else allow / warn
        LA-->>API: Allow + context.safeguard
        API->>B13: invoke

        B13->>B10: generate_special_link(asin, user_id)
        B10-->>B13: SpecialLinkDto { url, tag }

        par 並列処理
            B13->>DDB_Trans: PutItem<br/>USER#u / TRANSITION#{ulid}<br/>{ productAsin, context, sessionId? }
        and
            B13->>DDB_Cart: transition_status<br/>watching/notified-* → purchased<br/>(Q8 = A ステータスマシン)
        and
            B13->>DDB_Safe: UpdateItem<br/>ADD spent :amount<br/>(月間消費額更新)
        end

        B13-->>API: ExpAwardDto { specialLink, exp }
        API-->>Cart: { specialLink, exp }
        Cart->>Cart: EXP +1 トースト
        Cart->>Amazon: Linking.openURL(specialLink)<br/>(Deep Link)
        Amazon-->>User: 商品ページ表示<br/>(決済は Amazon 側で完結、FR-CART-04)

        Note over Cart: 1.2 秒後、ダメ化レポートへ自動遷移<br/>(US-02-02 と整合)
    end
```

> **Unit-5 owner としての責任範囲**:
>
> - M-05 CartInterceptScreen の「Amazon で買う」ボタン UI と onPress ハンドラ実装
> - 「Amazon で買う」ボタン近傍に **Associates 開示文言**（「YUDANE は Amazon Associates として、紹介リンク経由の購入で Amazon から紹介料を受け取っています」）を常時表示（US-03-04 AC-3 / FR-PROFILE-04 / NG-8）
> - 遷移確認オーバーレイに **「Amazon に移動します」** + ASIN + 商品名 + Associates 開示の 1 枚を必ず挟む（FR-CART-05 / Q3 が UC-03 主導線にも適用）
> - `POST /v1/amazon-transitions` への呼出し
> - Linking.openURL での Special Link 起動
> - Safeguard block 時の UI フィードバック
>
> **Special Link のリンク短縮方針（US-03-04 AC-5 / Associates Operating Agreement 遵守）**:
>
> - **本 Unit ではリンク短縮を採用しない**。B-10 AssociatesLinkGenerator（Unit-4 owner）が生成する Amazon ドメインの Special Link（`https://www.amazon.co.jp/dp/{asin}?tag={associatesTag}` 形式）をそのまま `Linking.openURL` に渡す
> - 短縮を行うと「Amazon への遷移であることが不明瞭」になり Associates Operating Agreement 違反となるため、bit.ly / cuttly 等の短縮サービス利用は **明示的に禁止**
> - 表示上はオーバーレイで「Amazon に移動します」と明示するため、URL 文字列が長くても UX 上の問題なし
>
> **Unit-4 owner（B-13 / B-10）への依存**:
>
> - B-13 AmazonTransitionRecorder 本体実装は Unit-4 Reel owner（[unit-of-work.md Unit-4](../../../inception/application-design/unit-of-work.md#unit-4-reel-エージェント型リール-uc-02)）
> - B-10 AssociatesLinkGenerator が「Amazon ドメインを保ったまま」Special Link を生成する責務を持つことを Unit-4 functional-design で確認必須
> - 本 Unit はリクエスト送信側のみ責任を持つ
> - API 契約 `POST /v1/amazon-transitions` は Unit-4 owner が OpenAPI 定義し、Unit-5 owner はクライアント側を実装

---

## 7. B-05 リトライバッチ（NFR Design Q4 = A' 追加）

部分失敗で `attackSchedule` が空の watching アイテムを 15 分間隔で補完。3 回失敗で `watching_orphaned` に遷移。

```mermaid
sequenceDiagram
    autonumber
    participant Sched as EventBridge<br/>rate(15 minutes)
    participant Retry as B-05<br/>cart_attack_scheduler_retry
    participant DDB_Cart as CartWatchItems
    participant EB as EventBridge<br/>Scheduler
    participant Alarm as CloudWatch<br/>Alarm 5
    actor MemberD as Member D<br/>(オンコール)

    Note over Sched: 15 分ごとに自動発火
    Sched->>Retry: invoke

    Retry->>DDB_Cart: GSI1 Query<br/>(GSI1PK=STATUS#watching,<br/>attackSchedule 不完全)
    DDB_Cart-->>Retry: [items × 100 件]

    loop 各 item に対して
        Retry->>Retry: retry_count = item.retry_count or 0
        alt retry_count < 3
            Retry->>EB: schedule_attacks(<br/>userId, itemId, asin, createdAt)
            alt 成功
                EB-->>Retry: AttackSchedule
                Retry->>DDB_Cart: UpdateItem<br/>SET attackSchedule, retry_count=0
                Retry->>Retry: metric("cart.scheduler.retry_succeeded", 1)
            else 失敗
                EB-->>Retry: error
                Retry->>DDB_Cart: UpdateItem<br/>ADD retry_count :one
                Retry->>Retry: metric("cart.scheduler.retry_failed", 1)
            end
        else retry_count >= 3
            Retry->>DDB_Cart: transition_status<br/>(watching → watching_orphaned)
            Note over Retry,Alarm: 手動復旧待ち状態
            Retry->>Alarm: cart.scheduler.retry_failed メトリクス累積
        end
    end

    Note over Alarm: 15 min 内に 5 件超
    Alarm->>MemberD: SNS → Slack #yudane-emergency<br/>「watching_orphaned 遷移が頻発」
    MemberD->>MemberD: §5.3.3 オンコール手順<br/>「Lambda 同時実行不足？」<br/>「Scheduler API 制限？」確認
    alt 復旧可能
        MemberD->>DDB_Cart: 手動 UpdateItem<br/>(watching_orphaned → watching, retry_count=0)
        Note over MemberD: 次の 15 分サイクルでリトライ再開
    end
```

> **設計上の注意点**:
>
> - `retry_count` 属性を CartWatchItem に追加（NFR Design Q4 = A' 反映、data-model.md §1.2 の追加属性として定義）
> - リトライ batch 自体が失敗（Lambda Error）した場合は `cart_attack_scheduler_retry` の Lambda Error Alarm（Alarm 4）が発火
> - 同一アイテムを繰り返し処理しないよう **GSI1 Query 結果を retry_count 昇順** で返却
> - 100 件超のアイテムが滞留する場合、次回起動で残りを処理（自然な逐次補完）

---

## 8. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: Unit-5 内のシーケンス（intake / attack / dismiss / push token）と Unit-1（Lambda Authorizer / S-03 / IdempotencyKeys）/ Unit-3（DebateLlmService）/ Unit-4（B-11 CreatorsApiClient）/ Unit-7（SafeguardStates）連携が時系列で可視化 |
| ドキュメント品質 | **強化**: 5 系統のシーケンス図に Q1〜Q8 確定が反映、Property 1〜5 の不変条件と整合 |
| AI-DLC プロセス | **強化**: Unit-1 sequence-diagrams.md と同一テンプレートで作成、整合性確保 |
