"""B-01 AuthEdgeLambda — Pre Token Generation トリガー（ALG-CLAIM、INIT-04）。

委ね Lv・称号・月間上限を JWT カスタム claim に付与し、UI の即時表示を可能にする。
"""

from __future__ import annotations

from typing import Any

from backend.src.auth.models import AchievementEntity, SafeguardStateEntity


def build_claims(
    achievement: AchievementEntity | None,
    safeguard: SafeguardStateEntity | None,
) -> dict[str, str]:
    """Achievement / SafeguardState からカスタム claim を構築する（INIT-04）。

    Args:
        achievement: 委ね Lv / 称号（None なら既定値）。
        safeguard: 月間上限（None なら 0）。

    Returns:
        Cognito claim 用の文字列辞書。
    """
    level = achievement.level if achievement else 1
    title = achievement.titles[-1] if achievement and achievement.titles else "new"
    monthly_limit = safeguard.monthly_limit_yen if safeguard else 0
    return {
        "yudane_level": str(level),
        "yudane_title": title,
        "yudane_monthly_limit": str(monthly_limit),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """Cognito Pre Token Generation トリガーの Lambda ハンドラ。"""
    from backend.src.auth.repositories.dynamodb import (
        DynamoAchievementRepository,
        DynamoSafeguardStateRepository,
    )

    user_id = event.get("request", {}).get("userAttributes", {}).get("sub", "")
    claims: dict[str, str] = {}
    if user_id:
        achievement = DynamoAchievementRepository().get(user_id)
        safeguard = DynamoSafeguardStateRepository().get(user_id)
        claims = build_claims(achievement, safeguard)

    event.setdefault("response", {})["claimsOverrideDetails"] = {
        "claimsToAddOrOverride": claims,
    }
    return event
