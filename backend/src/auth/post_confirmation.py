"""B-01 AuthEdgeLambda — Post Confirmation トリガー（ALG-INIT、INIT-01〜03）。

新規ユーザーの User / SafeguardState / Achievement を冪等に初期化する。
PreferenceVector は Unit-1 が空で持つが、本 Unit では User/Safeguard/Achievement を初期化。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.src.auth.models import (
    AchievementEntity,
    SafeguardStateEntity,
    UserEntity,
)
from backend.src.auth.repositories import (
    AchievementRepository,
    SafeguardStateRepository,
    UserRepository,
)
from backend.src.common.logging import AuditLogger

_LOGGER = AuditLogger(service="auth-edge")


def initialize_user(
    user_id: str,
    email: str,
    *,
    users: UserRepository,
    safeguards: SafeguardStateRepository,
    achievements: AchievementRepository,
    now: datetime,
) -> None:
    """新規ユーザーのエンティティ群を冪等初期化する（INIT-01/02）。

    既存ユーザーには何もしない（再試行で二重作成しない）。

    Args:
        user_id: Cognito sub。
        email: メールアドレス。
        users / safeguards / achievements: リポジトリ。
        now: 現在時刻。
    """
    if users.exists(user_id):
        return  # 冪等: 既存なら no-op
    iso = now.isoformat()
    month_anchor = now.strftime("%Y-%m")
    users.put(UserEntity(id=user_id, email=email, created_at=iso))
    safeguards.put(SafeguardStateEntity(user_id=user_id, month_anchor=month_anchor))
    achievements.put(AchievementEntity(user_id=user_id, updated_at=iso))


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """Cognito Post Confirmation トリガーの Lambda ハンドラ。

    実際のリポジトリ（DynamoDB 実装）は遅延 import で注入する。
    """
    from backend.src.auth.repositories.dynamodb import (
        DynamoAchievementRepository,
        DynamoSafeguardStateRepository,
        DynamoUserRepository,
    )

    attrs = event.get("request", {}).get("userAttributes", {})
    user_id = attrs.get("sub", "")
    email = attrs.get("email", "")
    if user_id:
        initialize_user(
            user_id,
            email,
            users=DynamoUserRepository(),
            safeguards=DynamoSafeguardStateRepository(),
            achievements=DynamoAchievementRepository(),
            now=datetime.now(UTC),
        )
        _LOGGER.log("info", "user initialized", {"userId": user_id})
    return event
