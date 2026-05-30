"""B-06 NotificationDispatcher — EventBridge Scheduler 起動 → Push 配信（US-03-02）。

EventBridge から `{userId, itemId, asin, step}` を受信し、Safeguard 判定 → テンプレート選択 →
End User Messaging Push の SendMessages 呼出 → NotificationLogs 記録 → status 遷移。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §2.3
TDD: クラシック TDD

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.cart.repository import ...` /
`from safeguard_policy import evaluate_notification` は CDK packaging 構成では runtime ImportError になる。
Member A の Unit-1 packaging 方針確立後に修正。詳細は doc/backlog.md B-505 参照。
"""

from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import boto3

from backend.src.cart.notification_templates import TEMPLATES, render_template
from backend.src.cart.repository import (
    CartWatchItemsRepo,
    NotificationLog,
    NotificationLogsRepo,
)
from backend.src.common.logging import AuditLogger

# evaluate_notification は本 Unit owner で shared/safeguard-policy/python に追加済み（Step 3）
# runtime path 解決
try:
    from safeguard_policy import evaluate_notification  # type: ignore[import-not-found]
except ImportError:
    evaluate_notification = None  # type: ignore[assignment]


def _build_deep_link(asin: str, step: str) -> str:
    """通知タップ時の Deep Link URL を生成する（functional-design.md §1.3 Q7=A）。"""
    return f"yudane://cart-attack/{asin}?step={step}"


def _build_eum_payload(
    asin: str, step: Literal["30m", "6h", "24h"], copy: dict[str, str]
) -> dict[str, Any]:
    """End User Messaging Push の SendMessages 用 payload。"""
    deep_link = _build_deep_link(asin, step)
    return {
        "APNSMessage": {
            "Title": copy["title"],
            "Body": copy["body"],
            "Action": "OPEN_APP",
            "Url": deep_link,
            "Sound": "default",
            "Data": {"productId": asin, "step": step, "type": f"cart-attack-{step}"},
        },
        "GCMMessage": {
            "Title": copy["title"],
            "Body": copy["body"],
            "Action": "OPEN_APP",
            "Url": deep_link,
            "Data": {"productId": asin, "step": step, "type": f"cart-attack-{step}"},
        },
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """EventBridge Scheduler から起動される B-06 メインハンドラ。

    フロー:
    1. event から userId / itemId / asin / step を取得
    2. CartWatchItem の最新 status 確認（dismissed/purchased なら配信せず終了）
    3. Users.pushEndpointId / SafeguardStates 取得
    4. evaluate_notification で配信可否判定（Property 5 通知抑制）
    5. block ならログのみ / allow ならテンプレート選択 → SendMessages → 配信ログ + status 遷移
    """
    audit = AuditLogger(service="cart-notification-dispatcher")
    user_id = event["userId"]
    item_id = event["itemId"]
    asin = event["asin"]
    step: Literal["30m", "6h", "24h"] = event["step"]  # type: ignore[assignment]

    repo = CartWatchItemsRepo()
    logs = NotificationLogsRepo()
    sent_at = datetime.now(timezone.utc).isoformat()
    notification_id = str(uuid.uuid4())

    # 1. CartWatchItem の最新状態取得
    item = repo.get(user_id, asin)
    if item is None:
        audit.log("warn", "Cart watch item not found, skipping notification", {
            "userId": user_id, "asin": asin, "itemId": item_id,
        })
        return {"statusCode": 200, "body": "skipped: not-found"}

    # 2. status が dismissed / purchased なら配信せず終了（Property 5 整合）
    if item.status in ("dismissed", "purchased"):
        audit.log("info", "Skipping notification for resolved item", {
            "asin": asin, "status": item.status,
        })
        return {"statusCode": 200, "body": "skipped: resolved"}

    # 3. Users + SafeguardStates 取得（Unit-2 / Unit-7 owner、本 Unit は consumer）
    users_table_name = os.environ.get("USERS_TABLE", "")
    safeguard_table_name = os.environ.get("SAFEGUARD_STATES_TABLE", "")

    user_data: dict[str, Any] = {}
    safeguard_state: dict[str, Any] = {}

    if users_table_name:
        users_table = boto3.resource("dynamodb").Table(users_table_name)
        user_data = users_table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": "PROFILE"}
        ).get("Item", {}) or {}

    if safeguard_table_name:
        sg_table = boto3.resource("dynamodb").Table(safeguard_table_name)
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        safeguard_state = sg_table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"SAFEGUARD#{month_key}"}
        ).get("Item", {}) or {}

    push_endpoint_id = user_data.get("pushEndpointId")
    display_name = user_data.get("displayName", "")

    # 4. Safeguard 判定（Property 5、Unit-7 連携）
    if evaluate_notification is not None and safeguard_state:
        decision = evaluate_notification(
            user_id=user_id,
            monthly_limit_yen=int(safeguard_state.get("monthly_limit_yen", 70_000)),
            current_budget_used_yen=int(safeguard_state.get("current_budget_used_yen", 0)),
            cooldown_on=bool(safeguard_state.get("cooldown_on", False)),
            quiet_week=bool(safeguard_state.get("quiet_week", False)),
            has_debt=bool(safeguard_state.get("has_debt", False)),
            cooldown_until=safeguard_state.get("cooldown_until"),
        )
        if decision.decision == "block":
            logs.create(
                user_id,
                NotificationLog(
                    notification_id=notification_id,
                    cart_watch_item_id=item_id,
                    channel=f"cart-attack-{step}",
                    status="suppressed_by_safeguard",
                    reason_code=decision.reason_code,
                    sent_at=sent_at,
                ),
            )
            audit.metric(
                "cart.notification.suppressed_by_safeguard",
                1,
                "Count",
                {"step": step, "reason": decision.reason_code},
            )
            return {"statusCode": 200, "body": "suppressed: safeguard"}

    # 5. テンプレート選択 + 配信
    template = random.choice(TEMPLATES[step])
    copy = render_template(
        step=step,
        template=template,
        product_title=item.product_meta.title,
        price_yen=item.product_meta.price_yen,
        user_name=display_name,
    )

    delivery_status = "sent"
    delivery_receipt: dict[str, Any] = {}
    eum_app_id = os.environ.get("EUM_APPLICATION_ID", "")

    if eum_app_id and push_endpoint_id:
        try:
            # AWS Pinpoint EoL 2026-10-30 / End User Messaging 後継（要件書 §7、Issue Z4）
            # boto3 では引き続き 'pinpoint' client name で SendMessages API が提供される。
            # 2026-10 以降は AWS のマイグレーションガイドに従って client name 変更を再評価する。
            pinpoint = boto3.client("pinpoint")
            response = pinpoint.send_messages(
                ApplicationId=eum_app_id,
                MessageRequest={
                    "Addresses": {push_endpoint_id: {"ChannelType": "APNS"}},
                    "MessageConfiguration": _build_eum_payload(asin, step, copy),
                },
            )
            delivery_receipt = response.get("MessageResponse", {}).get("Result", {})
        except Exception as e:
            audit.log("error", "Push delivery failed", {"asin": asin, "error": str(e)})
            delivery_status = "failed"
            delivery_receipt = {"error": str(e)}
    else:
        # eum_app_id / push_endpoint_id 未設定（dev / Unit-2 完成前）→ ログのみ
        # Issue W4 注記（2 巡目 2026-05-30）: delivery_status='skipped' 時は status 遷移を意図的に
        # 走らせない（実配信していないため notified-30m は不正確）。dev 環境では本分岐に入る限り
        # status は watching のままで、6h/24h の Schedule が起動したときも同じく skipped が返り、
        # 統合 E2E は Unit-2 完成（実 EUM_APPLICATION_ID + push_endpoint_id 注入）後に成立する。
        # CloudWatch Metric `cart.notification.dispatched.skipped` で skipped 件数を可視化済み。
        audit.log(
            "info",
            "Skip EUM SendMessages (dev or pre-Unit-2)",
            {
                "hasAppId": bool(eum_app_id),
                "hasEndpoint": bool(push_endpoint_id),
                "stayingStatus": item.status,
                "step": step,
            },
        )
        delivery_status = "skipped"

    # 配信ログ + status 遷移
    logs.create(
        user_id,
        NotificationLog(
            notification_id=notification_id,
            cart_watch_item_id=item_id,
            channel=f"cart-attack-{step}",
            status=delivery_status,
            sent_at=sent_at,
            template_id=template["id"],
            copy=copy,
            delivery_receipt=delivery_receipt,
        ),
    )

    if delivery_status == "sent":
        repo.transition_status(user_id, asin, f"notified-{step}")  # type: ignore[arg-type]

    audit.metric(
        "cart.notification.dispatched",
        1,
        "Count",
        {"step": step, "status": delivery_status},
    )
    return {"statusCode": 200, "body": json.dumps({"status": delivery_status})}
