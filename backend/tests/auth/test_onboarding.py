"""オンボ段階保存ロジックの単体テスト + PBT（NFR2-COV / PBT-04）。"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.auth.models import UserEntity
from backend.src.auth.onboarding import (
    ProfilePatch,
    apply_profile_patch,
    compute_monthly_limit_yen,
    is_profile_complete,
)


def _new_user() -> UserEntity:
    return UserEntity(id="u1", email="a@example.com", created_at="2026-05-30T00:00:00Z")


def test_step_advances_and_completes() -> None:
    """5 項目入力で profile_completed=true。"""
    user = _new_user()
    user = apply_profile_patch(user, ProfilePatch(monthly_disposable_yen=100_000, step=1))
    user = apply_profile_patch(user, ProfilePatch(monthly_savings_yen=30_000, step=2))
    user = apply_profile_patch(user, ProfilePatch(favorite_brands=["A", "B"], step=3))
    user = apply_profile_patch(user, ProfilePatch(ng_categories=["gamble"], step=4))
    user = apply_profile_patch(
        user,
        ProfilePatch(has_debt=False, associates_disclosure_acknowledged=True, step=5),
    )
    assert user.profile_completed
    assert user.onboarding_step == 5


def test_favorite_brands_dedup() -> None:
    """好きなブランドは重複除去（ONB-04）。"""
    user = apply_profile_patch(_new_user(), ProfilePatch(favorite_brands=["A", "A", "B"], step=3))
    assert user.favorite_brands == ["A", "B"]


def test_compute_monthly_limit() -> None:
    """月間上限は使える額の 70%（ONB-06）。"""
    assert compute_monthly_limit_yen(100_000) == 70_000


def test_incomplete_profile() -> None:
    """未完了は profile_completed=false。"""
    user = apply_profile_patch(_new_user(), ProfilePatch(monthly_disposable_yen=100_000, step=1))
    assert not is_profile_complete(user)


@given(step=st.integers(min_value=0, max_value=5))
@settings(max_examples=100)
def test_step_never_regresses(step: int) -> None:
    """PBT-04: step は後退しない（同一/小さい step の再適用で前進済みを維持）。"""
    user = _new_user()
    user.onboarding_step = 3
    updated = apply_profile_patch(user, ProfilePatch(step=step))
    assert updated.onboarding_step == max(3, step)


@given(
    disposable=st.integers(min_value=0, max_value=1_000_000),
    step=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100)
def test_patch_idempotent(disposable: int, step: int) -> None:
    """PBT-04: 同一 patch の二重適用で結果が変わらない（冪等）。"""
    user = _new_user()
    once = apply_profile_patch(user, ProfilePatch(monthly_disposable_yen=disposable, step=step))
    twice = apply_profile_patch(once, ProfilePatch(monthly_disposable_yen=disposable, step=step))
    assert once.model_dump() == twice.model_dump()
