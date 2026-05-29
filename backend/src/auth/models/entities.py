"""Unit-2 ドメインエンティティ（domain-entities.md）。

DynamoDB 永続化を伴う業務エンティティの Pydantic 表現。API スキーマ（生成モデル）とは
別に、内部の不変条件を持つドメインモデルとして定義する。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserEntity(BaseModel):
    """User 集約（UserProfile を埋め込み）。"""

    id: str
    email: str
    created_at: str
    profile_completed: bool = False
    onboarding_step: int = Field(default=0, ge=0, le=5)
    # UserProfile 埋め込み（段階保存）
    monthly_disposable_yen: int | None = None
    monthly_savings_yen: int | None = None
    favorite_brands: list[str] = Field(default_factory=list)
    ng_categories: list[str] = Field(default_factory=list)
    has_debt: bool | None = None
    associates_disclosure_acknowledged: bool = False


class SafeguardStateFlags(BaseModel):
    """セーフガードのフラグ群。"""

    cooldown_on: bool = False
    quiet_week: bool = False
    has_debt: bool = False


class SafeguardStateEntity(BaseModel):
    """SafeguardState（Unit-1 SafeguardPolicy の入力源、US-AUTH-03）。"""

    user_id: str
    monthly_limit_yen: int = 0
    current_budget_used_yen: int = 0
    transition_count_month: int = 0
    flags: SafeguardStateFlags = Field(default_factory=SafeguardStateFlags)
    debt_release_requested_at: str | None = None
    month_anchor: str = ""


class AchievementEntity(BaseModel):
    """委ね Lv / 称号 / Streak（UC-05）。"""

    user_id: str
    exp: int = 0
    level: int = 1
    titles: list[str] = Field(default_factory=list)
    current_streak_days: int = 0
    longest_streak_days: int = 0
    updated_at: str = ""
