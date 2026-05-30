"""ALG-BOOST の単体テスト + PBT（発火条件の真理値表 / 価格範囲不変条件）。"""

from __future__ import annotations

import itertools

from hypothesis import given, settings

from backend.src.reel.models import (
    ProductMeta,
    RecommendationContext,
    SafeguardContextFlags,
    ScoreComponents,
    ScoredCandidate,
    TimeBucket,
)
from backend.src.reel.ranking import (
    BOOST_MAX_CARDS,
    BOOST_PRICE_MAX_RATIO,
    BOOST_PRICE_MIN_RATIO,
    apply_boost,
    should_boost,
)
from backend.tests.reel.strategies import recommendation_context


def _ctx(stress: str, late: bool, *, quiet: bool = False, cooldown: bool = False, avg: int = 10_000) -> RecommendationContext:
    return RecommendationContext(
        user_id="u1",
        stress_level=stress,  # type: ignore[arg-type]
        time_bucket=TimeBucket(local_hour=23 if late else 12, is_late_night=late),
        safeguard_flags=SafeguardContextFlags(quiet_week=quiet, cooldown_on=cooldown),
        average_price_yen=avg,
    )


def test_should_boost_truth_table() -> None:
    """発火は『深夜 かつ ストレス mid 以上 かつ 非 quiet 非 cooldown』のみ（REEL-BOOST-01/02）。"""
    for stress, late, quiet, cooldown in itertools.product(
        ["low", "mid", "high"], [True, False], [True, False], [True, False]
    ):
        expected = late and stress in ("mid", "high") and not quiet and not cooldown
        assert should_boost(_ctx(stress, late, quiet=quiet, cooldown=cooldown)) is expected


def _cand(asin: str, price: int) -> ScoredCandidate:
    comp = ScoreComponents(relatedness=1.0, time_boost=0, stress_boost=0, calendar_match=0, recency_decay=0)
    return ScoredCandidate(
        product=ProductMeta(asin=asin, title="x", price_yen=price, image_url="https://e.invalid/i", category="audio", brand="b"),
        base_relatedness=1.0,
        score=1.0,
        origin="purchase-related",
        components=comp,
    )


def test_boost_inserts_high_price_at_head() -> None:
    """高単価カードが先頭に挿入され origin が late-night-boost になる。"""
    ctx = _ctx("high", True, avg=10_000)  # 1.5x=15000, 3x=30000
    scored = [_cand("B000000001", 5_000), _cand("B000000002", 20_000)]
    result = apply_boost(scored, ctx)
    assert result[0].product.asin == "B000000002"
    assert result[0].origin == "late-night-boost"


def test_no_boost_when_not_firing() -> None:
    """発火条件を満たさなければ素通し。"""
    ctx = _ctx("low", True, avg=10_000)
    scored = [_cand("B000000001", 20_000)]
    assert apply_boost(scored, ctx) == scored


# --- PBT ---

@given(ctx=recommendation_context())
@settings(max_examples=200)
def test_boost_price_within_range(ctx: RecommendationContext) -> None:
    """PBT: ブースト枠の価格は平均の 1.5〜3.0 倍内（REEL-BOOST-03）。"""
    scored = [_cand(f"B00000{i:04d}", price) for i, price in enumerate([1_000, 15_000, 25_000, 40_000])]
    result = apply_boost(scored, ctx)
    boosts = [c for c in result if c.origin == "late-night-boost"]
    if ctx.average_price_yen > 0:
        low = ctx.average_price_yen * BOOST_PRICE_MIN_RATIO
        high = ctx.average_price_yen * BOOST_PRICE_MAX_RATIO
        for b in boosts:
            assert low <= b.product.price_yen <= high
    assert len(boosts) <= BOOST_MAX_CARDS
