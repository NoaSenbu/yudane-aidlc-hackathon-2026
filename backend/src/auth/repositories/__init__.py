"""Unit-2 リポジトリ（DynamoDB アクセス抽象 + boto3 実装）。"""

from backend.src.auth.repositories.protocols import (
    AchievementRepository,
    SafeguardStateRepository,
    UserRepository,
)

__all__ = [
    "AchievementRepository",
    "SafeguardStateRepository",
    "UserRepository",
]
