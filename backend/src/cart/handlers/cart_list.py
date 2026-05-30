"""B-04 CartListHandler — GET /v1/cart-watch-items / GET /v1/cart-watch-items/{asin}。

一覧取得（status filter + cursor pagination）/ 単一取得（path param）。
NFR Design Q2=A' staleTime 階層化で M-05 一覧は staleTime=60s / 詳細は 0s。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.1

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.cart.repository import ...`
は CDK packaging 構成では runtime ImportError になる。Member A の Unit-1 packaging 方針確立後に修正。
詳細は doc/backlog.md B-505 参照。
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

from backend.src.cart.repository import ACTIVE_STATUSES, CartWatchItem, CartWatchItemsRepo
from backend.src.common.authz import extract_sub
from backend.src.common.logging import AuditLogger

# Issue W1 修正（2 巡目 2026-05-30）: Z5 で public 化した repository.ACTIVE_STATUSES を直接利用。
# ローカル _ACTIVE_STATUSES の重複定義を撤去し、watching_orphaned 含む差分の二重メンテリスクを解消。
_ALL_STATUSES = list(ACTIVE_STATUSES) + ["purchased", "dismissed"]


def _response(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _problem(error_type: str, title: str, status: int) -> dict[str, Any]:
    return {
        "type": f"https://api.yudane.app/errors/{error_type}",
        "title": title,
        "status": status,
    }


def _item_to_dict(item: CartWatchItem) -> dict[str, Any]:
    """CartWatchItem を API レスポンス用辞書に変換する（cart_intake._item_to_dict と同一仕様）。"""
    return {
        "itemId": item.item_id,
        "asin": item.asin,
        "status": item.status,
        "productMeta": {
            "title": item.product_meta.title,
            "priceYen": item.product_meta.price_yen,
            "imageUrl": item.product_meta.image_url,
            "reviewSummary": item.product_meta.review_summary,
            "brand": item.product_meta.brand,
            "category": item.product_meta.category,
        },
        "attackSchedule": (
            {
                "schedule_30m": item.attack_schedule.schedule_30m,
                "schedule_6h": item.attack_schedule.schedule_6h,
                "schedule_24h": item.attack_schedule.schedule_24h,
            }
            if item.attack_schedule
            else None
        ),
        "triggerSource": item.trigger_source,
        "retry_count": item.retry_count,
        "lastNotifiedAt": item.last_notified_at,
        "createdAt": item.created_at,
        "updatedAt": item.updated_at,
    }


def _encode_cursor(last_key: dict[str, Any]) -> str:
    """DDB の LastEvaluatedKey を base64 cursor に変換する（不透明トークン）。"""
    return base64.urlsafe_b64encode(json.dumps(last_key).encode()).decode()


def _decode_cursor(cursor: str) -> dict[str, Any]:
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


def list_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """GET /v1/cart-watch-items または /v1/cart-watch-items/{asin}。

    Issue W3 修正（2 巡目 2026-05-30）: extract_sub 経由で sub を取得し、
    Authorizer 経路欠損時は 401 で fail-closed（SECURITY-08 / fail-closed 原則）。
    本エンドポイントは path に userId を含めないため @require_owner デコレータは不要だが、
    sub 抽出ロジックは require_owner と共通化する。
    """
    audit = AuditLogger(service="cart-list")
    user_id = extract_sub(event)
    if user_id is None:
        return _response(401, _problem("auth.unauthenticated", "認証が必要です", 401))
    path_params = event.get("pathParameters") or {}
    asin = path_params.get("asin")

    repo = CartWatchItemsRepo()

    # 単一取得（path param あり）
    if asin:
        if not re.match(r"^[A-Z0-9]{10}$", asin):
            return _response(400, _problem("validation.invalid-asin-format", "ASIN 形式不正", 400))
        item = repo.get(user_id, asin)
        if item is None:
            return _response(
                404, _problem("not-found.cart-watch-item", "監視アイテムなし", 404)
            )
        return _response(200, _item_to_dict(item))

    # 一覧取得
    query_params = event.get("queryStringParameters") or {}
    status_filter = query_params.get("status", "active")
    limit = min(int(query_params.get("limit", 10)), 50)
    cursor_str: Optional[str] = query_params.get("cursor")

    # status filter の解決
    if status_filter == "active":
        target_statuses = list(ACTIVE_STATUSES)
    elif status_filter in _ALL_STATUSES:
        target_statuses = [status_filter]
    else:
        return _response(400, _problem("validation.invalid-status", "status filter 不正", 400))

    # PK = USER#{userId} の Query + status FilterExpression
    table = repo._table  # type: ignore[attr-defined]
    query_kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("CART#"),
        "FilterExpression": Attr("status").is_in(target_statuses),
        "Limit": limit,
    }
    if cursor_str:
        try:
            query_kwargs["ExclusiveStartKey"] = _decode_cursor(cursor_str)
        except Exception:
            return _response(400, _problem("validation.invalid-cursor", "cursor 不正", 400))

    response = table.query(**query_kwargs)
    items = [CartWatchItem.from_dynamodb(i) for i in response.get("Items", [])]
    last_key = response.get("LastEvaluatedKey")

    body: dict[str, Any] = {"items": [_item_to_dict(i) for i in items]}
    if last_key:
        body["nextCursor"] = _encode_cursor(last_key)

    audit.metric("cart.list.served", 1, "Count", {"status": status_filter})
    return _response(200, body)
