"""RLC-01 Reel Feed Orchestrator（B-03）: buildReel の組み立て。

候補生成（CandidateSourcePort）→ 決定論リランク（ALG-RANK）→ 深夜ブースト（ALG-BOOST）
→ 上位 N をラベル/ピッチ付き ReelCard 化 → ReelPage + 次カーソル。
ラベルは同期確定（矛盾解消3、後追いなし）。LLM は注入（テストはフェイク）。
"""

from __future__ import annotations

import uuid

from backend.src.reel.bedrock_client import TextGenerator
from backend.src.reel.cursor import ReelCursor, encode_cursor
from backend.src.reel.labels import generate_label, generate_pitch
from backend.src.reel.models import (
    RankingWeights,
    RecommendationContext,
    ReelCard,
    ReelPage,
)
from backend.src.reel.ranking import CandidateSourcePort, apply_boost, rank

LIMIT = 10


def build_reel(
    ctx: RecommendationContext,
    *,
    source: CandidateSourcePort,
    cursor: ReelCursor,
    weights: RankingWeights | None = None,
    generator: TextGenerator | None = None,
    generated_at: str,
    limit: int = LIMIT,
) -> ReelPage:
    """リールページを組み立てる（ALG-RANK → ALG-BOOST → カード化、純粋寄り）。

    Args:
        ctx: 推薦コンテキスト。
        source: 候補生成ソース（MVP=購入履歴ヒューリスティック）。
        cursor: 現在のページングカーソル（既出抑制・ブースト消費）。
        weights: リランク重み（None は既定）。
        generator: ラベル/ピッチ用 LLM（None はテンプレートフォールバック）。
        generated_at: 生成時刻（ISO 8601、外部から注入で決定論化）。
        limit: 1 ページのカード数。

    Returns:
        ReelPage（cards + 次カーソル + generatedAt）。
    """
    weights = weights or RankingWeights()
    seen = frozenset(cursor.seen_card_keys)

    scored = rank(source.fetch(ctx), ctx, weights, seen_keys=seen)

    consumed_boost = False
    if not cursor.boost_consumed:
        boosted = apply_boost(scored, ctx)
        consumed_boost = any(c.origin == "late-night-boost" for c in boosted)
        scored = boosted

    top = scored[:limit]
    cards: list[ReelCard] = []
    for sc in top:
        label = generate_label(sc.product, ctx, generator=generator)
        pitch = generate_pitch(sc.product, ctx, generator=generator)
        cards.append(
            ReelCard(
                card_id=f"card-{uuid.uuid4().hex[:12]}",
                product=sc.product,
                pitch=pitch,
                ownership_label=label,
                tags=_derive_tags(sc.origin, ctx),
                origin=sc.origin,
                is_high_price_boost=(sc.origin == "late-night-boost"),
                rank_score=sc.score,
            )
        )

    new_keys = tuple(sc.product.asin for sc in top)
    next_cursor = cursor.advance(new_keys, consumed_boost)
    next_token = encode_cursor(next_cursor) if cards else None
    return ReelPage(cards=tuple(cards), next_cursor=next_token, generated_at=generated_at)


def _derive_tags(origin: str, ctx: RecommendationContext) -> tuple[str, ...]:
    """カード出自・文脈から表示タグを導出する。"""
    if origin == "late-night-boost":
        return ("頑張ったあなたへ",)
    if origin == "calendar" or ctx.calendar_category is not None:
        return (f"{ctx.calendar_category}のためのエージェント提案",)
    return ()
