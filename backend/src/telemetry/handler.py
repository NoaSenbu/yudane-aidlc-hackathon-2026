"""B-14 TelemetryIngestionService の Lambda ハンドラ（POST /v1/telemetry）。

JWT sub と user_id の一致を検証し（SECURITY-08）、既知イベントを EMF へ集計、
原イベントを S3 Data Lake へ書き込む（本ファイルでは EMF 集計と結果返却まで）。
"""

from __future__ import annotations

import json
from typing import Any, Final

from pydantic import ValidationError

from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError, ErrorCategory, to_problem_details
from backend.src.common.logging import AuditLogger
from backend.src.common.models import IngestResult, TelemetryEnvelope
from backend.src.telemetry.ingestion import filter_known_events

_LOGGER = AuditLogger(service="platform-telemetry")

# S-04 イベントカタログ（telemetry-contracts と一致）
_KNOWN_EVENTS: Final[frozenset[str]] = frozenset(
    {"screen_view", "app_foreground", "app_background", "deeplink_open"}
)


@require_owner
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """テレメトリバッチを取り込む Lambda ハンドラ。

    Args:
        event: API Gateway proxy event。
        context: Lambda context。

    Returns:
        API Gateway proxy response（202 / 4xx）。
    """
    try:
        envelope = _parse_envelope(event)
        outcome = filter_known_events(envelope, _KNOWN_EVENTS)
        _LOGGER.metric("platform.telemetry.accepted", outcome.accepted, "Count", {})
        _LOGGER.metric("platform.telemetry.dropped", outcome.dropped, "Count", {})
        result = IngestResult(accepted=outcome.accepted, dropped=outcome.dropped)
        return _response(202, result.model_dump())
    except DomainError as err:
        _LOGGER.log("warn", "telemetry ingest rejected", {"reasonCode": err.code})
        return _problem_response(err)


def _parse_envelope(event: dict[str, Any]) -> TelemetryEnvelope:
    """リクエストボディを検証して TelemetryEnvelope にする（SECURITY-05）。"""
    raw = event.get("body") or "{}"
    try:
        return TelemetryEnvelope.model_validate(json.loads(raw))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise DomainError(
            ErrorCategory.VALIDATION,
            "validation.invalid-format",
            f"テレメトリ封筒の検証に失敗: {exc}",
            user_message="リクエスト形式が不正です",
            status=400,
        ) from exc


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _problem_response(err: DomainError) -> dict[str, Any]:
    return {
        "statusCode": err.status,
        "headers": {"Content-Type": "application/problem+json"},
        "body": json.dumps(to_problem_details(err)),
    }
