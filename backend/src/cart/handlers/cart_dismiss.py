"""B-04 CartDismissHandler — DELETE /v1/cart-watch-items/{asin}（US-03-02 AC-4）。

監視解除 + 残追撃ジョブ取消 + ステータス遷移 watching/notified-* → dismissed。
DELETE は冪等のため Idempotency-Key 不要（Unit-1 Q7=B）。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §2.1.1
TDD: クラシック TDD

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.cart.repository import ...`
は CDK packaging 構成では runtime ImportError になる。Member A の Unit-1 packaging 方針確立後に修正。
詳細は doc/backlog.md B-505 参照。
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.src.cart.repository import CartWatchItemsRepo
from backend.src.cart.scheduler import cancel_attacks
from backend.src.common.authz import extract_sub
from backend.src.common.logging import AuditLogger


def _response(status: int, body: Any = None) -> dict[str, Any]:
    if body is None:
        return {"statusCode": status, "headers": {}, "body": ""}
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


def dismiss_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """DELETE /v1/cart-watch-items/{asin} のメインハンドラ。

    Issue W3 修正（2 巡目 2026-05-30）: extract_sub 経由で sub を取得し、
    Authorizer 経路欠損時は 401 で fail-closed（SECURITY-08）。
    """
    audit = AuditLogger(service="cart-dismiss")
    user_id = extract_sub(event)
    if user_id is None:
        return _response(401, _problem("auth.unauthenticated", "認証が必要です", 401))
    asin = event.get("pathParameters", {}).get("asin", "")

    # ASIN 形式検証
    if not re.match(r"^[A-Z0-9]{10}$", asin):
        return _response(400, _problem("validation.invalid-asin-format", "ASIN 形式不正", 400))

    repo = CartWatchItemsRepo()
    item = repo.get(user_id, asin)

    if item is None:
        return _response(
            404, _problem("not-found.cart-watch-item", "監視リストに該当アイテムなし", 404)
        )

    # 既に dismissed / purchased なら 204（冪等返却、Property 1）
    if item.status in ("dismissed", "purchased"):
        return _response(204)

    # 残追撃ジョブをキャンセル（部分失敗許容、ResourceNotFoundException は無視）
    if item.attack_schedule:
        try:
            cancel_attacks(item.attack_schedule)
        except Exception as e:
            # cancel 失敗でも dismissed 遷移は続行（B-06 が dismissed 判定で抑制）
            audit.log("warn", "cancel_attacks partial failure", {"asin": asin, "error": str(e)})

    # ステータス遷移 + TTL 7 日 + GSI1 から外す（Sparse 化）
    success = repo.transition_to_dismissed(user_id, asin)
    if not success:
        # 競合（他経路で既に遷移済）→ 冪等 204
        return _response(204)

    audit.log("info", "Cart watch item dismissed", {"userId": user_id, "asin": asin})
    audit.metric("cart.dismissed", 1, "Count", {"previousStatus": item.status})
    return _response(204)
