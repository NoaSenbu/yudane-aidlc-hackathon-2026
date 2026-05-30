"""B-01 Post Confirmation 初期化の単体テスト（INIT-01/02 冪等）。"""

from __future__ import annotations

from datetime import datetime

from backend.src.auth.post_confirmation import initialize_user
from backend.src.auth.pre_token_generation import build_claims
from backend.src.auth.models import AchievementEntity, SafeguardStateEntity
from backend.tests.auth.fakes import (
    FakeAchievementRepository,
    FakeSafeguardStateRepository,
    FakeUserRepository,
)

_NOW = datetime.fromisoformat("2026-05-30T00:00:00")


def test_initialize_creates_entities() -> None:
    """新規ユーザーで 3 エンティティを初期化。"""
    users = FakeUserRepository()
    safeguards = FakeSafeguardStateRepository()
    achievements = FakeAchievementRepository()
    initialize_user(
        "u1", "a@example.com",
        users=users, safeguards=safeguards, achievements=achievements, now=_NOW,
    )
    assert users.get("u1") is not None
    assert safeguards.get("u1") is not None
    assert achievements.get("u1") is not None


def test_initialize_idempotent() -> None:
    """既存ユーザーには二重作成しない（INIT-02）。"""
    users = FakeUserRepository()
    safeguards = FakeSafeguardStateRepository()
    achievements = FakeAchievementRepository()
    initialize_user("u1", "a@example.com", users=users, safeguards=safeguards,
                    achievements=achievements, now=_NOW)
    first = users.get("u1")
    # email を変えて再実行 → 既存なので上書きされない
    initialize_user("u1", "changed@example.com", users=users, safeguards=safeguards,
                    achievements=achievements, now=_NOW)
    assert users.get("u1") == first


def test_build_claims() -> None:
    """Pre Token Generation の claim 構築（INIT-04）。"""
    ach = AchievementEntity(user_id="u1", exp=500, level=3, titles=["本日の湯水使い"])
    sg = SafeguardStateEntity(user_id="u1", monthly_limit_yen=70_000)
    claims = build_claims(ach, sg)
    assert claims["yudane_level"] == "3"
    assert claims["yudane_title"] == "本日の湯水使い"
    assert claims["yudane_monthly_limit"] == "70000"


def test_build_claims_defaults() -> None:
    """エンティティなしは既定 claim。"""
    claims = build_claims(None, None)
    assert claims["yudane_level"] == "1"
    assert claims["yudane_title"] == "new"
    assert claims["yudane_monthly_limit"] == "0"
