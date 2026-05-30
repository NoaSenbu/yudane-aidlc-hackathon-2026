"""テスト用インメモリリポジトリ（Protocol を満たす）。"""

from __future__ import annotations

from backend.src.auth.models import (
    AchievementEntity,
    SafeguardStateEntity,
    UserEntity,
)


class FakeUserRepository:
    """インメモリ Users。"""

    def __init__(self) -> None:
        self._data: dict[str, UserEntity] = {}

    def get(self, user_id: str) -> UserEntity | None:
        return self._data.get(user_id)

    def put(self, user: UserEntity) -> None:
        self._data[user.id] = user

    def exists(self, user_id: str) -> bool:
        return user_id in self._data


class FakeSafeguardStateRepository:
    """インメモリ SafeguardStates。"""

    def __init__(self) -> None:
        self._data: dict[str, SafeguardStateEntity] = {}

    def get(self, user_id: str) -> SafeguardStateEntity | None:
        return self._data.get(user_id)

    def put(self, state: SafeguardStateEntity) -> None:
        self._data[state.user_id] = state


class FakeAchievementRepository:
    """インメモリ Achievements。"""

    def __init__(self) -> None:
        self._data: dict[str, AchievementEntity] = {}

    def get(self, user_id: str) -> AchievementEntity | None:
        return self._data.get(user_id)

    def put(self, achievement: AchievementEntity) -> None:
        self._data[achievement.user_id] = achievement
