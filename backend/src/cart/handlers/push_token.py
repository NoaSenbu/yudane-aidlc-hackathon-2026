"""B-04 PushTokenHandler — POST /v1/push-tokens（Q5=C End User Messaging Endpoint 管理）。

APNs / FCM トークンを End User Messaging Push の Endpoint として登録または更新。
Idempotency-Key は token 値の UUID v5 で生成（Mobile 側、同一トークン再送 = 副作用 1 回）。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §1.3 / Q5=C
TDD: クラシック TDD

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.common.logging import AuditLogger`
は CDK packaging 構成では runtime ImportError になる。Member A の Unit-1 packaging 方針確立後に修正。
詳細は doc/backlog.md B-505 参照。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import boto3
from pydantic import BaseModel, Field, ValidationError

from backend.src.common.authz import extract_sub
from backend.src.common.logging import AuditLogger

# 2026-05-29 v3 Issue R8 対応: with_idempotency middleware は Unit-1 整備中
# TODO(unit-1-platform-additions-001): Member A の PR #platform-additions-001 merge 後に有効化
# from backend.src.common.idempotency import with_idempotency


class PushTokenRequest(BaseModel):
    """POST /v1/push-tokens のリクエスト body。"""

    token: str = Field(min_length=1, max_length=512)
    platform: Literal["APNS", "GCM"]


class PushTokenResponse(BaseModel):
    endpointId: str


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


# @with_idempotency  # TODO(unit-1-platform-additions-001): 有効化
def register_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """POST /v1/push-tokens のメインハンドラ。

    フロー:
    1. Cognito sub 取得 + リクエスト検証
    2. Users.pushEndpointId 既存確認（Unit-2 owner Users テーブル）
    3. End User Messaging Push の UpdateEndpoint 呼出（新規 or 既存トークン更新）
    4. Users.pushEndpointId / pushPlatform / pushTokenUpdatedAt 更新
    5. レスポンス返却
    """
    audit = AuditLogger(service="cart-push-token")
    # Issue W3 修正（2 巡目 2026-05-30）: extract_sub 経由で sub を取得し、
    # Authorizer 経路欠損時は 401 で fail-closed（SECURITY-08）。
    user_id = extract_sub(event)
    if user_id is None:
        return _response(401, _problem("auth.unauthenticated", "認証が必要です", 401))

    try:
        body = PushTokenRequest.model_validate_json(event.get("body") or "{}")
    except ValidationError as e:
        audit.log("warn", "Invalid push token request", {"userId": user_id, "errors": str(e)})
        return _response(400, _problem("validation.invalid-request", "リクエストが不正", 400))

    users_table_name = os.environ.get("USERS_TABLE", "")
    if not users_table_name:
        audit.log("error", "USERS_TABLE not configured", {})
        return _response(500, _problem("internal.misconfigured", "サーバー設定エラー", 500))

    users_table = boto3.resource("dynamodb").Table(users_table_name)

    # 既存 endpointId 確認（Unit-2 owner Users テーブル、本 Unit は consumer）
    existing_user = users_table.get_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
    ).get("Item")
    existing_endpoint_id: Optional[str] = (
        existing_user.get("pushEndpointId") if existing_user else None
    )

    # End User Messaging Push の UpdateEndpoint 呼出
    eum_app_id = os.environ.get("EUM_APPLICATION_ID", "")
    if not eum_app_id:
        audit.log("warn", "EUM_APPLICATION_ID not configured (dev/sandbox?)", {})

    endpoint_id = existing_endpoint_id or str(uuid.uuid4())
    is_newly_created = existing_endpoint_id is None

    if eum_app_id:
        try:
            # AWS Pinpoint EoL 2026-10-30 / End User Messaging 後継（要件書 §7、Issue Z4）
            # boto3 では引き続き 'pinpoint' client name で UpdateEndpoint API が提供される。
            # 2026-10 以降は AWS のマイグレーションガイドに従って client name 変更を再評価する。
            pinpoint = boto3.client("pinpoint")
            pinpoint.update_endpoint(
                ApplicationId=eum_app_id,
                EndpointId=endpoint_id,
                EndpointRequest={
                    "Address": body.token,
                    "ChannelType": body.platform,
                    "OptOut": "NONE",
                    "User": {"UserId": user_id},
                },
            )
        except Exception as e:
            audit.log("error", "EUM UpdateEndpoint failed", {"userId": user_id, "error": str(e)})
            return _response(
                503, _problem("external-api.eum-update-endpoint-failed", "Push 登録失敗", 503)
            )

    # Users テーブル更新（pushEndpointId / pushPlatform / pushTokenUpdatedAt）
    now_iso = datetime.now(timezone.utc).isoformat()
    users_table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        UpdateExpression=(
            "SET pushEndpointId = :eid, "
            "pushPlatform = :plat, "
            "pushTokenUpdatedAt = :now"
        ),
        ExpressionAttributeValues={
            ":eid": endpoint_id,
            ":plat": body.platform,
            ":now": now_iso,
        },
    )

    audit.metric("cart.push_token.registered", 1, "Count", {"platform": body.platform})
    return _response(
        201 if is_newly_created else 200,
        PushTokenResponse(endpointId=endpoint_id).model_dump(),
    )
