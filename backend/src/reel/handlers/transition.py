"""POST /v1/amazon-transitions ハンドラ（B-13、RLC-07）。

Authorizer + sub 照合後、リクエストを検証し record_transition を呼ぶ。
Safeguard block は 409、レート制限は API Gateway 側で 429（REEL-API-04/07）。
gate / repo は注入（テストはフェイク、実体は DynamoDB / S-03 で結線）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError, ErrorCategory, to_problem_details
from backend.src.common.logging import AuditLogger
from backend.src.reel.models import AmazonTransitionRequest
from backend.src.reel.transition import SafeguardGate, TransitionRepository, record_transition

_LOGGER = AuditLogger(service="reel-transition")


def make_handler(gate: SafeguardGate, repo: TransitionRepository) -> Any:  # noqa: ANN401
    """依存（gate / repo）を注入してハンドラを生成する（テスト容易性）。"""

    @require_owner
    def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
        try:
            req = _parse_request(event)
            month_bucket = datetime.now(UTC).strftime("%Y-%m")
            award = record_transition(req, gate=gate, repo=repo, month_bucket=month_bucket)
            _LOGGER.metric("reel.transition.awarded", award.awarded, "Count", {})
            return _response(201, award.model_dump())
        except DomainError as err:
            if err.category is ErrorCategory.SAFEGUARD:
                _LOGGER.metric("reel.transition.blocked", 1, "Count", {})
            _LOGGER.log("warn", "reel transition rejected", {"reasonCode": err.code})
            return _problem_response(err)

    return handler


def _parse_request(event: dict[str, Any]) -> AmazonTransitionRequest:
    """リクエストボディを検証し、sub を user_id に束ねる（SECURITY-05/08）。"""
    raw = event.get("body") or "{}"
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    sub = claims.get("sub", "")
    try:
        body = json.loads(raw)
        body["user_id"] = sub  # クライアント値ではなく JWT sub を正とする（SECURITY-08）
        return AmazonTransitionRequest.model_validate(body)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise DomainError(
            ErrorCategory.VALIDATION,
            "validation.invalid-format",
            f"遷移リクエストの検証に失敗: {exc}",
            user_message="リクエスト形式が不正です",
            status=400,
        ) from exc


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _problem_response(err: DomainError) -> dict[str, Any]:
    return {
        "statusCode": err.status,
        "headers": {"Content-Type": "application/problem+json"},
        "body": json.dumps(to_problem_details(err), ensure_ascii=False),
    }
