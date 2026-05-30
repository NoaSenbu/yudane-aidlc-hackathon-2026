"""負債フラグ申告/解除ハンドラ（US-AUTH-03、DEBT-01/04/05）。

require_owner で IDOR 対策。declare_debt / request_debt_release（debt_safeguard）を適用。
実際の解除は B-08 日次バッチの evaluate_debt_release（72h 遅延評価）が行う。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.src.auth.debt_safeguard import declare_debt, request_debt_release
from backend.src.auth.repositories import SafeguardStateRepository
from backend.src.auth.handlers.responses import json_response, problem_response
from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError, ErrorCategory
from backend.src.common.logging import AuditLogger

_LOGGER = AuditLogger(service="auth-safeguard-debt")


def apply_debt_action(
    user_id: str,
    action: str,
    *,
    safeguards: SafeguardStateRepository,
    now: datetime,
) -> str:
    """負債アクション（declare / request-release）を適用する。

    Args:
        user_id: 対象ユーザー。
        action: "declare" | "request-release"。
        safeguards: リポジトリ。
        now: 現在時刻。

    Returns:
        適用後の状態説明。

    Raises:
        DomainError: 状態なし（not-found）/ 不正アクション（validation）。
    """
    state = safeguards.get(user_id)
    if state is None:
        raise DomainError(ErrorCategory.NOT_FOUND, "not-found.resource", "safeguard not found")
    if action == "declare":
        safeguards.put(declare_debt(state))
        return "debt-declared"
    if action == "request-release":
        safeguards.put(request_debt_release(state, now))
        return "release-requested"
    raise DomainError(ErrorCategory.VALIDATION, "validation.invalid-format", "unknown action")


@require_owner
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """負債フラグ申告/解除リクエストのハンドラ。"""
    from backend.src.auth.repositories.dynamodb import DynamoSafeguardStateRepository

    user_id = event.get("pathParameters", {}).get("userId", "")
    try:
        body = json.loads(event.get("body") or "{}")
        result = apply_debt_action(
            user_id,
            body.get("action", ""),
            safeguards=DynamoSafeguardStateRepository(),
            now=datetime.now(UTC),
        )
        _LOGGER.log("info", "debt action applied", {"reasonCode": result})
        return json_response(200, {"result": result})
    except DomainError as err:
        return problem_response(err)
