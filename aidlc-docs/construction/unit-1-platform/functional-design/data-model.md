# Unit-1 Platform — Data Model（DynamoDB Multi Table Design）

> Q6 = B 確定（Multi Table Design）に基づき、YUDANE 全体で使う DynamoDB テーブル設計を定義する。各テーブルは Unit owner と紐づける。
>
> 参照: [functional-design.md](./functional-design.md) §0 確定事項サマリ / [components.md](../../../inception/application-design/components.md) / [api-contracts.md §9](../../../../.kiro/steering/api-contracts.md)

---

## 1. テーブル一覧（Unit owner 別）

| Table | Unit owner | 用途 | Q5 関連 |
|---|---|---|---|
| `Users` | Unit-2 Auth & Profile | ユーザー基本情報 | — |
| `PreferenceVectors` | Unit-2 / Unit-4 | 嗜好ベクトル + B-02 が context として読む | Q5 で B-02 が直接 GetItem |
| `CartWatchItems` | Unit-5 Cart Intercept | カート監視リスト | — |
| `DebateSessions` | Unit-3 Debate | 論破セッション | — |
| `DebateMessages` | Unit-3 Debate | 論破セッション内のターン履歴 | — |
| `DebateRateLimits` | Unit-1 Platform（Unit-3 で利用） | **Q5 確定で新設**：B-02 のレート制限カウンタ（Redis 代替） | **Q5 確定の中核** |
| `IdempotencyKeys` | Unit-1 Platform | **Q7 確定で新設**：POST/PATCH の冪等キー検知 | Q7 確定の中核 |
| `AmazonTransitions` | Unit-4 / Unit-8 | 「🛍 Amazon で買う」タップ記録 | — |
| `Achievements` | Unit-2 / Unit-8 | 委ね Lv / 称号 / EXP | — |
| `SafeguardStates` | Unit-7 Safeguard | 月間上限 / 冷却モード状態 | — |
| `NotificationLogs` | Unit-5 / Unit-8 | プッシュ通知配信ログ | — |
| `ReelImpressions` | Unit-4 Reel | リール表示ログ（A/B テスト用） | — |
| `WeeklyReports` | Unit-8 Dame Report | 週次集計サマリ | — |

合計 **13 テーブル**。Unit-1 Platform で **共通設定（命名規約 / 暗号化 / バックアップ / TTL）** を定義し、各 Unit owner が個別テーブル設計を Functional Design で詳細化する。

---

## 2. 共通設定（Unit-1 で確定）

### 2.1 命名規約

- テーブル名: `yudane-<env>-<resource>`（例: `yudane-dev-users`, `yudane-prd-debate-sessions`）
- 個人 sandbox: `yudane-dev-<initial>-<resource>`（CDK Context `developer` キー注入）

### 2.2 暗号化

- すべて KMS CMEK 暗号化（SECURITY-01）
- KMS キーは Unit-1 Platform Stack で 1 つ作成、全テーブルで共有
- prd / dev とも `ap-northeast-1` 単独運用（Multi-Region Key は DR 対応時に backlog で再評価）

### 2.3 バックアップ

- prd: PITR（Point-in-Time Recovery）有効、35 日保持
- dev: PITR 無効、削除 OK

### 2.4 課金モード

- 全テーブル On-Demand（PAY_PER_REQUEST）
- 理由: ハッカソン規模では Provisioned のキャパシティ計画が過剰、On-Demand のコストで十分

### 2.5 削除保護

- prd: `removalPolicy = RETAIN` + DeletionProtection 有効
- dev: `removalPolicy = DESTROY`、DeletionProtection 無効

---

## 3. Unit-1 Platform 担当テーブル詳細

### 3.1 DebateRateLimits（Q5 確定で新設）

B-02 DebateLlmService の論破レート制限カウンタ（Redis 代替）。**hourBucket SK の試行回数**と**横断 SK の連続拒否カウンタ**を分離して、時間境界またぎの正確性を担保する。

#### 3.1.1 hourBucket SK（時間ごとの試行回数）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK`（Partition Key） | String | `USER#{userId}` |
| `SK`（Sort Key） | String | `DEBATE_RATE#{hourBucket}`（hourBucket = ISO8601 の 1 時間粒度、例 `2026-05-27T03:00Z`） |
| `attempts` | Number | 当該 1 時間内の論破試行回数（`UpdateItem ADD` で原子的更新） |
| `ttl` | Number | UNIX timestamp（hourBucket + 2 時間で自動削除） |

#### 3.1.2 DEBATE_STATE SK（横断状態、m1 修正で新設）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK`（Partition Key） | String | `USER#{userId}` |
| `SK`（Sort Key） | String | `DEBATE_STATE`（固定、ユーザー単位 1 件） |
| `consecutiveRefuses` | Number | 連続拒否回数（FR-DEBATE-05 クールダウン判定、時間境界またぎ可） |
| `lastRefuseAt` | String | 最終拒否時刻（ISO 8601） |
| `cooldownUntil` | String | クールダウン解除時刻（ISO 8601、3 回連続拒否で +3 時間） |
| `ttl` | Number | UNIX timestamp（最終更新から 30 日で自動削除、長期間ログインしないユーザー向け） |

#### アクセスパターン

```python
from datetime import datetime, timedelta, timezone

def increment_attempt(user_id: str) -> int:
    """論破試行のカウントアップ（B-02 内、hourBucket SK）"""
    now = datetime.now(timezone.utc)  # m5 修正: utcnow() deprecated
    hour_bucket = now.strftime("%Y-%m-%dT%H:00Z")
    response = table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": f"DEBATE_RATE#{hour_bucket}"},
        UpdateExpression="ADD attempts :one SET #ttl = :ttl",
        ExpressionAttributeNames={"#ttl": "ttl"},
        ExpressionAttributeValues={
            ":one": 1,
            ":ttl": int((now + timedelta(hours=2)).timestamp()),
        },
        ReturnValues="UPDATED_NEW",
    )
    return response["Attributes"]["attempts"]

def increment_refuse(user_id: str) -> tuple[int, str | None]:
    """連続拒否カウンタ更新（B-02 内、DEBATE_STATE SK、時間境界またぎ可）"""
    now = datetime.now(timezone.utc)
    response = table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "DEBATE_STATE"},
        UpdateExpression="ADD consecutiveRefuses :one SET lastRefuseAt = :now, #ttl = :ttl",
        ExpressionAttributeNames={"#ttl": "ttl"},
        ExpressionAttributeValues={
            ":one": 1,
            ":now": now.isoformat(),
            ":ttl": int((now + timedelta(days=30)).timestamp()),
        },
        ReturnValues="UPDATED_NEW",
    )
    consecutive = response["Attributes"]["consecutiveRefuses"]
    cooldown_until = None
    if consecutive >= 3:
        # 3 回連続拒否 → クールダウン適用（FR-DEBATE-05）
        cooldown_until = (now + timedelta(hours=3)).isoformat()
        table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": "DEBATE_STATE"},
            UpdateExpression="SET cooldownUntil = :cu",
            ExpressionAttributeValues={":cu": cooldown_until},
        )
    return consecutive, cooldown_until

def reset_consecutive_refuses(user_id: str) -> None:
    """論破成功時にカウンタリセット（B-02 / B-13 内）"""
    table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "DEBATE_STATE"},
        UpdateExpression="SET consecutiveRefuses = :zero",
        ExpressionAttributeValues={":zero": 0},
    )
```

#### Q5 設計ポイント

- **Redis vs DynamoDB のレイテンシ差**: DDB UpdateItem 5-10ms vs Redis INCR 1-3ms。Bedrock ストリーミングのトータル時間（〜3 秒）から見れば誤差レベル
- **B-02 を VPC 外に配置可能**にすることで SnapStart 適用 + ENI 新規作成リスク完全回避を実現
- **TTL 自動削除**で不要レコードを残さない（コスト最適化）。ただし DynamoDB TTL は最大 48h 遅延で削除されるため、判定側で `ttl < now()` を明示チェックする
- **m1 修正（2026-05-27）**: `consecutiveRefuses` を hourBucket SK から `DEBATE_STATE` SK に分離。hourBucket は 1 時間粒度のため時間境界またぎで連続拒否カウンタがリセットされる問題を排除。FR-DEBATE-05 の「3 回連続拒否」は時間境界をまたいでも検知される
- **m5 修正（2026-05-27）**: `datetime.now(timezone.utc)` で Python 3.12 deprecated の `utcnow()` を回避

---

### 3.2 IdempotencyKeys（Q7 確定で新設）

M-12 ApiClient が `Idempotency-Key` ヘッダで POST / PATCH のリトライを許可するための重複検知テーブル。**atomic lock パターン**で race condition を排除する。

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `IDEMPOTENCY#{idempotencyKey}`（UUID v7） |
| `SK` | String | `STATIC`（複合 PK 不要、PK 単独で OK） |
| `requestHash` | String | リクエストボディの **正規化済み** SHA-256（RFC 8785 JCS 風: `json.dumps(payload, sort_keys=True, separators=(",", ":"))`） |
| `status` | String | `IN_PROGRESS` / `COMPLETED` |
| `responseStatus` | Number | キャッシュされた HTTP ステータスコード（COMPLETED 時のみ） |
| `responseBodyKey` | String | S3 key（CMEK 暗号化バケット）— レスポンスボディは S3 に格納（DDB 400KB 上限と PII リスク回避） |
| `createdAt` | String | ISO 8601 |
| `ttl` | Number | UNIX timestamp（5 分後で自動削除、ただし最大 48h 遅延を考慮し読取側で `ttl < now` ガード必須） |

#### アクセスパターン（atomic lock-then-execute）

```python
# Backend Lambda 共通 middleware（B-12 AuditLogger に統合）
import hashlib
import json
from datetime import datetime, timedelta, timezone

def hash_request(body: str | dict) -> str:
    """リクエストボディの正規化済み SHA-256（RFC 8785 JCS 風）"""
    if isinstance(body, str):
        body = json.loads(body)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def with_idempotency(handler):
    def wrapper(event, context):
        key = event["headers"].get("Idempotency-Key")
        if not key:
            return handler(event, context)

        request_hash = hash_request(event["body"])
        now = datetime.now(timezone.utc)
        ttl = int((now + timedelta(minutes=5)).timestamp())

        # === atomic lock 取得（race condition 排除） ===
        try:
            idempotency_table.put_item(
                Item={
                    "PK": f"IDEMPOTENCY#{key}",
                    "SK": "STATIC",
                    "requestHash": request_hash,
                    "status": "IN_PROGRESS",
                    "createdAt": now.isoformat(),
                    "ttl": ttl,
                },
                # 新規 or TTL 期限切れの古いレコードのみ書き込み許可
                ConditionExpression="attribute_not_exists(PK) OR #ttl < :now",
                ExpressionAttributeNames={"#ttl": "ttl"},
                ExpressionAttributeValues={":now": int(now.timestamp())},
            )
            # lock 取得成功 → 通常実行
            result = handler(event, context)

            # 結果を S3 に格納（DDB 400KB 上限と PII リスク回避）
            response_body_key = f"idempotency/{key}.json"
            s3_client.put_object(
                Bucket=IDEMPOTENCY_BUCKET,
                Key=response_body_key,
                Body=json.dumps(result.body).encode("utf-8"),
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=KMS_KEY_ID,
            )

            # COMPLETED に更新
            idempotency_table.update_item(
                Key={"PK": f"IDEMPOTENCY#{key}", "SK": "STATIC"},
                UpdateExpression="SET #status = :completed, responseStatus = :rs, responseBodyKey = :rb",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":completed": "COMPLETED",
                    ":rs": result.statusCode,
                    ":rb": response_body_key,
                },
            )
            return result

        except idempotency_table.meta.client.exceptions.ConditionalCheckFailedException:
            # 既存レコードあり → 重複リクエスト
            existing = idempotency_table.get_item(
                Key={"PK": f"IDEMPOTENCY#{key}", "SK": "STATIC"}
            ).get("Item")

            # TTL 期限切れチェック（DynamoDB TTL は最大 48h 遅延で削除されるため明示ガード）
            if existing.get("ttl", 0) < int(now.timestamp()):
                # 期限切れの残骸 → 再帰的にリトライ（次回 PutItem で上書き成功）
                return wrapper(event, context)

            # ボディハッシュ不一致 → 409
            if existing["requestHash"] != request_hash:
                return Response(409, ProblemDetails(
                    type="https://api.yudane.app/errors/idempotency-key-mismatch",
                    title="冪等キー不一致",
                    status=409,
                ))

            # IN_PROGRESS → 別 Lambda 実行中、競合回避のため 409
            if existing.get("status") == "IN_PROGRESS":
                return Response(409, ProblemDetails(
                    type="https://api.yudane.app/errors/idempotency-in-progress",
                    title="同じ冪等キーで処理中",
                    status=409,
                ))

            # COMPLETED → S3 からキャッシュ済みレスポンス取得
            response_body = s3_client.get_object(
                Bucket=IDEMPOTENCY_BUCKET,
                Key=existing["responseBodyKey"],
            )["Body"].read().decode("utf-8")
            return Response(existing["responseStatus"], json.loads(response_body))

    return wrapper
```

**設計ポイント（C1 修正、2026-05-27 セルフレビュー後）**:

1. **Atomic Lock**: `PutItem + ConditionExpression="attribute_not_exists(PK) OR ttl < :now"` で race condition を排除。同時着弾した 2 つのリクエストのうち、1 つだけが `IN_PROGRESS` を取得できる
2. **JSON 正規化**: `requestHash` は `sort_keys=True, separators=(",", ":")` で計算、キー順 / 空白差で false 409 を出さない
3. **S3 経由レスポンス格納**: DynamoDB 400KB アイテム上限と PII リスク回避のため、レスポンスボディは S3（CMEK）に格納し、DDB は S3 key のみ保持
4. **TTL 期限切れガード**: DynamoDB TTL は最大 48h 遅延で削除されるため、読取側で `ttl < now` を明示チェックして残骸を排除
5. **IN_PROGRESS 状態**: 別 Lambda が処理中の場合は 409 で即返却、二重実行を防ぐ
6. **datetime API**: `datetime.now(timezone.utc)` で Python 3.13 deprecated 警告を回避（`datetime.utcnow()` は使わない）

#### 適用エンドポイント（Unit-1 で固定）

- `POST /v1/cart-watch-items`（重複登録防止）
- `POST /v1/debate-sessions`（セッション 1 件保証）
- `POST /v1/amazon-transitions`（重複 EXP 加算防止）

#### 適用しないエンドポイント（Q3 確定との整合）

- `POST /v1/telemetry`: **本テーブル不使用**。Telemetry の重複検知は Q3 確定通り **ElastiCache 1h TTL 単独** で実装する（B-14 TelemetryIngestionService 内で `redis.set(f"telemetry-batch:{batchId}", "1", ex=3600, nx=True)`）。理由は (1) Telemetry は高頻度・低レイテンシが必須で DynamoDB の 5 分 TTL より長い保持が望ましい、(2) ElastiCache 単独で重複検知が完結し責務が明確、(3) DynamoDB IdempotencyKeys との併用は責務曖昧化を招くため明示的に除外

---

## 4. 主要テーブル概要（他 Unit owner、参考）

各 Unit Functional Design で詳細化されるが、Unit-1 で命名と PK/SK の方針を確定する。

### 4.1 Users（Unit-2 owner）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `USER#{userId}`（Cognito sub） |
| `SK` | String | `PROFILE` |
| `emailHash` | String | SHA-256 ハッシュ化（SECURITY-01、m3 修正） |
| `displayName` | String | |
| `level` | Number | 委ね Lv |
| `monthlyLimit` | Number | 月間上限（円） |
| `recoveryCodeHash` | String | TOTP MFA Recovery Code の SHA-256 ハッシュ（B-01 で生成、`/v1/auth/recovery-code` で 1 回限り取得済み） |
| `createdAt`, `updatedAt` | String | ISO 8601 |

GSI: `GSI1 (emailHash → userId)` でログイン時の email→userId 引き当て。

### 4.2 PreferenceVectors（Unit-2 / Unit-4 owner）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `USER#{userId}` |
| `SK` | String | `PREFERENCE#{version}` |
| `vector` | List<Number> | 1024 次元埋め込み（OpenSearch には別途投入） |
| `tags` | StringSet | 嗜好タグ（"book", "audio" 等） |
| `lastUpdatedAt` | String | |

### 4.3 CartWatchItems（Unit-5 owner）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `USER#{userId}` |
| `SK` | String | `CART#{asin}` |
| `productMeta` | Map | 商品メタ（B-11 から取得時にコピー） |
| `attackSchedule` | Map | { 30m, 6h, 24h } の EventBridge Schedule 名 |
| `status` | String | `watching` / `notified-30m` / `notified-6h` / `notified-24h` / `purchased` / `dismissed` |
| `createdAt` | String | |
| `ttl` | Number | 24 時間後（status=watching の場合）|

### 4.4 DebateSessions（Unit-3 owner）

| 属性 | 型 | 説明 |
|---|---|---|
| `PK` | String | `USER#{userId}` |
| `SK` | String | `DEBATE#{sessionId}`（ULID） |
| `productAsin` | String | |
| `trigger` | String | `reel-refuse` / `cart-attack` / `long-view` |
| `outcome` | String | `agreed` / `refused` / `timeout` / `cooldown` |
| `stressLevel` | String | `low` / `mid` / `high`（FR-DEBATE-09） |
| `startedAt`, `endedAt` | String | |
| `tokenCount` | Number | Bedrock 出力トークン数（コスト集計用） |

GSI: `GSI1 (productAsin → sessionId)` で商品別の論破成功率分析。

### 4.5 残テーブル

> **m7 修正（2026-05-27）**: SK が `{timestamp}` だった `AmazonTransitions` / `NotificationLogs` / `ReelImpressions` を `{ulid}` に変更。同一ユーザー高速操作時の SK 衝突 → 後勝ち上書きでテレメトリ損失を防ぐ（Property 2「Telemetry 欠損率 0.1% 以下」と整合）。

| Table | PK / SK | 主な属性 |
|---|---|---|
| DebateMessages | `DEBATE#{sessionId}` / `MSG#{turn}` | role, content, timestamp |
| AmazonTransitions | `USER#{userId}` / `TRANSITION#{ulid}` | productAsin, context, expAwarded, occurredAt |
| Achievements | `USER#{userId}` / `ACHIEVEMENT#{id}` | type, awardedAt |
| SafeguardStates | `USER#{userId}` / `SAFEGUARD#{month}` | spent, limit, cooldownUntil, quietWeekUntil |
| NotificationLogs | `USER#{userId}` / `NOTIFY#{ulid}` | channel, payload, deliveryReceipt, sentAt |
| ReelImpressions | `USER#{userId}` / `IMPRESSION#{ulid}` | productAsin, action（view/skip/tap）, occurredAt |
| WeeklyReports | `USER#{userId}` / `WEEK#{isoWeek}` | metrics（4 指標）, generatedAt |

---

## 5. テーブル設計の原則（Unit-1 で確定）

1. **PK は基本 `USER#{userId}`**（テナント分離 + クエリ局所性）
2. **SK は domain prefix + identifier**（例: `DEBATE#{sessionId}`、`PROFILE`、`PREFERENCE#{version}`）
3. **TTL は UNIX timestamp** で `ttl` 属性に格納、自動削除を活用。ただし DynamoDB TTL は最大 48h 遅延で削除されるため、**読取側で `ttl < now()` を明示チェック**（IdempotencyKeys / DebateRateLimits 等の判定処理側で必須、m4 修正）
4. **GSI は最小限**（per-table 1〜2 個まで、コスト最適化）
5. **Sparse Index は必要時に活用**（属性が存在するレコードのみ GSI に乗せる、Achievements の `awardedAt` 等の楽観的フィールドで採用）
6. **Single Table Design は採用しない**（Q6 = B 確定）
7. **PII は KMS 暗号化 + ハッシュ化**（SECURITY-01）

---

## 6. CDK 実装方針（Unit-1 Platform Stack）

`platform-stack.ts` でテーブルを **個別に Construct 化**し、各 Unit Stack から ARN を SSM Parameter Store 経由で参照する。

```typescript
// infra/lib/platform-stack.ts（Unit-1 で実装）
interface PlatformStackProps extends StackProps {
  envName: 'dev' | 'prd';            // M3 修正: Stack.env (cdk.Environment) との命名衝突回避
  developerInitial?: string;          // 個人 sandbox suffix（C-4 確定）
}

export class PlatformStack extends Stack {
  public readonly debateRateLimitsTable: dynamodb.ITable;
  public readonly idempotencyKeysTable: dynamodb.ITable;
  public readonly idempotencyBucket: s3.IBucket;          // C1 修正: レスポンスボディ格納用 S3
  public readonly kmsKey: kms.IKey;
  public readonly envName: 'dev' | 'prd';
  public readonly isPrd: boolean;

  constructor(scope: Construct, id: string, props: PlatformStackProps) {
    super(scope, id, props);
    this.envName = props.envName;
    this.isPrd = props.envName === 'prd';

    // KMS キー（共通）
    // M6 修正: prd の Multi-Region Key 方針は ap-northeast-1 単独運用のため決勝後の DR 対応時に再評価（backlog 化候補）
    // ハッカソン期間は Single Region のみ
    this.kmsKey = new kms.Key(this, 'YudaneKey', {
      enableKeyRotation: true,
      removalPolicy: this.isPrd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      // multiRegion: false（ap-northeast-1 単独運用、Multi-Region は将来 DR 対応時に backlog で再評価）
    });

    // C1 修正: IdempotencyKeys のレスポンスボディ格納用 S3 バケット（CMEK 暗号化）
    this.idempotencyBucket = new s3.Bucket(this, 'IdempotencyBucket', {
      bucketName: `yudane-${this.envName}-idempotency-bodies`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      lifecycleRules: [{ expiration: Duration.minutes(15) }],  // TTL 5min + バッファ
      removalPolicy: this.isPrd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    // DebateRateLimits（Q5 確定）
    this.debateRateLimitsTable = new dynamodb.Table(this, 'DebateRateLimitsTable', {
      tableName: `yudane-${this.envName}-debate-rate-limits`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.kmsKey,
      timeToLiveAttribute: 'ttl',
      // M1 修正: aws-cdk-lib v2 の最新 API（pointInTimeRecovery は deprecated）
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: this.isPrd,
        recoveryPeriodInDays: this.isPrd ? 35 : undefined,
      },
      deletionProtection: this.isPrd,
      removalPolicy: this.isPrd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    // IdempotencyKeys（Q7 確定、C1 修正で atomic lock パターン）
    this.idempotencyKeysTable = new dynamodb.Table(this, 'IdempotencyKeysTable', {
      tableName: `yudane-${this.envName}-idempotency-keys`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: this.kmsKey,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: this.isPrd,
      },
      deletionProtection: this.isPrd,
      removalPolicy: this.isPrd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    // SSM Parameter Store に ARN を登録（他 Stack から参照）
    new ssm.StringParameter(this, 'DebateRateLimitsTableArn', {
      parameterName: `/yudane/${this.envName}/platform/debate-rate-limits-table-arn`,
      stringValue: this.debateRateLimitsTable.tableArn,
    });
    new ssm.StringParameter(this, 'IdempotencyKeysTableArn', {
      parameterName: `/yudane/${this.envName}/platform/idempotency-keys-table-arn`,
      stringValue: this.idempotencyKeysTable.tableArn,
    });
    new ssm.StringParameter(this, 'IdempotencyBucketName', {
      parameterName: `/yudane/${this.envName}/platform/idempotency-bucket-name`,
      stringValue: this.idempotencyBucket.bucketName,
    });
    // ...
  }
}
```

他のテーブル（Users / CartWatchItems / DebateSessions 等）は **各 Unit の Stack で作成**し、本 Unit-1 ではテーブルファクトリ Construct のみ提供する設計（テーブル数増加時の保守性を優先）。

---

## 7. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: 13 テーブルを Unit owner と紐づけて責任分界、Q5 確定の DebateRateLimits / Q7 確定の IdempotencyKeys を Unit-1 で集中管理 |
| ドキュメント品質 | **強化**: PK/SK 設計、TTL、GSI、KMS の具体的方針が決定済み |
