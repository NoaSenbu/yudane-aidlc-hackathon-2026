"""B-04 CartIntakeHandler — POST /v1/cart-watch-items（US-03-01）。

Q2=A 二段検証（Mobile 抽出 → Backend 再検証）+ Property 1（重複登録の冪等性）+
Property 6（active 100 件上限）。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §2.1
TDD: クラシック TDD

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.cart.repository import ...` /
`from asin_extractor import extract_asin` は CDK の `lambda.Code.fromAsset('../backend/src/cart')` +
handler `'handlers.cart_intake.lambda_handler'` packaging 構成では runtime ImportError になる。
Member A の Unit-1 packaging 方針確立（doc/backlog.md B-505）後に修正する。
ローカル pytest は backend/conftest.py の sys.path = リポジトリルートで動作するため import は健全。
"""

from __future__ import annotations

import json
import os
import re
import uuid  # W2-1 修正（2 巡目 2026-05-30）: 関数内 import を module-level に移動（PEP 8）
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.src.cart.dummy_catalog import get_dummy_product
from backend.src.cart.repository import (
    AttackSchedule,
    CartWatchItem,
    CartWatchItemsRepo,
    ProductMeta,
)
from backend.src.cart.scheduler import schedule_attacks
from backend.src.common.authz import extract_sub
from backend.src.common.logging import AuditLogger

# 2026-05-29 v3 Issue R8 対応: with_idempotency middleware は Unit-1 整備中
# TODO(unit-1-platform-additions-001): Member A の PR #platform-additions-001 merge 後に有効化
# from backend.src.common.idempotency import with_idempotency

MAX_ACTIVE_WATCH_ITEMS = 100  # Property 6 / SECURITY-15 上限

# AsinExtractor は shared/asin-extractor の Python 実装を呼ぶ（path 依存解決待ちで関数 import）
# v3 注: shared/asin-extractor/python/asin_extractor.py の extract_asin() を呼び出す


class CartIntakeRequest(BaseModel):
    """POST /v1/cart-watch-items のリクエスト body。"""

    url: str = Field(min_length=1)
    asin: str = Field(min_length=10, max_length=10)

    @field_validator("asin")
    @classmethod
    def _asin_format(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9]{10}$", v):
            raise ValueError("ASIN must be 10 uppercase alphanumeric characters")
        return v


class CartIntakeResponse(BaseModel):
    """POST /v1/cart-watch-items のレスポンス body。"""

    item: dict[str, Any]
    isNewlyCreated: bool


def _problem_details(
    error_type: str, title: str, status: int, detail: Optional[str] = None
) -> dict[str, Any]:
    """RFC 7807 Problem Details を生成する。"""
    body: dict[str, Any] = {
        "type": f"https://api.yudane.app/errors/{error_type}",
        "title": title,
        "status": status,
    }
    if detail:
        body["detail"] = detail
    return body


def _response(status: int, body: Any) -> dict[str, Any]:
    """API Gateway proxy response を生成する。"""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _item_to_dict(item: CartWatchItem) -> dict[str, Any]:
    """CartWatchItem を API レスポンス用辞書に変換する（OpenAPI CartWatchItemDto 整合）。"""
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


# @with_idempotency  # TODO(unit-1-platform-additions-001): 有効化
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """POST /v1/cart-watch-items のメインハンドラ。

    フロー:
    1. Cognito sub 取得 + リクエスト検証
    2. ASIN 再検証（Q2=A、SECURITY-05）
    3. 既存登録チェック（status=watching → 既存返却 / dismissed/purchased → 再活性化 / 新規）
    4. Property 6 件数上限チェック
    5. Creators API → 商品メタ取得（B-11、ダミーカタログ fallback）
    6. CartWatchItem 登録 + B-05 schedule_attacks 同期呼出
    7. レスポンス返却（2 秒以内、US-03-01 AC-3）
    """
    audit = AuditLogger(service="cart-intake")
    # Issue W3 修正（2 巡目 2026-05-30）: extract_sub 経由で sub を取得し、
    # Authorizer 経路欠損時は 401 で fail-closed（SECURITY-08）。
    user_id = extract_sub(event)
    if user_id is None:
        return _response(401, _problem_details("auth.unauthenticated", "認証が必要です", 401))

    # リクエスト検証
    try:
        body = CartIntakeRequest.model_validate_json(event.get("body") or "{}")
    except ValidationError as e:
        audit.log("warn", "Invalid intake request", {"userId": user_id, "errors": str(e)})
        return _response(400, _problem_details("validation.invalid-request", "リクエストが不正", 400))

    # Q2=A 反映: Backend 側で再検証（Mobile の抽出を信用しない、SECURITY-05）
    # shared/asin-extractor の Python 実装を import（runtime 解決）
    try:
        from asin_extractor import extract_asin  # type: ignore[import-not-found]
    except ImportError:
        # Python path 解決失敗時のフォールバック（最小バリデーションのみ）
        if not re.match(r"^[A-Z0-9]{10}$", body.asin):
            return _response(400, _problem_details("validation.invalid-asin", "ASIN 不正", 400))
        extracted_asin = body.asin
    else:
        asin_result = extract_asin(body.url)
        if not asin_result.ok or asin_result.asin != body.asin:
            audit.log(
                "warn",
                "ASIN mismatch between mobile and backend",
                {
                    "userId": user_id,
                    "mobileAsin": body.asin,
                    "backendOk": asin_result.ok,
                    "reason": getattr(asin_result, "reason", None) if not asin_result.ok else None,
                },
            )
            return _response(400, _problem_details("asin-mismatch", "ASIN 不一致", 400))
        extracted_asin = asin_result.asin

    repo = CartWatchItemsRepo()

    # 既存登録チェック
    existing = repo.get(user_id, extracted_asin)
    if existing and existing.status == "watching":
        audit.log(
            "info",
            "Duplicate intake, returning existing",
            {"userId": user_id, "asin": extracted_asin},
        )
        return _response(
            200,
            CartIntakeResponse(item=_item_to_dict(existing), isNewlyCreated=False).model_dump(),
        )

    # dismissed / purchased からの再活性化（Issue X 対応、ユーザーの「やっぱり気になる」）
    if existing and existing.status in ("dismissed", "purchased"):
        audit.log(
            "info",
            "Reactivating from terminal status",
            {"userId": user_id, "asin": extracted_asin, "previousStatus": existing.status},
        )
        now = datetime.now(timezone.utc)
        item = repo.reactivate(user_id, extracted_asin, now)
        if item is not None:
            try:
                attack_schedule = schedule_attacks(user_id, item.item_id, extracted_asin, now)
                repo.update_attack_schedule(user_id, extracted_asin, attack_schedule)
            except Exception as e:
                audit.log(
                    "error",
                    "Failed to schedule attacks for reactivation",
                    {"itemId": item.item_id, "error": str(e)},
                )
            audit.metric("cart.intake.reactivated", 1, "Count", {"previousStatus": existing.status})
            return _response(
                200,
                CartIntakeResponse(item=_item_to_dict(item), isNewlyCreated=False).model_dump(),
            )

    # Property 6 件数上限チェック（SECURITY-15）
    active_count = repo.count_active(user_id)
    if active_count >= MAX_ACTIVE_WATCH_ITEMS:
        audit.log(
            "warn",
            "Active items limit exceeded",
            {"userId": user_id, "activeCount": active_count},
        )
        return _response(
            429,
            _problem_details(
                "rate-limit.too-many-cart-watch-items",
                "監視リスト件数の上限を超えました",
                429,
                detail=f"上限 {MAX_ACTIVE_WATCH_ITEMS} 件",
            ),
        )

    # Creators API で商品メタ取得（B-11、ダミーカタログ fallback、§8 A-10）
    use_dummy = os.environ.get("USE_DUMMY_CATALOG", "true").lower() == "true"
    product_meta: Optional[ProductMeta] = None
    if use_dummy:
        product_meta = get_dummy_product(extracted_asin)
    # else: B-11 CreatorsApiClient を呼ぶ（Unit-4 owner、未実装）

    if product_meta is None:
        return _response(
            404,
            _problem_details("not-found.product", "商品が見つからなかった", 404),
        )

    # CartWatchItem 登録 + B-05 schedule_attacks 同期呼出
    now = datetime.now(timezone.utc)
    item_id = str(uuid.uuid4())  # ULID は Unit-1 整備時に切替
    item = repo.create(
        user_id=user_id,
        asin=extracted_asin,
        item_id=item_id,
        product_meta=product_meta,
        status="watching",
        created_at=now,
    )

    try:
        attack_schedule = schedule_attacks(user_id, item.item_id, extracted_asin, now)
        repo.update_attack_schedule(user_id, extracted_asin, attack_schedule)
    except Exception as e:
        # 部分失敗でも CartWatchItem は status=watching で残す（B-05 retry batch で補完）
        audit.log(
            "error",
            "Failed to schedule attacks",
            {"itemId": item.item_id, "error": str(e)},
        )

    audit.metric("cart.intake.created", 1, "Count", {})
    return _response(
        201,
        CartIntakeResponse(item=_item_to_dict(item), isNewlyCreated=True).model_dump(),
    )
