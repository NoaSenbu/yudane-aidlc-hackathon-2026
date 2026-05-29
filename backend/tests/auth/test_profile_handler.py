"""profile / 負債ハンドラのドメインロジック単体テスト（US-AUTH-01/03）。"""

from __future__ import annotations

from datetime import datetime

import pytest

from backend.src.auth.handlers.profile import apply_profile_update
from backend.src.auth.handlers.safeguard_debt import apply_debt_action
from backend.src.auth.models import SafeguardStateEntity, UserEntity
from backend.src.auth.onboarding import ProfilePatch
from backend.src.common.exceptions import DomainError
from backend.tests.auth.fakes import FakeSafeguardStateRepository, FakeUserRepository

_NOW = datetime.fromisoformat("2026-05-30T00:00:00")


def _seed() -> tuple[FakeUserRepository, FakeSafeguardStateRepository]:
    users = FakeUserRepository()
    safeguards = FakeSafeguardStateRepository()
    users.put(UserEntity(id="u1", email="a@example.com", created_at="2026-05-30T00:00:00Z"))
    safeguards.put(SafeguardStateEntity(user_id="u1"))
    return users, safeguards


def test_profile_completion_sets_monthly_limit() -> None:
    """完了時に月間上限が 70% で確定（ONB-06）。"""
    users, safeguards = _seed()
    for patch in [
        ProfilePatch(monthly_disposable_yen=100_000, step=1),
        ProfilePatch(monthly_savings_yen=20_000, step=2),
        ProfilePatch(favorite_brands=["A"], step=3),
        ProfilePatch(ng_categories=["x"], step=4),
        ProfilePatch(has_debt=False, associates_disclosure_acknowledged=True, step=5),
    ]:
        apply_profile_update("u1", patch, users=users, safeguards=safeguards)
    assert safeguards.get("u1").monthly_limit_yen == 70_000


def test_profile_debt_sets_flags() -> None:
    """完了時に負債ありなら冷却 ON（US-AUTH-03 連携）。"""
    users, safeguards = _seed()
    for patch in [
        ProfilePatch(monthly_disposable_yen=100_000, step=1),
        ProfilePatch(monthly_savings_yen=20_000, step=2),
        ProfilePatch(favorite_brands=["A"], step=3),
        ProfilePatch(ng_categories=["x"], step=4),
        ProfilePatch(has_debt=True, associates_disclosure_acknowledged=True, step=5),
    ]:
        apply_profile_update("u1", patch, users=users, safeguards=safeguards)
    state = safeguards.get("u1")
    assert state.flags.has_debt
    assert state.flags.cooldown_on


def test_profile_not_found() -> None:
    """存在しないユーザーは not-found。"""
    users, safeguards = _seed()
    with pytest.raises(DomainError) as exc:
        apply_profile_update("ghost", ProfilePatch(step=1), users=users, safeguards=safeguards)
    assert exc.value.status == 404


def test_debt_declare_action() -> None:
    """負債申告アクション（DEBT-01）。"""
    _, safeguards = _seed()
    result = apply_debt_action("u1", "declare", safeguards=safeguards, now=_NOW)
    assert result == "debt-declared"
    assert safeguards.get("u1").flags.has_debt


def test_debt_unknown_action() -> None:
    """不正アクションは validation エラー。"""
    _, safeguards = _seed()
    with pytest.raises(DomainError) as exc:
        apply_debt_action("u1", "bogus", safeguards=safeguards, now=_NOW)
    assert exc.value.category.value == "validation"
