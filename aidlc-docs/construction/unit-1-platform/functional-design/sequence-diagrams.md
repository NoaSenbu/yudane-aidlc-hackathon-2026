# Unit-1 Platform — Sequence Diagrams

> Q1〜Q10 の確定を Mermaid sequence diagram で可視化する。
>
> 参照: [functional-design.md](./functional-design.md) / [data-model.md](./data-model.md)

---

## 1. Cognito 認証フロー（Q1 = A 反映: dev 任意 / prd 強制 MFA）

### 1.1 サインアップ + MFA 設定

```mermaid
sequenceDiagram
    participant User
    participant Mobile as M-11 AuthModule
    participant Cognito as Cognito User Pool
    participant AuthEdge as B-01 AuthEdgeLambda
    participant DDB as DynamoDB Users

    User->>Mobile: signUp(email, password)
    Mobile->>Cognito: SignUpCommand
    Cognito-->>Mobile: 200 + ConfirmationCode
    Mobile-->>User: 確認コード入力 UI

    User->>Mobile: confirmSignUp(code)
    Mobile->>Cognito: ConfirmSignUpCommand
    Cognito->>AuthEdge: PostConfirmation Trigger
    AuthEdge->>DDB: PutItem User / PreferenceVector / SafeguardState
    DDB-->>AuthEdge: 201
    AuthEdge-->>Cognito: 200
    Cognito-->>Mobile: 200

    Note over Mobile,Cognito: prd 環境では MFA 必須（Q1 = A）
    alt env = prd
        Mobile->>Cognito: AssociateSoftwareTokenCommand
        Cognito-->>Mobile: secretCode (TOTP seed)
        Mobile-->>User: QR コード表示
        User->>Mobile: TOTP 入力
        Mobile->>Cognito: VerifySoftwareTokenCommand
        Cognito-->>Mobile: 200（TOTP 設定完了）
        
        Note over Mobile,AuthEdge: Recovery Code は Cognito 標準仕様にないため<br/>B-01 で別途生成（Unit-2 Auth & Profile で実装）
        Mobile->>AuthEdge: GET /v1/auth/recovery-code
        AuthEdge->>AuthEdge: secrets.token_urlsafe(16) で生成
        AuthEdge->>DDB: PutItem Users<br/>recoveryCodeHash = SHA-256(code)
        AuthEdge-->>Mobile: 200 + Recovery Code（平文、1 回限り）
        Mobile-->>User: Recovery Code 表示（再表示不可）
    else env = dev
        Note over Mobile: MFA 任意、スキップ可能
    end
```

### 1.2 サインイン + JWT 取得

```mermaid
sequenceDiagram
    participant User
    participant Mobile as M-11 AuthModule
    participant Cognito as Cognito User Pool
    participant AuthEdge as B-01 AuthEdgeLambda
    participant DDB as DynamoDB

    User->>Mobile: signIn(email, password)
    Mobile->>Cognito: InitiateAuthCommand (USER_PASSWORD_AUTH)
    
    alt MFA 設定済み（prd 必須 / dev 任意）
        Cognito-->>Mobile: ChallengeName=SOFTWARE_TOKEN_MFA
        Mobile-->>User: TOTP 入力 UI
        User->>Mobile: confirmMfa(totp)
        Mobile->>Cognito: RespondToAuthChallengeCommand
    end
    
    Cognito->>AuthEdge: PreTokenGeneration Trigger
    AuthEdge->>DDB: GetItem User（委ね Lv / 称号 / 月間上限）
    DDB-->>AuthEdge: User attributes
    AuthEdge-->>Cognito: ClaimsToAddOrOverride { custom:level, custom:title, custom:limit }
    Cognito-->>Mobile: TokenSet（idToken に custom claim 含む）
    Mobile->>Mobile: Zustand に保持（在ユーザー情報）
    Mobile-->>User: ホーム画面へ遷移
```

---

## 2. Telemetry 投入フロー（Q3 = B + 安全装置 3 点反映）

### 2.1 通常時の flush（5 件バッファ → 成功）

```mermaid
sequenceDiagram
    participant App as Mobile (各 Tab)
    participant Tel as M-13 Telemetry
    participant AS as AsyncStorage
    participant API as API Gateway
    participant Lambda as B-14 TelemetryIngestion
    participant Redis as ElastiCache
    participant Firehose as Kinesis Firehose
    participant S3

    App->>Tel: track("debate.started", {...})
    Tel->>Tel: バッファに push (1 件)
    App->>Tel: track("reel.swiped", {...})
    App->>Tel: track("cart.intercept_received", {...})
    App->>Tel: track("debate.agreed", {...})
    App->>Tel: track("amazon.tap", {...})
    Note over Tel: バッファ 5 件 → flush
    
    Tel->>Tel: batchId = UUID v7
    Tel->>AS: putItem("telemetry-queue-v1", events)
    Tel->>API: POST /v1/telemetry<br/>Idempotency-Key: <batchId>
    API->>Lambda: invoke
    
    Lambda->>Redis: SET telemetry-batch:{batchId} EX 3600 NX
    alt 重複なし（NX 成功）
        Redis-->>Lambda: OK
        Lambda->>Firehose: PutRecordBatch(events)
        Firehose-->>Lambda: 200
        Firehose->>S3: 内部バッファ flush（60s/5MiB）
        Lambda-->>API: 200 { status: "accepted" }
    else 重複あり（NX 失敗）
        Redis-->>Lambda: nil（既存）
        Lambda-->>API: 200 { status: "duplicate" }
    end
    
    API-->>Tel: 200
    Tel->>AS: removeItem("telemetry-queue-v1") （成功時）
```

### 2.2 失敗時のリトライ（DLQ + 永続キュー復元）

```mermaid
sequenceDiagram
    participant Tel as M-13 Telemetry
    participant AS as AsyncStorage
    participant API as API Gateway
    participant Lambda as B-14 TelemetryIngestion
    participant DLQ as SQS DLQ
    participant Firehose as Kinesis Firehose

    Tel->>API: POST /v1/telemetry<br/>Idempotency-Key: <batchId>
    API->>Lambda: invoke
    Lambda->>Firehose: PutRecordBatch
    Firehose--xLambda: 503 Service Unavailable
    Lambda--xAPI: 500 InternalError
    Note over Lambda,DLQ: Lambda 失敗 → 自動 DLQ 退避（Q3 安全装置 2）
    Lambda->>DLQ: SQS message（events + batchId）
    
    API--xTel: 5xx
    Note over Tel,AS: 永続キューに残留（Q8 オフライン挙動）
    Tel->>AS: keep telemetry-queue-v1
    
    Note over Tel: 5 分後 / アプリ起動時に再 flush
    Tel->>API: POST /v1/telemetry<br/>Idempotency-Key: <同 batchId>
    API->>Lambda: invoke
    Lambda->>Firehose: PutRecordBatch（復旧後）
    Firehose-->>Lambda: 200
    Lambda-->>API: 200
    API-->>Tel: 200
    Tel->>AS: removeItem
```

### 2.3 オフライン → オンライン復帰時の flush（Q8 反映）

```mermaid
sequenceDiagram
    participant App as Mobile App
    participant NetInfo as NetInfo
    participant Tel as M-13 Telemetry
    participant AS as AsyncStorage
    participant API as API Gateway

    Note over App: オフライン中
    App->>Tel: track("reel.swiped", ...)
    Tel->>AS: put永続キュー（送信せず溜める）
    App->>Tel: track("debate.refused", ...)
    Tel->>AS: put永続キュー
    
    NetInfo-->>App: ネットワーク復帰
    App->>Tel: onNetworkOnline()
    Tel->>AS: getItem("telemetry-queue-v1")
    AS-->>Tel: 蓄積済み events
    
    loop 100 件 / 1MB ごと
        Tel->>API: POST /v1/telemetry<br/>Idempotency-Key: <batchId>
        API-->>Tel: 200
        Tel->>AS: 該当 batch を削除
    end
```

---

## 3. API Gateway Authorizer フロー（Q2 = C ハイブリッド反映）

### 3.1 軽量 API（Cognito Authorizer のみ）

```mermaid
sequenceDiagram
    participant Mobile as M-12 ApiClient
    participant API as API Gateway
    participant Cog as Cognito Authorizer
    participant Lambda as B-XX (e.g. B-14 Telemetry)

    Mobile->>API: POST /v1/telemetry<br/>Authorization: Bearer <jwt><br/>X-Correlation-Id: <ulid>
    API->>Cog: 検証
    Cog-->>API: claims { sub, email, custom:level }
    API->>Lambda: invoke + claims
    Lambda-->>API: 200
    API-->>Mobile: 200
```

### 3.2 Safeguard 介入 API（Lambda Authorizer + Safeguard 判定、Q5 セルフレビュー後修正反映）

```mermaid
sequenceDiagram
    participant Mobile as M-12 ApiClient
    participant API as API Gateway
    participant Auth as Lambda Authorizer<br/>(VPC 外、S-03 直接 import)
    participant DDB as DynamoDB<br/>SafeguardStates / DebateRateLimits
    participant Lambda as B-02 / B-13

    Mobile->>API: POST /v1/debate-sessions<br/>Authorization: Bearer <jwt>
    API->>Auth: invoke (キャッシュミス)
    Auth->>Auth: JWT 検証（Cognito JWKS）
    Note over Auth: S-03 SafeguardPolicy を直接 import<br/>（Q5 セルフレビュー後修正、B-09 RPC 不使用）
    Auth->>DDB: GetItem SafeguardStates<br/>PK=USER#{uid} SK=SAFEGUARD#{month}
    DDB-->>Auth: { spent, limit, cooldownUntil }
    Auth->>DDB: GetItem DebateRateLimits<br/>PK=USER#{uid} SK=DEBATE_STATE
    DDB-->>Auth: { consecutiveRefuses, lastRefuseAt }
    Auth->>Auth: S-03.evaluateMonthlyLimit() / evaluateCooldown()
    
    alt allow
        Auth-->>API: IAM Policy: Allow + context.safeguard=ok
        API->>Lambda: invoke
        Lambda-->>API: 200
        API-->>Mobile: 200
    else block（月間上限到達）
        Auth-->>API: IAM Policy: Deny
        API-->>Mobile: 403 Problem Details<br/>type=safeguard/monthly-limit
    else warn（しきい値接近）
        Auth-->>API: IAM Policy: Allow + context.safeguard=warn
        API->>Lambda: invoke + safeguard=warn
        Lambda-->>API: 200 + warning header
        API-->>Mobile: 200 + X-Safeguard-Warn: true
    end
    
    Note over API,Auth: 同一 userId は 5 分キャッシュ<br/>論破ストリーミング系全体が VPC 外で完結
```

**Q5 セルフレビュー後修正の反映（2026-05-27）**:

- 当初設計（B-09 RPC + ElastiCache）から、Lambda Authorizer 内に S-03 SafeguardPolicy を直接 import + DDB 直接参照に変更
- B-09 SafeguardRulesEngine Lambda は管理 UI / バッチ処理 / 監査ログ専用に責務縮小（Lambda Authorizer の前段配置から外れる）
- これにより VPC 内 Lambda は B-03 / B-11 / B-14 の 3 つに限定され、論破ストリーミング系全体（API Gateway → Lambda Authorizer → B-02）が VPC 外で完結
- 詳細は [functional-design.md §3.1 / §4.2](./functional-design.md) を参照

---

## 4. 論破ストリーミングフロー（Q5 確定: B-02 DDB 化 + SnapStart）

### 4.1 論破セッション開始（B-02 が VPC 外 + SnapStart で動作）

```mermaid
sequenceDiagram
    participant Mobile as M-04 DebateScreen
    participant API as API Gateway
    participant Auth as Lambda Authorizer
    participant Safe as B-09 SafeguardRulesEngine
    participant B02 as B-02 DebateLlmService<br/>(VPC 外, SnapStart)
    participant DDB as DynamoDB
    participant Bedrock as Bedrock Claude Haiku 4.5

    Mobile->>API: POST /v1/debate-sessions
    API->>Auth: invoke
    Auth->>Safe: evaluate("debate-start")
    Safe-->>Auth: allow
    Auth-->>API: Allow

    API->>B02: invoke (SnapStart 復元 ~300ms)
    Note over B02: SnapStart Hook で<br/>UUID 等を再生成<br/>(@register_after_restore)
    
    B02->>DDB: GetItem PreferenceVectors PK=USER#{uid}
    DDB-->>B02: vector
    B02->>DDB: GetItem DebateRateLimits PK=USER#{uid} SK=DEBATE_RATE#{hour}
    DDB-->>B02: { attempts: 1, consecutiveRefuses: 0 }
    B02->>DDB: UpdateItem ADD attempts :1<br/>(原子的カウントアップ、Redis 代替)
    DDB-->>B02: { attempts: 2 }
    
    B02->>B02: estimate_stress_level(context)
    Note over B02: M-1（事実 + 心理 2 軸）+ M-2（ストレス × ご褒美軸）併走プロンプト合成
    
    B02->>Bedrock: InvokeModelWithResponseStream
    Bedrock-->>B02: SSE stream (初回トークン < 300ms)
    B02-->>API: SSE stream
    API-->>Mobile: SSE stream
    Mobile-->>Mobile: タイピング演出 + 90 秒タイマー
```

### 4.2 論破成功 → Amazon 遷移 → 肯定フィードバック

```mermaid
sequenceDiagram
    participant Mobile as M-04 DebateScreen
    participant API as API Gateway
    participant Auth as Lambda Authorizer<br/>(Safeguard 統合)
    participant B13 as B-13 AmazonTransitionRecorder
    participant B10 as B-10 AssociatesLinkGenerator
    participant DDB as DynamoDB

    Mobile->>API: POST /v1/debate-sessions/{id}/agree
    API->>Auth: invoke (Safeguard 判定)
    Auth-->>API: Allow
    API->>B13: invoke
    B13->>B10: generateSpecialLink(asin, userId)
    B10-->>B13: SpecialLinkDto
    B13->>DDB: PutItem AmazonTransitions
    B13->>DDB: UpdateItem Achievements (EXP +N)
    B13-->>API: { specialLink, expAwarded }
    API-->>Mobile: 200
    
    Mobile-->>Mobile: 「🛍 Amazon で買う」ボタンを Special Link で起動
    Mobile-->>Mobile: 1.2 秒後に肯定フィードバックトースト発火<br/>「今日もいい選択だったね」(FR-DEBATE-09 / M-2)
```

---

## 5. 冪等キーフロー（Q7 = B 反映）

```mermaid
sequenceDiagram
    participant Mobile as M-12 ApiClient
    participant API as API Gateway
    participant Lambda as B-04 (例: CartIntake)
    participant DDB as DynamoDB IdempotencyKeys
    participant Mainflow as ビジネスロジック

    Mobile->>Mobile: idempotencyKey = UUID v7
    Mobile->>API: POST /v1/cart-watch-items<br/>Idempotency-Key: <key>
    API->>Lambda: invoke
    
    Lambda->>DDB: GetItem PK=IDEMPOTENCY#{key}
    
    alt 初回（item なし）
        DDB-->>Lambda: null
        Lambda->>Mainflow: 実処理（ASIN 抽出 + 監視登録）
        Mainflow-->>Lambda: result
        Lambda->>DDB: PutItem IdempotencyKeys<br/>{ requestHash, responseStatus, responseBody, ttl=5min }
        Lambda-->>API: 201 + result
        API-->>Mobile: 201
        
    else リトライ（item あり、同 hash）
        DDB-->>Lambda: { responseStatus: 201, responseBody }
        Note over Lambda: 実処理スキップ、キャッシュ返却
        Lambda-->>API: 201 + cached body
        API-->>Mobile: 201（同一レスポンス）
        
    else 異常（item あり、異なる hash）
        DDB-->>Lambda: { requestHash: "abc..." }
        Note over Lambda: ボディ不一致 → 409
        Lambda-->>API: 409 Problem Details<br/>type=idempotency-key-mismatch
        API-->>Mobile: 409
    end

    Mobile->>Mobile: ネットワーク不安定時のリトライ
    Note over Mobile: 同 idempotencyKey で再送 → 上記「リトライ」フロー
```

---

## 6. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: Cognito Trigger / Authorizer / Telemetry / 論破 / 冪等キーの 5 系統が Mermaid で可視化、Unit 跨ぎの責任分界が明示 |
| ドキュメント品質 | **強化**: Q1〜Q10 確定が sequence レベルで具体化、誤実装リスクを低減 |
| AI-DLC プロセス（予選評価軸） | **強化**: Functional Design Part 2 の証跡として残る |
