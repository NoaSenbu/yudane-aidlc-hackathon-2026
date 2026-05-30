"""Unit-4 Reel の Hypothesis ドメインジェネレータ（PBT-07）。

購入履歴 / 価格 / StressLevel / TimeBucket / SafeguardFlags / ProductMeta の現実的な生成器。
他の PBT テストから再利用する。
"""

from __future__ import annotations

from hypothesis import strategies as st

from backend.src.reel.models import (
    OnboardingPreferences,
    ProductMeta,
    PurchaseHistoryItem,
    RecommendationContext,
    SafeguardContextFlags,
    TimeBucket,
)

# 10 桁英数字 ASIN（大文字、ASIN-01）
asins = st.from_regex(r"^[A-Z0-9]{10}$", fullmatch=True)

categories = st.sampled_from(["audio", "home", "food", "stationery", "presentation", "date"])
brands = st.sampled_from(["SoundCore", "MUJI", "BlueMountain", "Pilot", "Generic"])
stress_levels = st.sampled_from(["low", "mid", "high"])
prices = st.integers(min_value=100, max_value=300_000)


def product_meta() -> st.SearchStrategy[ProductMeta]:
    """ProductMeta の生成器。"""
    return st.builds(
        ProductMeta,
        asin=asins,
        title=st.text(min_size=1, max_size=30),
        price_yen=prices,
        image_url=st.just("https://example.invalid/img.jpg"),
        review_summary=st.text(max_size=20),
        category=categories,
        brand=brands,
    )


def purchase_history_item() -> st.SearchStrategy[PurchaseHistoryItem]:
    """購入履歴 1 件の生成器。"""
    return st.builds(
        PurchaseHistoryItem,
        asin=asins,
        category=categories,
        brand=brands,
        price_yen=prices,
        purchased_at=st.just("2026-05-01T00:00:00Z"),
    )


def time_bucket() -> st.SearchStrategy[TimeBucket]:
    """TimeBucket の生成器（is_late_night と local_hour を整合させる）。"""
    return st.integers(min_value=0, max_value=23).map(
        lambda h: TimeBucket(local_hour=h, is_late_night=(h >= 22 or h < 2))
    )


def safeguard_flags() -> st.SearchStrategy[SafeguardContextFlags]:
    """SafeguardContextFlags の生成器。"""
    return st.builds(
        SafeguardContextFlags,
        quiet_week=st.booleans(),
        cooldown_on=st.booleans(),
        ng_categories=st.lists(categories, max_size=3).map(tuple),
    )


def recommendation_context() -> st.SearchStrategy[RecommendationContext]:
    """RecommendationContext の生成器。"""
    return st.builds(
        RecommendationContext,
        user_id=st.text(min_size=1, max_size=12),
        purchase_history=st.lists(purchase_history_item(), max_size=5).map(tuple),
        onboarding_preferences=st.builds(
            OnboardingPreferences,
            brands=st.lists(brands, max_size=3).map(tuple),
            categories=st.lists(categories, max_size=3).map(tuple),
        ),
        stress_level=stress_levels,
        time_bucket=time_bucket(),
        calendar_category=st.none() | st.sampled_from(["presentation", "date", "camping", "other"]),
        safeguard_flags=safeguard_flags(),
        average_price_yen=st.integers(min_value=0, max_value=100_000),
    )
