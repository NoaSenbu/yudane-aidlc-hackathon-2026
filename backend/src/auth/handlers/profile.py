"""profile ハンドラ — POST/PATCH /v1/users/{userId}/profile（US-AUTH-01）。

require_owner（Unit-1）で IDOR 対策。オンボ段階保存（apply_profile_patch）を適用し、
完了時に SafeguardState の月間上限を確定する。
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from backend.src.auth.models import UserEntity
from backend.src.auth.onboarding import (
    ProfilePatch,
    apply_profile_patch,
    compute_monthly_limit_yen,
)
from backend.src.auth.repositories import SafeguardStateRepository, UserRepository
from backend.src.auth.handlers.responses import json_response, problem_response
from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError, ErrorCategory
from backend.src.common.logging import AuditLogger

_LOGGER = AuditLogger(service="auth-profile")


def apply_profile_update(
    user_id: str,
    patch: ProfilePatch,
    *,
    users: UserRepository,
    safeguards: SafeguardStateRepository,
) -> UserEntity:
    """プロファイル段階更新を適用し、完了時に月間上限を確定する（ONB-02/06）。

    Args:
        user_id: 対象ユーザー。
        patch: 1 画面分の部分入力。
        users / safeguards: リポジトリ。

    Returns:
        更新後 User。

    Raises:
        DomainError: ユーザーが存在しない（not-found）。
    """
    user = users.get(user_id)
    if user is None:
        raise DomainError(
            ErrorCategory.NOT_FOUND,
            "not-found.resource",
            f"user not found: {user_id}",
            status=404,
        )
    updated = apply_profile_patch(user, patch)
    users.put(updated)

    # 完了 + 月間上限確定（ONB-06）
    if updated.profile_completed and updated.monthly_disposable_yen is not None:
        state = safeguards.get(user_id)
        if state is not None:
            state.monthly_limit_yen = compute_monthly_limit_yen(updated.monthly_disposable_yen)
            if updated.has_debt:
                state.flags.has_debt = True
                state.flags.cooldown_on = True
            safeguards.put(state)
    return updated


def _parse_patch(event: dict[str, Any]) -> ProfilePatch:
    """リクエストボディを ProfilePatch に検証変換する（SECURITY-05）。"""
    raw = event.get("body") or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DomainError(
            ErrorCategory.VALIDATION,
            "validation.invalid-format",
            "JSON parse error",
            status=400,
        ) from exc
    try:
        return ProfilePatch(
            monthly_disposable_yen=data.get("monthlyDisposableYen"),
            monthly_savings_yen=data.get("monthlySavingsYen"),
            favorite_brands=data.get("favoriteBrands"),
            ng_categories=data.get("ngCategories"),
            has_debt=data.get("hasDebt"),
            associates_disclosure_acknowledged=data.get("associatesDisclosureAcknowledged"),
            step=int(data.get("onboardingStep", 0)),
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise DomainError(
            ErrorCategory.VALIDATION,
            "validation.invalid-format",
            "profile payload invalid",
            status=400,
        ) from exc


@require_owner
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """profile ハンドラ（POST/PATCH 共通、段階保存）。"""
    from backend.src.auth.repositories.dynamodb import (
        DynamoSafeguardStateRepository,
        DynamoUserRepository,
    )

    user_id = event.get("pathParameters", {}).get("userId", "")
    try:
        patch = _parse_patch(event)
        updated = apply_profile_update(
            user_id,
            patch,
            users=DynamoUserRepository(),
            safeguards=DynamoSafeguardStateRepository(),
        )
        method = event.get("httpMethod", "PATCH").upper()
        status = 201 if method == "POST" else 200
        return json_response(status, {"userId": updated.id, "onboardingStep": updated.onboarding_step,
                                      "profileCompleted": updated.profile_completed})
    except DomainError as err:
        _LOGGER.log("warn", "profile update rejected", {"reasonCode": err.code})
        return problem_response(err)
