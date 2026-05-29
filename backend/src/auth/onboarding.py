"""オンボーディング段階保存ロジック（ALG-ONBOARD / PAT2-ONB-01、純ロジック）。

サーバー権威の onboarding_step を冪等に前進させ、5 項目完了で profile_completed=true。
DynamoDB アクセスから分離し純関数としてテスト可能にする。
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.src.auth.models import UserEntity

# Unit-1 SafeguardPolicy の DEFAULT 比率（オンボ完了時の上限算出）
DEFAULT_MONTHLY_LIMIT_RATIO = 0.7
TOTAL_ONBOARDING_STEPS = 5


@dataclass(frozen=True)
class ProfilePatch:
    """1 画面分の部分入力（いずれも任意）。"""

    monthly_disposable_yen: int | None = None
    monthly_savings_yen: int | None = None
    favorite_brands: list[str] | None = None
    ng_categories: list[str] | None = None
    has_debt: bool | None = None
    associates_disclosure_acknowledged: bool | None = None
    step: int = 0


def apply_profile_patch(user: UserEntity, patch: ProfilePatch) -> UserEntity:
    """部分入力を User に適用し、onboarding_step を冪等に前進させる（ONB-02/03）。

    step は後退しない（max 演算）。同一 step の再適用で結果が変わらない（冪等、PBT-04）。

    Args:
        user: 現在の User。
        patch: 1 画面分の部分入力。

    Returns:
        更新後の User（新インスタンス、入力は破壊しない）。
    """
    updated = user.model_copy(deep=True)
    if patch.monthly_disposable_yen is not None:
        updated.monthly_disposable_yen = patch.monthly_disposable_yen
    if patch.monthly_savings_yen is not None:
        updated.monthly_savings_yen = patch.monthly_savings_yen
    if patch.favorite_brands is not None:
        # 重複除去（順序保持、ONB-04）
        updated.favorite_brands = list(dict.fromkeys(patch.favorite_brands))
    if patch.ng_categories is not None:
        updated.ng_categories = list(dict.fromkeys(patch.ng_categories))
    if patch.has_debt is not None:
        updated.has_debt = patch.has_debt
    if patch.associates_disclosure_acknowledged is not None:
        updated.associates_disclosure_acknowledged = patch.associates_disclosure_acknowledged

    # step は後退しない（冪等性の要）
    updated.onboarding_step = max(updated.onboarding_step, patch.step)
    updated.profile_completed = is_profile_complete(updated)
    return updated


def is_profile_complete(user: UserEntity) -> bool:
    """5 項目すべて入力済み + 開示確認済みかを判定する（ONB-05）。"""
    return (
        user.monthly_disposable_yen is not None
        and user.monthly_savings_yen is not None
        and len(user.favorite_brands) >= 1
        and user.has_debt is not None
        and user.associates_disclosure_acknowledged
    )


def compute_monthly_limit_yen(monthly_disposable_yen: int) -> int:
    """オンボ完了時の月間上限を算出する（ONB-06、DEFAULT 比率 0.7）。"""
    return round(monthly_disposable_yen * DEFAULT_MONTHLY_LIMIT_RATIO)
