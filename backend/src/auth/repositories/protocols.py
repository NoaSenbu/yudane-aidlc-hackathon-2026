"""リポジトリの Protocol（DynamoDB 実装と純ロジックを疎結合にする）。

ドメインロジック・ハンドラはこの Protocol に依存し、テストではインメモリ実装を注入する。
"""

from __future__ import annotations

from typing import Protocol

from backend.src.auth.models import (
    AchievementEntity,
    SafeguardStateEntity,
    UserEntity,
)


class UserRepository(Protocol):
    """Users テーブルアクセス。"""

    def get(self, user_id: str) -> UserEntity | None: ...

    def put(self, user: UserEntity) -> None: ...

    def exists(self, user_id: str) -> bool: ...


class SafeguardStateRepository(Protocol):
    """SafeguardStates テーブルアクセス。"""

    def get(self, user_id: str) -> SafeguardStateEntity | None: ...

    def put(self, state: SafeguardStateEntity) -> None: ...


class AchievementRepository(Protocol):
    """Achievements テーブルアクセス。"""

    def get(self, user_id: str) -> AchievementEntity | None: ...

    def put(self, achievement: AchievementEntity) -> None: ...
