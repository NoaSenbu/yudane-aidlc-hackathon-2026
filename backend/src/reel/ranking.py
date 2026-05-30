"""ALG-RANK + ALG-BOOST: リール推薦（B-03、CL-1/CL-2=A / Q2=A）。

候補生成（購入履歴ベース関連商品）→ 決定論的リランク → 深夜ブースト挿入。
すべて純関数（外部 I/O なし、PBT-03 決定論）。LLM は順位に使わない。
設計: business-logic-model ALG-RANK/ALG-BOOST / business-rules REEL-RANK/BOOST。
"""

from __future__ import annotations

from typing import Protocol

from backend.src.reel.models import (
    CardOrigin,
    CatalogQuery,
    ProductMeta,
    RankingWeights,
    RecommendationContext,
    ScoreComponents,
    ScoredCandidate,
)

# 深夜ブースト定数（REEL-BOOST 設定値）
BOOST_PRICE_MIN_RATIO = 1.5
BOOST_PRICE_MAX_RATIO = 3.0
BOOST_MAX_CARDS = 3
CANDIDATE_POOL_SIZE = 50


class CandidateSourcePort(Protocol):
    """候補生成の抽象（R-PAT-RANK-01）。MVP=購入履歴ヒューリスティック / 決勝=ベクトル検索（B-204）。"""

    def fetch(self, ctx: RecommendationContext) -> list[tuple[ProductMeta, CardOrigin]]:
        """コンテキストから候補（商品 + 出自）を返す。"""
        ...


class _CatalogLike(Protocol):
    """ranking が必要とするカタログの最小インターフェース。"""

    def search_items(self, query: CatalogQuery) -> list[ProductMeta]: ...


class PurchaseHistoryHeuristicSource:
    """MVP 候補生成: 購入履歴のカテゴリ/ブランド一致 + 共購買（CL-1=A）。

    購入履歴が空なら cold start（オンボ嗜好 → 不足はキュレーション全件）にフォールバック（CL-3=A）。
    """

    def __init__(self, catalog: _CatalogLike) -> None:
        """カタログ（ProductCatalogPort 互換）を受け取る。"""
        self._catalog = catalog

    def fetch(self, ctx: RecommendationContext) -> list[tuple[ProductMeta, CardOrigin]]:
        """候補（商品 + 出自）を返す。"""
        ng = ctx.safeguard_flags.ng_categories
        if ctx.purchase_history:
            query = CatalogQuery(
                by_category=tuple({h.category for h in ctx.purchase_history}),
                by_brand=tuple({h.brand for h in ctx.purchase_history}),
                seed_asins=tuple(h.asin for h in ctx.purchase_history),
                exclude_ng_categories=ng,
                max_results=CANDIDATE_POOL_SIZE,
            )
            origin: CardOrigin = "purchase-related"
            items = self._catalog.search_items(query)
            return [(item, origin) for item in items]

        # cold start（CL-3）
        seed_query = CatalogQuery(
            by_category=ctx.onboarding_preferences.categories,
            by_brand=ctx.onboarding_preferences.brands,
            exclude_ng_categories=ng,
            max_results=CANDIDATE_POOL_SIZE,
        )
        seeded = self._catalog.search_items(seed_query)
        if seeded:
            return [(item, "onboarding-seed") for item in seeded]
        # キュレーション固定リスト（全件、NG 除外のみ）
        popular = self._catalog.search_items(
            CatalogQuery(exclude_ng_categories=ng, max_results=CANDIDATE_POOL_SIZE)
        )
        return [(item, "curated-popular") for item in popular]


def stress_factor(level: str) -> float:
    """ストレス係数（REEL-RANK-04）: low=0 / mid=0.5 / high=1.0。"""
    return {"low": 0.0, "mid": 0.5, "high": 1.0}.get(level, 0.0)


def _relatedness(product: ProductMeta, ctx: RecommendationContext) -> float:
    """購入履歴との関連度（0..1）。カテゴリ一致 0.6 + ブランド一致 0.4。"""
    if not ctx.purchase_history:
        return 0.5  # cold start は中立値
    categories = {h.category for h in ctx.purchase_history}
    brands = {h.brand for h in ctx.purchase_history}
    score = 0.0
    if product.category in categories:
        score += 0.6
    if product.brand in brands:
        score += 0.4
    return score


def _matches_calendar(product: ProductMeta, ctx: RecommendationContext) -> bool:
    """カレンダーカテゴリと商品の関連（簡易: カテゴリ文字列の包含）。"""
    if ctx.calendar_category is None:
        return False
    return ctx.calendar_category in product.category or product.category in ctx.calendar_category


def _in_post_transition_cooldown(product: ProductMeta, ctx: RecommendationContext) -> bool:
    """遷移直後 10 分の同カテゴリ抑制（FR-AUTH-03 / REEL-RANK-10）。

    recent_transitions に同一カテゴリが含まれれば cooldown 対象とみなす
    （時刻判定の実体は呼び出し側が 10 分窓で絞った recent_transitions を渡す前提）。
    """
    return any(rt.category == product.category for rt in ctx.recent_transitions)


def _recency_penalty(product: ProductMeta, seen_keys: frozenset[str]) -> float:
    """直近表示の減衰（既出は 1.0、未出は 0.0）。"""
    return 1.0 if product.asin in seen_keys else 0.0


def rank(
    candidates: list[tuple[ProductMeta, CardOrigin]],
    ctx: RecommendationContext,
    weights: RankingWeights,
    seen_keys: frozenset[str] = frozenset(),
) -> list[ScoredCandidate]:
    """候補を決定論的にリランクする（純関数、REEL-RANK-02/03）。

    NG カテゴリ除外・既出抑制・遷移後カテゴリ cooldown を適用し、重み付き加算スコアで
    降順ソート（同点は asin 昇順 tiebreak で安定）。

    Args:
        candidates: 候補（商品 + 出自）。
        ctx: 推薦コンテキスト。
        weights: リランク重み。
        seen_keys: 既出 ASIN 集合（カーソル由来）。

    Returns:
        スコア降順の ScoredCandidate（決定論）。
    """
    ng = set(ctx.safeguard_flags.ng_categories)
    scored: list[ScoredCandidate] = []
    for product, origin in candidates:
        if product.category in ng:
            continue
        if product.asin in seen_keys:
            continue
        if _in_post_transition_cooldown(product, ctx):
            continue
        base = _relatedness(product, ctx)
        components = ScoreComponents(
            relatedness=weights.relatedness * base,
            time_boost=weights.time_boost * (1.0 if ctx.time_bucket.is_late_night else 0.0),
            stress_boost=weights.stress_boost * stress_factor(ctx.stress_level),
            calendar_match=weights.calendar_match * (1.0 if _matches_calendar(product, ctx) else 0.0),
            recency_decay=-weights.recency_decay * _recency_penalty(product, seen_keys),
        )
        scored.append(
            ScoredCandidate(
                product=product,
                base_relatedness=base,
                score=components.total(),
                origin=origin,
                components=components,
            )
        )
    scored.sort(key=lambda s: (-s.score, s.product.asin))
    return scored


def should_boost(ctx: RecommendationContext) -> bool:
    """深夜高単価ブーストの発火判定（REEL-BOOST-01/02、Q2=A）。

    22:00〜02:00 かつ ストレス mid 以上、かつ quietWeek/cooldown でない。
    """
    return (
        ctx.time_bucket.is_late_night
        and ctx.stress_level in ("mid", "high")
        and not ctx.safeguard_flags.quiet_week
        and not ctx.safeguard_flags.cooldown_on
    )


def apply_boost(
    scored: list[ScoredCandidate], ctx: RecommendationContext
) -> list[ScoredCandidate]:
    """深夜高単価ブーストをフィード先頭に挿入する（ALG-BOOST、REEL-BOOST-03/04）。

    平均価格の 1.5〜3.0 倍の高単価カードを最大 BOOST_MAX_CARDS 件、origin を
    late-night-boost に書き換えて先頭へ。発火条件を満たさなければ素通し。

    Args:
        scored: リランク済み候補。
        ctx: 推薦コンテキスト。

    Returns:
        ブースト適用後の候補リスト。
    """
    if not should_boost(ctx) or ctx.average_price_yen <= 0:
        return scored
    low = ctx.average_price_yen * BOOST_PRICE_MIN_RATIO
    high = ctx.average_price_yen * BOOST_PRICE_MAX_RATIO
    boosts: list[ScoredCandidate] = []
    rest: list[ScoredCandidate] = []
    for cand in scored:
        if len(boosts) < BOOST_MAX_CARDS and low <= cand.product.price_yen <= high:
            boosts.append(
                cand.model_copy(
                    update={
                        "origin": "late-night-boost",
                    }
                )
            )
        else:
            rest.append(cand)
    return boosts + rest
