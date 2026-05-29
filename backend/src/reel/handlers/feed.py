"""GET /v1/reel ハンドラ（B-03、RLC-01）。

Authorizer + sub 照合（require_owner）後、カーソル/limit を検証し build_reel を呼ぶ。
MVP は DummyCatalogAdapter をプロセス内で利用（VPC/Redis/invoke なし）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError, ErrorCategory, to_problem_details
from backend.src.common.logging import AuditLogger
from backend.src.reel.catalog import CachedCatalog, DummyCatalogAdapter
from backend.src.reel.cursor import decode_cursor
from backend.src.reel.feed import LIMIT, build_reel
from backend.src.reel.models import RecommendationContext
from backend.src.reel.ranking import PurchaseHistoryHeuristicSource

_LOGGER = AuditLogger(service="reel-feed")
_MAX_LIMIT = 50


@require_owner
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """リールフィード取得ハンドラ。

    Args:
        event: API Gateway proxy event。
        context: Lambda context。

    Returns:
        API Gateway proxy response（200 / 4xx）。
    """
    try:
        cursor_token, limit = _parse_query(event)
        ctx = _load_context(event)
        source = PurchaseHistoryHeuristicSource(CachedCatalog(DummyCatalogAdapter()))
        page = build_reel(
            ctx,
            source=source,
            cursor=decode_cursor(cursor_token),
            generated_at=datetime.now(UTC).isoformat(),
            limit=limit,
        )
        _LOGGER.metric("reel.feed.cards", len(page.cards), "Count", {})
        return _response(200, page.model_dump())
    except DomainError as err:
        _LOGGER.log("warn", "reel feed rejected", {"reasonCode": err.code})
        return _problem_response(err)


def _parse_query(event: dict[str, Any]) -> tuple[str | None, int]:
    """cursor / limit クエリを検証する（SECURITY-05 / REEL-API-03）。"""
    params = event.get("queryStringParameters") or {}
    cursor = params.get("cursor")
    limit_raw = params.get("limit")
    limit = LIMIT
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError) as exc:
            raise DomainError(
                ErrorCategory.VALIDATION,
                "validation.invalid-format",
                f"limit が不正: {limit_raw!r}",
                user_message="リクエスト形式が不正です",
                status=400,
            ) from exc
        if not 1 <= limit <= _MAX_LIMIT:
            raise DomainError(
                ErrorCategory.VALIDATION,
                "validation.out-of-range",
                f"limit は 1〜{_MAX_LIMIT}",
                user_message="リクエスト形式が不正です",
                status=400,
            )
    return cursor, limit


def _load_context(event: dict[str, Any]) -> RecommendationContext:
    """推薦コンテキストを構築する（MVP: sub のみ。嗜好/履歴は Unit-2 連携で拡張）。"""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub", "anonymous")
    return RecommendationContext(user_id=user_id)


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def _problem_response(err: DomainError) -> dict[str, Any]:
    return {
        "statusCode": err.status,
        "headers": {"Content-Type": "application/problem+json"},
        "body": json.dumps(to_problem_details(err), ensure_ascii=False),
    }
