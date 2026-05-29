"""Unit-5 Cart Intercept — Repository 層。

CartWatchItems / NotificationLogs テーブルへのアクセス。
ステータスマシン（Q8=A）の ConditionExpression による不正遷移防止が中核。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/data-model.md §1〜§5
TDD: クラシック TDD（Red → Green → Refactor → PBT 補強）
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

CartStatus = Literal[
    "watching",
    "notified-30m",
    "notified-6h",
    "notified-24h",
    "purchased",
    "dismissed",
    "watching_orphaned",
]

# ステータス遷移ルール（data-model.md §1.3）
VALID_PREDECESSORS: dict[CartStatus, list[CartStatus]] = {
    "notified-30m": ["watching"],
    "notified-6h": ["watching", "notified-30m"],
    "notified-24h": ["watching", "notified-30m", "notified-6h"],
    "purchased": ["watching", "notified-30m", "notified-6h", "notified-24h"],
    "dismissed": [
        "watching",
        "notified-30m",
        "notified-6h",
        "notified-24h",
        "watching_orphaned",
    ],
    "watching_orphaned": ["watching"],
    "watching": ["watching_orphaned", "dismissed", "purchased"],  # 手動復旧 + 再活性化
}

# 後方互換のための alias（既存テストが触っていたら残す）
_VALID_PREDECESSORS = VALID_PREDECESSORS

# active 状態（Property 6 件数上限カウント対象）
ACTIVE_STATUSES: list[CartStatus] = [
    "watching",
    "notified-30m",
    "notified-6h",
    "notified-24h",
    "watching_orphaned",
]
_ACTIVE_STATUSES = ACTIVE_STATUSES  # 後方互換 alias


@dataclass(frozen=True)
class ProductMeta:
    """商品メタ情報（Creators API から取得）。"""

    title: str
    price_yen: int
    image_url: Optional[str] = None
    review_summary: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None


@dataclass(frozen=True)
class AttackSchedule:
    """3 段追撃ジョブの EventBridge Scheduler 名。"""

    schedule_30m: str
    schedule_6h: str
    schedule_24h: str


@dataclass(frozen=True)
class CartWatchItem:
    """CartWatchItems テーブルの 1 行（DTO）。

    user_id は PK = USER#{userId} から復元（Issue Z2 修正、retry batch で必要）。
    """

    item_id: str
    user_id: str
    asin: str
    status: CartStatus
    product_meta: ProductMeta
    created_at: str
    updated_at: str
    trigger_source: str = "share-extension"
    attack_schedule: Optional[AttackSchedule] = None
    last_notified_at: Optional[str] = None
    retry_count: int = 0

    @classmethod
    def from_dynamodb(cls, item: dict[str, Any]) -> "CartWatchItem":
        meta_raw = item.get("productMeta", {}) or {}
        sched_raw = item.get("attackSchedule")
        # PK = USER#{userId} から user_id を復元（Issue Z2 修正）
        pk = item.get("PK", "")
        user_id = pk.removeprefix("USER#") if pk.startswith("USER#") else ""
        return cls(
            item_id=item["itemId"],
            user_id=user_id,
            asin=item["asin"],
            status=item["status"],
            product_meta=ProductMeta(
                title=meta_raw.get("title", ""),
                price_yen=int(meta_raw.get("priceYen", 0)),
                image_url=meta_raw.get("imageUrl"),
                review_summary=meta_raw.get("reviewSummary"),
                brand=meta_raw.get("brand"),
                category=meta_raw.get("category"),
            ),
            created_at=item["createdAt"],
            updated_at=item["updatedAt"],
            trigger_source=item.get("triggerSource", "share-extension"),
            attack_schedule=(
                AttackSchedule(
                    schedule_30m=sched_raw["schedule_30m"],
                    schedule_6h=sched_raw["schedule_6h"],
                    schedule_24h=sched_raw["schedule_24h"],
                )
                if sched_raw
                else None
            ),
            last_notified_at=item.get("lastNotifiedAt"),
            retry_count=int(item.get("retry_count", 0)),
        )


@dataclass(frozen=True)
class NotificationLog:
    """NotificationLogs テーブルの 1 行。"""

    notification_id: str
    cart_watch_item_id: str
    channel: str
    status: str  # 'sent' | 'failed' | 'suppressed_by_safeguard' | 'suppressed_by_quiet_week'
    sent_at: str
    template_id: Optional[str] = None
    copy: dict[str, Any] = field(default_factory=dict)
    delivery_receipt: dict[str, Any] = field(default_factory=dict)
    reason_code: Optional[str] = None
    tapped_at: Optional[str] = None


def _table(table_name_env: str) -> Any:
    """DynamoDB Table リソースを環境変数から解決する。"""
    table_name = os.environ[table_name_env]
    return boto3.resource("dynamodb").Table(table_name)


class CartWatchItemsRepo:
    """CartWatchItems テーブルのアクセサ。

    ステータスマシン（data-model.md §1.3）の ConditionExpression による不正遷移防止が中核。
    GSI1 Sparse Index 化（dismissed/purchased で REMOVE GSI1PK）。
    """

    def __init__(self, table: Optional[Any] = None) -> None:
        self._table = table if table is not None else _table("CART_WATCH_ITEMS_TABLE")

    def get(self, user_id: str, asin: str) -> Optional[CartWatchItem]:
        """単一アイテム取得（PK=USER#u, SK=CART#asin、1 RCU の効率的アクセス）。"""
        response = self._table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
        )
        item = response.get("Item")
        return CartWatchItem.from_dynamodb(item) if item else None

    def create(
        self,
        user_id: str,
        asin: str,
        item_id: str,
        product_meta: ProductMeta,
        status: CartStatus,
        created_at: datetime,
        trigger_source: str = "share-extension",
    ) -> CartWatchItem:
        """新規 CartWatchItem を登録する（status=watching で開始、GSI1 を Sparse セット）。"""
        created_iso = created_at.isoformat()
        ttl_watching_days = 30  # data-model.md §1.2 watching 中は 30 日
        item: dict[str, Any] = {
            "PK": f"USER#{user_id}",
            "SK": f"CART#{asin}",
            "itemId": item_id,
            "asin": asin,
            "status": status,
            "productMeta": {
                "title": product_meta.title,
                "priceYen": product_meta.price_yen,
                "imageUrl": product_meta.image_url,
                "reviewSummary": product_meta.review_summary,
                "brand": product_meta.brand,
                "category": product_meta.category,
            },
            "triggerSource": trigger_source,
            "createdAt": created_iso,
            "updatedAt": created_iso,
            "GSI1PK": f"STATUS#{status}",
            "GSI1SK": created_iso,
            "retry_count": 0,
            "ttl": int((created_at + timedelta(days=ttl_watching_days)).timestamp()),
        }
        self._table.put_item(
            Item=item,
            # 同 user × asin 既存時は ConditionalCheckFailed（呼出側で reactivate に分岐）
            ConditionExpression=Attr("PK").not_exists() & Attr("SK").not_exists(),
        )
        return CartWatchItem.from_dynamodb(item)

    def transition_status(
        self,
        user_id: str,
        asin: str,
        to_status: CartStatus,
        now: Optional[datetime] = None,
    ) -> bool:
        """ステータス遷移（不正遷移は ConditionExpression で reject、True/False で結果返却）。

        purchased / dismissed では GSI1PK を REMOVE して Sparse 化（data-model.md §1.4）。
        """
        valid = VALID_PREDECESSORS[to_status]
        current = now if now is not None else datetime.now(timezone.utc)
        current_iso = current.isoformat()

        # 基本 UpdateExpression
        update_parts: list[str] = ["#s = :to", "#u = :now"]
        remove_parts: list[str] = []
        expr_names: dict[str, str] = {"#s": "status", "#u": "updatedAt"}
        expr_values: dict[str, Any] = {":to": to_status, ":now": current_iso}

        if to_status in ("purchased", "dismissed"):
            # GSI1 から外す + TTL 7 日
            remove_parts.extend(["GSI1PK", "GSI1SK"])
            expr_names["#ttl"] = "ttl"
            update_parts.append("#ttl = :ttl")
            expr_values[":ttl"] = int((current + timedelta(days=7)).timestamp())
        else:
            # active 状態への遷移は GSI1PK を更新
            update_parts.append("GSI1PK = :gsi_pk")
            expr_values[":gsi_pk"] = f"STATUS#{to_status}"

        # ConditionExpression: 現在の status が valid_predecessors 内
        for i, v in enumerate(valid):
            expr_values[f":v{i}"] = v
        condition = "#s IN (" + ", ".join(f":v{i}" for i in range(len(valid))) + ")"

        update_expr = "SET " + ", ".join(update_parts)
        if remove_parts:
            update_expr += " REMOVE " + ", ".join(remove_parts)

        try:
            self._table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
                UpdateExpression=update_expr,
                ConditionExpression=condition,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def transition_to_dismissed(self, user_id: str, asin: str) -> bool:
        """dismissed への遷移（B-04 dismiss handler から呼出）。"""
        return self.transition_status(user_id, asin, "dismissed")

    def transition_to_purchased(self, user_id: str, asin: str) -> bool:
        """purchased への遷移（Unit-4 B-13 AmazonTransitionRecorder から呼出）。"""
        return self.transition_status(user_id, asin, "purchased")

    def reactivate(
        self,
        user_id: str,
        asin: str,
        now: Optional[datetime] = None,
    ) -> Optional[CartWatchItem]:
        """dismissed / purchased から watching への再活性化。

        既存 itemId を維持しつつ status を watching に戻し、createdAt を更新、
        GSI1 を再付与、TTL を 30 日に再設定する。attackSchedule は呼出側で再生成。
        """
        current = now if now is not None else datetime.now(timezone.utc)
        current_iso = current.isoformat()
        try:
            response = self._table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
                UpdateExpression=(
                    "SET #s = :watching, createdAt = :now, updatedAt = :now, "
                    "GSI1PK = :gsi_pk, GSI1SK = :now, #ttl = :ttl, retry_count = :zero"
                ),
                ConditionExpression="#s IN (:dismissed, :purchased)",
                ExpressionAttributeNames={"#s": "status", "#ttl": "ttl"},
                ExpressionAttributeValues={
                    ":watching": "watching",
                    ":now": current_iso,
                    ":gsi_pk": "STATUS#watching",
                    ":ttl": int((current + timedelta(days=30)).timestamp()),
                    ":dismissed": "dismissed",
                    ":purchased": "purchased",
                    ":zero": 0,
                },
                ReturnValues="ALL_NEW",
            )
            return CartWatchItem.from_dynamodb(response["Attributes"])
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise

    def update_attack_schedule(
        self,
        user_id: str,
        asin: str,
        attack_schedule: AttackSchedule,
    ) -> None:
        """attackSchedule 属性を更新（schedule_attacks 成功後）。"""
        self._table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
            UpdateExpression="SET attackSchedule = :sched, retry_count = :zero",
            ExpressionAttributeValues={
                ":sched": {
                    "schedule_30m": attack_schedule.schedule_30m,
                    "schedule_6h": attack_schedule.schedule_6h,
                    "schedule_24h": attack_schedule.schedule_24h,
                },
                ":zero": 0,
            },
        )

    def increment_retry_count(self, user_id: str, asin: str) -> int:
        """retry_count をインクリメント（B-05 retry batch 失敗時）。"""
        response = self._table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": f"CART#{asin}"},
            UpdateExpression="ADD retry_count :one",
            ExpressionAttributeValues={":one": 1},
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["retry_count"])

    def count_active(self, user_id: str) -> int:
        """active 状態のアイテム数を返す（Property 6 / SECURITY-15 件数上限チェック用）。

        PK = USER#{userId} の Query + filter で 1 回完結（4 回 GSI1 Query は高コスト）。
        """
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{user_id}")
            & Key("SK").begins_with("CART#"),
            FilterExpression=Attr("status").is_in(ACTIVE_STATUSES),
            Select="COUNT",
        )
        return int(response.get("Count", 0))

    def query_orphan_candidates(self, limit: int = 100) -> list[CartWatchItem]:
        """B-05 retry batch 用: status=watching かつ attackSchedule が不完全なアイテムを retry_count 昇順で抽出。"""
        response = self._table.query(
            IndexName="GSI1-status-createdAt",
            KeyConditionExpression=Key("GSI1PK").eq("STATUS#watching"),
            FilterExpression=Attr("attackSchedule").not_exists()
            | Attr("attackSchedule.schedule_30m").not_exists(),
            Limit=limit,
        )
        items = [CartWatchItem.from_dynamodb(i) for i in response.get("Items", [])]
        # retry_count 昇順（同一アイテムの繰り返し処理回避）
        return sorted(items, key=lambda x: x.retry_count)


class NotificationLogsRepo:
    """NotificationLogs テーブルのアクセサ（B-06 が記録）。"""

    def __init__(self, table: Optional[Any] = None) -> None:
        self._table = table if table is not None else _table("NOTIFICATION_LOGS_TABLE")

    def create(self, user_id: str, log: NotificationLog) -> None:
        """通知配信ログを記録する（90 日 TTL）。"""
        sent_at_dt = datetime.fromisoformat(log.sent_at)
        ttl = int((sent_at_dt + timedelta(days=90)).timestamp())
        item = {
            "PK": f"USER#{user_id}",
            "SK": f"NOTIFY#{log.notification_id}",
            "notificationId": log.notification_id,
            "cartWatchItemId": log.cart_watch_item_id,
            "channel": log.channel,
            "status": log.status,
            "sentAt": log.sent_at,
            "templateId": log.template_id,
            "copy": log.copy,
            "deliveryReceipt": log.delivery_receipt,
            "ttl": ttl,
        }
        if log.reason_code:
            item["reasonCode"] = log.reason_code
        if log.tapped_at:
            item["tappedAt"] = log.tapped_at
        self._table.put_item(Item=item)
