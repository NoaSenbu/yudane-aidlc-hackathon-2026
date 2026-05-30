# Unit-5 Cart Intercept — Data Model

> Q8 = A（ステータスマシン方式）確定に基づき、Unit-5 owner の DynamoDB テーブル詳細を定義する。Unit-1 [data-model.md §2 共通設定](../../unit-1-platform/functional-design/data-model.md#2-共通設定unit-1-で確定) と §5 設計原則 を継承する。
>
> 参照: [functional-design.md](./functional-design.md) §0 確定事項サマリ / [Unit-1 data-model.md §4.3 / §4.5](../../unit-1-platform/functional-design/data-model.md)

---

## 0. テーブル一覧

| Table | Unit owner | 用途 | Q8 関連 |
|---|---|---|---|
| `CartWatchItems` | Unit-5 Cart Intercept | カート監視リスト + ステータスマシン管理 | **Q8 確定の中核** |
| `NotificationLogs` | Unit-5 Cart Intercept | Push 通知配信ログ（B-06 が記録） | — |

両テーブルとも Unit-1 共通設定（命名規約 / KMS 暗号化 / On-Demand 課金 / TTL / 削除保護）を継承。

---

## 1. CartWatchItems テーブル詳細（Q8 = A 確定）

### 1.1 PK / SK 設計

| 属性 | 型 | 説明 |
|---|---|---|
| `PK`（Partition Key） | String | `USER#{userId}` |
| `SK`（Sort Key） | String | `CART#{asin}` — 同一 user × asin で 1 件保証（重複登録の自然な排除） |
| `GSI1PK` | String | `STATUS#{status}` — Sparse GSI でステータス別クエリ |
| `GSI1SK` | String | `{createdAt}`（ISO 8601）— 同 status 内で時系列順 |

### 1.2 属性定義

| 属性 | 型 | 説明 |
|---|---|---|
| `itemId` | String | ULID（itemId は asin と異なり履歴を一意に識別、NotificationLogs から FK 参照） |
| `asin` | String | Amazon ASIN（10 文字） |
| `productMeta` | Map | `{ title, priceYen, imageUrl, reviewSummary, brand, category }` — B-11 取得時にコピー |
| `status` | String | `watching` / `notified-30m` / `notified-6h` / `notified-24h` / `purchased` / `dismissed` / **`watching_orphaned`**（NFR Design Q4 = A' 追加、attackSchedule 作成失敗が 3 回連続した手動復旧待ち状態）（[ステータスマシン](#13-ステータスマシンq8--a)） |
| `attackSchedule` | Map | `{ schedule_30m: string, schedule_6h: string, schedule_24h: string }` — EventBridge Scheduler 名（キャンセル時に参照） |
| `triggerSource` | String | `share-extension` / `reel-swipe-right` / `clipboard-suggest`（将来）— ストーリー由来分析用 |
| `lastNotifiedAt` | String | ISO 8601 — 最後に通知が配信された時刻（status 遷移と同期） |
| `retry_count` | Number | **NFR Design Q4 = A' 反映**: B-05 リトライバッチ（[sequence-diagrams.md §7](./sequence-diagrams.md#7-b-05-リトライバッチnfr-design-q4--a-追加)）が `attackSchedule` 作成失敗時にインクリメント。`watching` 状態でのみ意味を持ち、3 回連続失敗で `watching_orphaned` に遷移。成功時は 0 にリセット。デフォルト 0、初回 intake 時に明示設定不要（読込側で `item.get("retry_count", 0)` を許容）|
| `createdAt` | String | ISO 8601 — 登録時刻（追撃ジョブの起算点） |
| `updatedAt` | String | ISO 8601 — 最終更新時刻 |
| `ttl` | Number | UNIX timestamp — `dismissed` / `purchased` 後 7 日で自動削除、`watching` 中は 30 日（長期未消化アイテムの掃除） |

### 1.3 ステータスマシン（Q8 = A）

```
                 ┌─────────────┐
                 │   watching  │ ← 初期状態（B-04 CartIntakeHandler 登録時）
                 └──────┬──────┘
                        │
          ┌─────────────┼─────────────┐──── 3 回失敗 ────┐
          │             │             │                  │
       30m 発火       6h 発火        24h 発火        B-05 retry
          │             │             │                  │
          ▼             ▼             ▼                  ▼
   ┌─────────────┐┌─────────────┐┌─────────────┐  ┌──────────────┐
   │notified-30m ││notified-6h  ││notified-24h │  │watching_     │
   └──────┬──────┘└──────┬──────┘└──────┬──────┘  │orphaned      │
          │              │              │          │(NFR Design   │
          └──────────────┼──────────────┘          │ Q4=A' 追加) │
                         │                          └──────┬───────┘
              ┌──────────┴──────────┐                      │
              │                     │              手動復旧 │
        Amazon 遷移成功      「いらない」                   │
              │                     │                      ▼
              ▼                     ▼                ┌──────────┐
       ┌──────────┐           ┌──────────┐           │ watching │
       │purchased │           │dismissed │←─「いらない」（orphaned からも）
       └──────────┘           └──────────┘
       (TTL 7 日後削除)        (TTL 7 日後削除)
```

#### 遷移ルール

| From | To | トリガー | 実行コンポーネント |
|---|---|---|---|
| (none) | watching | Share 受信 + B-04 登録 | B-04 CartIntakeHandler |
| watching | notified-30m | EventBridge 30m 発火 + 配信成功 | B-06 NotificationDispatcher |
| notified-30m | notified-6h | EventBridge 6h 発火 + 配信成功 | B-06 NotificationDispatcher |
| notified-6h | notified-24h | EventBridge 24h 発火 + 配信成功 | B-06 NotificationDispatcher |
| watching / notified-* | purchased | B-13 AmazonTransitionRecorder から `cart-attack` context で transition 記録 | Unit-4 B-13 → Unit-5 リポジトリ |
| watching / notified-* / **watching_orphaned** | dismissed | `DELETE /v1/cart-watch-items/{id}` 受信 → 残追撃ジョブ取消 | B-04 dismiss handler（同 Lambda） |
| dismissed / purchased | watching（**再活性化**） | 同 asin で再度 Share 受信 → ユーザーの「やっぱり気になる」表明 | B-04 CartIntakeHandler `reactivate()` |
| **watching** | **watching_orphaned**（NFR Design Q4 = A' 追加）| B-05 リトライバッチで attackSchedule 作成が 3 回連続失敗 | B-05 cart_attack_scheduler_retry |
| **watching_orphaned** | **watching**（手動復旧）| 運用判断でリトライ再開、CloudWatch Alarm 5 後の手動操作（または再活性化と同じく `reactivate()`）| Member D 手動オペレーション |

#### 不正遷移の防止

- ConditionExpression で「現在の status が想定セットに含まれる場合のみ更新」を強制
- 例: `notified-30m → notified-6h` は `status IN (:watching, :notified-30m)` をチェック

```python
def transition_status(user_id: str, asin: str, to_status: str) -> bool:
    valid_predecessors = {
        "notified-30m": ["watching"],
        "notified-6h": ["watching", "notified-30m"],  # 30m が遅延した場合も考慮
        "notified-24h": ["watching", "notified-30m", "notified-6h"],
        "purchased": ["watching", "notified-30m", "notified-6h", "notified-24h"],
        "dismissed": ["watching", "notified-30m", "notified-6h", "notified-24h", "watching_orphaned"],
        "watching_orphaned": ["watching"],  # NFR Design Q4 = A' 追加: B-05 retry 3 回失敗時のみ
        "watching": ["watching_orphaned", "dismissed", "purchased"],  # 手動復旧 + 再活性化
    }
    valid = valid_predecessors[to_status]
    try:
        table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
            UpdateExpression="SET #s = :to, #u = :now, GSI1PK = :gsi_pk",
            ConditionExpression="#s IN (" + ",".join(f":v{i}" for i in range(len(valid))) + ")",
            ExpressionAttributeNames={"#s": "status", "#u": "updatedAt"},
            ExpressionAttributeValues={
                ":to": to_status,
                ":now": datetime.now(timezone.utc).isoformat(),
                ":gsi_pk": f"STATUS#{to_status}",
                **{f":v{i}": v for i, v in enumerate(valid)},
            },
        )
        return True
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        # 既に他遷移が走った（例: ユーザーが dismissed にした）→ skip
        return False
```

### 1.4 GSI1: status × createdAt

#### 用途

- B-05 のリトライバッチ（ジョブ作成失敗した watching アイテムを発見）
- B-06 のステータス分析（notified-* で長時間滞留しているアイテム検出）
- 監視ダッシュボード（status 別件数の集計）

#### Sparse Index 化

`GSI1PK` / `GSI1SK` は `status` 更新時のみセット。`purchased` / `dismissed` 後は `GSI1PK` を削除して GSI から外す（コスト最適化）。

```python
# transition_status 内で purchased / dismissed への遷移時:
if to_status in ("purchased", "dismissed"):
    # GSI1 から外す（Sparse化）+ TTL 7 日設定
    update_expr += ", #ttl = :ttl REMOVE GSI1PK, GSI1SK"
    expr_values[":ttl"] = int((now + timedelta(days=7)).timestamp())
```

#### 便宜関数

`B-04 dismiss_lambda_handler`（[functional-design.md §2.1.1](./functional-design.md#211-b-04-dismiss-handlerdelete-v1cart-watch-itemsasin)）が呼ぶための薄いラッパー関数を提供:

```python
def transition_to_dismissed(self, user_id: str, asin: str) -> bool:
    """dismissed への遷移（TTL 7 日 + GSI1 Sparse 化を含む）"""
    return self.transition_status(user_id, asin, "dismissed")

def transition_to_purchased(self, user_id: str, asin: str) -> bool:
    """purchased への遷移（B-13 AmazonTransitionRecorder から呼ばれる）"""
    return self.transition_status(user_id, asin, "purchased")

def reactivate(self, user_id: str, asin: str, now: datetime) -> CartWatchItem:
    """5 巡目追加: dismissed / purchased から watching への再活性化（Issue X）

    既存 itemId を維持しつつ:
    - status を watching に戻す
    - createdAt を now に更新（追撃ジョブの起算点をリセット）
    - GSI1PK / GSI1SK を再付与（Sparse Index 復帰）
    - TTL を watching 用の 30 日に再設定
    - attackSchedule は呼び出し側で再度 schedule_attacks() を実行して上書き
    """
    response = self.table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
        UpdateExpression=(
            "SET #s = :watching, createdAt = :now, updatedAt = :now, "
            "GSI1PK = :gsi_pk, GSI1SK = :gsi_sk, #ttl = :ttl"
        ),
        ConditionExpression="#s IN (:dismissed, :purchased)",
        ExpressionAttributeNames={"#s": "status", "#ttl": "ttl"},
        ExpressionAttributeValues={
            ":watching": "watching",
            ":now": now.isoformat(),
            ":gsi_pk": "STATUS#watching",
            ":gsi_sk": now.isoformat(),
            ":ttl": int((now + timedelta(days=30)).timestamp()),
            ":dismissed": "dismissed",
            ":purchased": "purchased",
        },
        ReturnValues="ALL_NEW",
    )
    return CartWatchItem.from_dynamodb(response["Attributes"])

def count_active(self, user_id: str) -> int:
    """7 巡目追加（Issue II）+ NFR Design 2 巡目修正（Issue GGGG）: SECURITY-15 件数上限チェック用

    status が active 群（watching / notified-30m / notified-6h / notified-24h / watching_orphaned）の
    アイテム数をカウント。Property 6（DoS 防御）の前提となる。

    実装方針: GSI1 を使った 4 回 Query は高コストなため、
    PK = USER#{userId} の Query + filter で 1 回完結させる。
    M-05 一覧取得と同じクエリパターンで Cache 効果も期待できる。
    """
    response = self.table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("CART#"),
        FilterExpression=Attr("status").is_in(
            ["watching", "notified-30m", "notified-6h", "notified-24h", "watching_orphaned"]
        ),
        Select="COUNT",  # 件数のみ返却（Item は不要）
    )
    return response["Count"]
```

### 1.5 アクセスパターンと Cost

| パターン | クエリ | コスト |
|---|---|---|
| 単一アイテム取得 | `GetItem(PK=USER#u, SK=CART#asin)` | 0.5 RCU |
| ユーザーの全アイテム | `Query(PK=USER#u)` | 0.5 RCU × アイテム数 |
| 重複登録チェック | `GetItem(PK=USER#u, SK=CART#asin)` | 0.5 RCU |
| watching 中の全アイテム | `Query GSI1(GSI1PK=STATUS#watching)` | 0.5 RCU × 件数 |
| 通知配信時のステータス確認 | `GetItem` + `UpdateItem` ConditionExpression | 1 WCU + 0.5 RCU |

予選想定（10 ユーザー × 平均 5 アイテム / 月）の月額コスト見積もり:

- WCU: 10 × 5 × 4 操作（intake / 30m / 6h / 24h 通知）= 200 ユニット/月 ≒ $0.0003
- RCU: 200 × 0.5 = 100 ユニット/月 ≒ $0.0001
- ストレージ: 50 アイテム × 2KB = 0.1MB ≒ $0.00003
- 合計: 月額 **約 $0.001**（実質無料）

---

## 2. NotificationLogs テーブル詳細

### 2.1 PK / SK 設計

| 属性 | 型 | 説明 |
|---|---|---|
| `PK`（Partition Key） | String | `USER#{userId}` |
| `SK`（Sort Key） | String | `NOTIFY#{ulid}` — Unit-1 §4.5 m7 修正に整合（timestamp 衝突回避） |

### 2.2 属性定義

| 属性 | 型 | 説明 |
|---|---|---|
| `notificationId` | String | ULID（SK の一部） |
| `cartWatchItemId` | String | CartWatchItems の itemId（FK） |
| `channel` | String | `cart-attack-30m` / `cart-attack-6h` / `cart-attack-24h` / `calendar` / `report`（将来 Unit-6/8 でも利用） |
| `copy` | Map | `{ title: string, body: string }`（送信したコピー全文、監査・分析用） |
| `templateId` | String | テンプレート番号（Q3 = A 反映、`30m-3` 等）— 通知効果分析用 |
| `status` | String | `sent` / `failed` / `suppressed_by_safeguard` / `suppressed_by_quiet_week` |
| `deliveryReceipt` | Map | End User Messaging Push のレスポンス（成功/失敗の詳細） |
| `tappedAt` | String? | タップ時刻（M-09 PushNotificationHandler が `POST /v1/notifications/{id}/tap` で記録） |
| `sentAt` | String | ISO 8601 |
| `ttl` | Number | UNIX timestamp — 90 日で自動削除（北極星指標集計後の保持期間） |

### 2.3 アクセスパターン

| パターン | クエリ | 用途 |
|---|---|---|
| ユーザーの通知履歴 | `Query(PK=USER#u, SK begins_with NOTIFY#)` | M-05 CartInterceptScreen の追撃タイムライン表示 |
| 特定 cartWatchItem の通知履歴 | `Query GSI1(cartWatchItemId)` | 配信状況の監査 |
| Tap 率集計（Unit-8） | Scan + filter `tappedAt is not null` | 週次集計（B-08 が実行）|

### 2.4 GSI1: cartWatchItemId × sentAt

```typescript
// CDK 定義（cart-stack.ts §3）
notificationLogsTable.addGlobalSecondaryIndex({
  indexName: 'GSI1-cartWatchItemId',
  partitionKey: { name: 'cartWatchItemId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'sentAt', type: dynamodb.AttributeType.STRING },
  projectionType: dynamodb.ProjectionType.ALL,
});
```

---

## 3. 他テーブルへの影響（Unit-1 / Unit-2 で定義済み）

### 3.1 Users テーブル（Unit-2 owner）への追加属性

Q5 = C 反映により、`Users.PROFILE` に以下属性を追加（Unit-2 Functional Design で正式定義）:

| 属性 | 型 | 説明 |
|---|---|---|
| `pushEndpointId` | String? | AWS End User Messaging Push の Endpoint ID（B-06 が `SendMessages` の Address に指定） |
| `pushPlatform` | String? | `APNS` / `GCM` |
| `pushTokenUpdatedAt` | String? | トークンローテーション検知用 |

→ Unit-2 owner との調整: API 契約 `POST /v1/push-tokens` を Unit-2 の OpenAPI 第 1 版に追加（[api-contracts.md](../../../../.kiro/steering/api-contracts.md) の Member A 一括ドラフト方針 C-3 に整合）。

### 3.2 SafeguardStates テーブル（Unit-7 owner）参照

B-06 NotificationDispatcher が Property 5 担保のため、`SafeguardStates.PK=USER#u, SK=SAFEGUARD#{month}` を読み取る。書き込みは Unit-7 owner のみ。

**2 巡目セルフレビュー後追記（Issue D 関連）+ 2026-05-29 修正（Issue B6 / A4 対応）**: B-06 が `evaluate_notification(...)` を呼び出す際、以下の属性を SafeguardStates から読み取る必要がある:

| 属性 | 型 | 説明 |
|---|---|---|
| `cooldown_on` | Bool | ユーザー手動 ON フラグ |
| `cooldown_until` | String? | 自動冷却の解除時刻（ISO 8601、`evaluate_notification` の `cooldown_until` 引数に渡す） |
| `quiet_week` | Bool | 「静かな週」モード |
| `monthly_limit_yen` | Number | 月間上限（**main 由来 `decide_allow` 実装と整合した命名 / 単位**、business-rules.md SG-04）|
| `current_budget_used_yen` | Number | 当月の消費額合計（円、business-rules.md SG-05）|
| `has_debt` | Bool | 負債保有フラグ（SG-04、実効上限の re-scale 判定）|

これら 6 属性の正式スキーマは Unit-7 Safeguard Functional Design で確定する。本 Unit ではこれらが **取得可能**であることを前提とする。

> **2026-05-29 改訂（Issue B6 / A4 対応）**: 当初は `monthlyUsed` / `monthlyLimit` / `cooldownOn` 等のキャメルケース + `_yen` suffix なしで定義していたが、main 由来の `shared/safeguard-policy/{python/safeguard_policy.py, src/decide-allow.ts}` の正本実装と整合するため snake_case + `_yen` suffix に統一。`has_debt` は当初欠落していた（`decide_allow` の `flags.has_debt` 引数で必須）ため追加。

> **正式合意プロセス**: 上記属性 6 件 + S-03 `evaluate_notification` 関数の追加について、[functional-design.md §8.1 Unit 間契約レビュープロセス](./functional-design.md#81-本-unit-が他-unit-owner-にレビュー依頼する事項) で Member C（Unit-7 owner）にレビュー依頼。期限 2026-05-30 18:00 JST、合意エビデンスは GitHub PR `#safeguard-001` のマージ。Unit-1 §4.5 SafeguardStates 暫定スキーマも本 Unit-5 拡張版に同期するよう Member A に依頼（Issue B6）。

### 3.3 IdempotencyKeys テーブル（Unit-1 owner）使用

`POST /v1/cart-watch-items` / `POST /v1/push-tokens` で `with_idempotency` middleware（Unit-1 §3.2）を経由。テーブル仕様は Unit-1 で確定済み、本 Unit は consumer。

**2026-05-29 追記（Issue A1 対応）**: main 由来の Unit-1 では `IdempotencyKeysTable` / `IdempotencyBucket` および `backend/src/common/idempotency/with_idempotency.py` が**未実装**であることを確認。本 Unit の B-04 / push_token Lambda の Property 1（重複登録の冪等性）を担保するため、**Member A への正式依頼**として [functional-design.md §8.1](./functional-design.md#81-本-unit-が他-unit-owner-にレビュー依頼する事項) に記録（PlatformStack 7 項目追実装の一部）。

### 3.4 CartWatchItems 仕様の Unit-1 §4.3 同期依頼（Issue B5）

main 由来の [Unit-1 data-model.md §4.3 CartWatchItems](../../unit-1-platform/functional-design/data-model.md#43-cartwatchitemsunit-5-owner) 暫定スキーマは、本 Unit が確定した以下と乖離している:

| 項目 | Unit-1 暫定版（main） | Unit-5 確定版（本 §1）| Unit-1 同期方針 |
|---|---|---|---|
| ttl | 24 時間 | watching: 30 日 / dismissed-purchased: 7 日 | Unit-5 確定版に追従 |
| status enum | watching / notified-* / purchased / dismissed | + **`watching_orphaned`**（NFR Design Q4=A' 追加）| Unit-5 確定版に追従 |
| ConditionExpression | 未定義 | §1.3 Stateful 不正遷移防止 | Unit-5 が owner、Unit-1 §4.3 にリンク追加 |
| GSI1 (status × createdAt) | 未定義 | `STATUS#{status}` × `{createdAt}`、Sparse Index | Unit-5 が owner、Unit-1 §4.3 にリンク追加 |

> **正式合意プロセス**: Member A に Unit-1 §4.3 を Unit-5 §1.2 に同期する PR を依頼（[functional-design.md §8.1](./functional-design.md#81-本-unit-が他-unit-owner-にレビュー依頼する事項) `#cart-001` PR にカスケード）。期限 2026-05-29 18:00 JST。本 Unit-5 設計の方が新しい検討結果のため、**Unit-5 を正本としてカスケード**する方向で合意取得。

---

## 4. CDK 実装方針

[functional-design.md §3.1 cart-stack.ts](./functional-design.md#3-infrastructureinfralibcart-stackts) 参照。CartWatchItems / NotificationLogs を Cart Stack 内で作成し、SSM Parameter Store に ARN を登録、他 Stack（Unit-3 Debate / Unit-8 Report）からは SSM 経由で参照する。

---

## 5. 設計原則の遵守確認

Unit-1 §5 設計原則との整合:

| 原則 | 本テーブルの遵守状況 |
|---|---|
| PK は基本 `USER#{userId}` | ✅ 両テーブルとも遵守 |
| SK は domain prefix + identifier | ✅ `CART#{asin}` / `NOTIFY#{ulid}` |
| TTL は UNIX timestamp + 読取側で `ttl < now()` ガード | ✅ status=dismissed/purchased 後 7 日 / NotificationLogs 90 日 |
| GSI は最小限（per-table 1〜2 個） | ✅ 各 1 個（CartWatchItems: GSI1-status / NotificationLogs: GSI1-cartWatchItemId） |
| Sparse Index を必要時に活用 | ✅ CartWatchItems の GSI1 は status=watching/notified-* のみで sparse 化 |
| Single Table Design は採用しない | ✅ Multi Table Design 遵守 |
| PII は KMS 暗号化 + ハッシュ化 | ✅ KMS CMEK、PII（productMeta.title 等）は SECURITY-01 ハッシュ化対象外（公開商品情報） |

---

## 6. ハッカソン書類審査・予選評価軸へのインパクト

| 評価軸 | 本ドキュメントの貢献 |
|---|---|
| Unit 分解の適切さ | **強化**: Unit-5 owner の 2 テーブルが Unit-1 / Unit-2 / Unit-7 のテーブル群と責任分界、ステータスマシンが Unit 間の状態遷移を明示 |
| ドキュメント品質 | **強化**: ステータスマシン図 + 遷移ルール表 + 不正遷移防止 ConditionExpression + Sparse Index コスト最適化 + アクセスパターンコスト試算が一貫展開 |
