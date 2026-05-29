"""DynamoDB によるリポジトリ実装（boto3）。

テーブル名は環境変数（auth-stack が注入）から解決する。PK は userId（infrastructure-design Q1=A）。
"""

from __future__ import annotations

import os
from typing import Any

import boto3

from backend.src.auth.models import (
    AchievementEntity,
    SafeguardStateEntity,
    SafeguardStateFlags,
    UserEntity,
)


def _table(env_key: str) -> Any:  # noqa: ANN401 - boto3 Table は型が緩い
    """環境変数からテーブル名を解決して DynamoDB Table を返す。"""
    name = os.environ[env_key]
    return boto3.resource("dynamodb").Table(name)


class DynamoUserRepository:
    """Users テーブル（PK=userId）。"""

    def __init__(self) -> None:
        self._table = _table("USERS_TABLE")

    def get(self, user_id: str) -> UserEntity | None:
        """userId で User を取得する。"""
        item = self._table.get_item(Key={"userId": user_id}).get("Item")
        return UserEntity.model_validate(item) if item else None

    def put(self, user: UserEntity) -> None:
        """User を保存する（upsert）。"""
        self._table.put_item(Item={"userId": user.id, **user.model_dump()})

    def exists(self, user_id: str) -> bool:
        """User の存在を確認する（冪等初期化用）。"""
        return "Item" in self._table.get_item(Key={"userId": user_id})


class DynamoSafeguardStateRepository:
    """SafeguardStates テーブル（PK=userId）。"""

    def __init__(self) -> None:
        self._table = _table("SAFEGUARD_STATES_TABLE")

    def get(self, user_id: str) -> SafeguardStateEntity | None:
        """userId で SafeguardState を取得する。"""
        item = self._table.get_item(Key={"userId": user_id}).get("Item")
        if not item:
            return None
        flags = SafeguardStateFlags.model_validate(item.get("flags", {}))
        return SafeguardStateEntity(
            user_id=item["userId"],
            monthly_limit_yen=int(item.get("monthlyLimitYen", 0)),
            current_budget_used_yen=int(item.get("currentBudgetUsedYen", 0)),
            transition_count_month=int(item.get("transitionCountMonth", 0)),
            flags=flags,
            debt_release_requested_at=item.get("debtReleaseRequestedAt"),
            month_anchor=item.get("monthAnchor", ""),
        )

    def put(self, state: SafeguardStateEntity) -> None:
        """SafeguardState を保存する。"""
        self._table.put_item(
            Item={
                "userId": state.user_id,
                "monthlyLimitYen": state.monthly_limit_yen,
                "currentBudgetUsedYen": state.current_budget_used_yen,
                "transitionCountMonth": state.transition_count_month,
                "flags": state.flags.model_dump(),
                "debtReleaseRequestedAt": state.debt_release_requested_at,
                "monthAnchor": state.month_anchor,
            }
        )


class DynamoAchievementRepository:
    """Achievements テーブル（PK=userId）。"""

    def __init__(self) -> None:
        self._table = _table("ACHIEVEMENTS_TABLE")

    def get(self, user_id: str) -> AchievementEntity | None:
        """userId で Achievement を取得する。"""
        item = self._table.get_item(Key={"userId": user_id}).get("Item")
        return AchievementEntity.model_validate(item) if item else None

    def put(self, achievement: AchievementEntity) -> None:
        """Achievement を保存する。"""
        self._table.put_item(Item={"userId": achievement.user_id, **achievement.model_dump()})
