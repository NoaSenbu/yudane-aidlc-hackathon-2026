"""ALG-RANK の単体テスト + PBT-03（決定論・score=Σ・NG 除外・既出抑制・cooldown）。"""

from __future__ import annotations

from hypothesis import given, settings

from backend.src.reel.models import (
    ProductMeta,
    PurchaseHistoryItem,
    RankingWeights,
    RecentTransition,
    RecommendationContext,
    SafeguardContextFlags,
    TimeBucket,
)
from backend.src.reel.ranking import (
    PurchaseHistoryHeuristicSource,
    rank,
    stress_factor,
)
from backend.tests.reel.strategies import product_meta, recommendation_context

_WEIGHTS = RankingWeights()


def _product(asin: str, category: str = "audio", brand: str = "SoundCore", price: int = 1000) -> ProductMeta:
    return ProductMeta(
        asin=asin,
        title="x",
        price_yen=price,
        image_url="https://example.invalid/i.jpg",
        category=category,
        brand=brand,
    )


def _ctx(**kwargs: object) -> RecommendationContext:
    base: dict[str, object] = {
        "user_id": "u1",
        "purchase_history": (
            PurchaseHistoryItem(
                asin="B000000001", category="audio", brand="SoundCore", price_yen=1000, purchased_at="2026-05-01T00:00:00Z"
            ),
        ),
    }
    base.update(kwargs)
    return RecommendationContext(**base)  # type: ignore[arg-type]


def test_stress_factor_levels() -> None:
    """ストレス係数 low=0/mid=0.5/high=1.0（REEL-RANK-04）。"""
    assert stress_factor("low") == 0.0
    assert stress_factor("mid") == 0.5
    assert stress_factor("high") == 1.0


def test_category_match_scores_higher() -> None:
    """購入履歴とカテゴリ一致する商品が高スコア。"""
    cands = [(_product("B000000010", category="audio"), "purchase-related"),
             (_product("B000000011", category="food"), "purchase-related")]
    result = rank(cands, _ctx(), _WEIGHTS)  # type: ignore[arg-type]
    assert result[0].product.asin == "B000000010"


def test_ng_category_excluded() -> None:
    """NG カテゴリ商品は候補から除外（REEL-RANK-07）。"""
    ctx = _ctx(safeguard_flags=SafeguardContextFlags(ng_categories=("food",)))
    cands = [(_product("B000000020", category="food"), "purchase-related")]
    result = rank(cands, ctx, _WEIGHTS)  # type: ignore[arg-type]
    assert result == []


def test_seen_keys_excluded() -> None:
    """既出 ASIN は再提示しない（REEL-RANK-08）。"""
    cands = [(_product("B000000030"), "purchase-related")]
    result = rank(cands, _ctx(), _WEIGHTS, seen_keys=frozenset({"B000000030"}))  # type: ignore[arg-type]
    assert result == []


def test_post_transition_cooldown_excluded() -> None:
    """遷移直後の同カテゴリは除外（FR-AUTH-03 / REEL-RANK-10）。"""
    ctx = _ctx(recent_transitions=(RecentTransition(category="audio", transitioned_at="2026-05-30T13:00:00Z"),))
    cands = [(_product("B000000040", category="audio"), "purchase-related")]
    result = rank(cands, ctx, _WEIGHTS)  # type: ignore[arg-type]
    assert result == []


def test_late_night_time_boost_applied() -> None:
    """深夜帯は time_boost が加点される。"""
    day = _ctx(time_bucket=TimeBucket(local_hour=12, is_late_night=False))
    night = _ctx(time_bucket=TimeBucket(local_hour=23, is_late_night=True))
    cands = [(_product("B000000050"), "purchase-related")]
    s_day = rank(cands, day, _WEIGHTS)[0].score  # type: ignore[arg-type]
    s_night = rank(cands, night, _WEIGHTS)[0].score  # type: ignore[arg-type]
    assert s_night > s_day


# --- PBT-03 ---

@given(ctx=recommendation_context(), products=product_meta() | product_meta())
@settings(max_examples=200)
def test_score_equals_sum_components(ctx: RecommendationContext, products: ProductMeta) -> None:
    """PBT: score は components の総和に一致（REEL-RANK-03、検算可能）。"""
    result = rank([(products, "purchase-related")], ctx, _WEIGHTS)
    for sc in result:
        assert abs(sc.score - sc.components.total()) < 1e-9


@given(ctx=recommendation_context())
@settings(max_examples=200)
def test_rank_deterministic(ctx: RecommendationContext) -> None:
    """PBT: 同一入力 → 同一順位（決定論、REEL-RANK-02）。"""
    src = PurchaseHistoryHeuristicSource(_FixedCatalog())
    cands = src.fetch(ctx)
    r1 = rank(cands, ctx, _WEIGHTS)
    r2 = rank(cands, ctx, _WEIGHTS)
    assert [s.product.asin for s in r1] == [s.product.asin for s in r2]


@given(ctx=recommendation_context())
@settings(max_examples=200)
def test_no_ng_category_in_result(ctx: RecommendationContext) -> None:
    """PBT: 結果に NG カテゴリ商品が現れない（REEL-RANK-07）。"""
    src = PurchaseHistoryHeuristicSource(_FixedCatalog())
    result = rank(src.fetch(ctx), ctx, _WEIGHTS)
    ng = set(ctx.safeguard_flags.ng_categories)
    assert all(sc.product.category not in ng for sc in result)


class _FixedCatalog:
    """テスト用の固定カタログ（search_items のみ）。"""

    _items = [
        ProductMeta(asin="B0F0000001", title="a", price_yen=1000, image_url="https://e.invalid/i", category="audio", brand="SoundCore"),
        ProductMeta(asin="B0F0000002", title="b", price_yen=2000, image_url="https://e.invalid/i", category="food", brand="MUJI"),
        ProductMeta(asin="B0F0000003", title="c", price_yen=3000, image_url="https://e.invalid/i", category="home", brand="MUJI"),
    ]

    def search_items(self, query: object) -> list[ProductMeta]:
        ng = getattr(query, "exclude_ng_categories", ())
        return [i for i in self._items if i.category not in ng]
