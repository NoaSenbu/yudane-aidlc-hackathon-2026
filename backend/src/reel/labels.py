"""ALG-PITCH / ALG-LABEL: 推薦コメント・所有感ラベル生成（B-03、Q4=A）。

LLM 生成 + 出力モデレーション（NG-6/NG-3）+ テンプレートフォールバック + 24h 重複防止。
順位には影響しない（表示テキストのみ）。LLM は TextGenerator で注入（テストはフェイク）。
設計: business-logic ALG-PITCH/LABEL / business-rules REEL-LABEL-01〜08 / R-PAT-MOD-01。
"""

from __future__ import annotations

import re

from backend.src.reel.bedrock_client import TextGenerator
from backend.src.reel.models import (
    LabelSource,
    OwnershipLabel,
    ProductMeta,
    RecommendationContext,
)

# NG-6（脅迫・罪悪感強要）/ NG-3（身体・家族・人種・病歴・宗教）の禁止表現（簡易辞書）
_NG_PATTERNS = (
    re.compile(r"(買わないと|やめると).*(悪化|不幸|損|後悔)"),  # NG-6 脅迫型
    re.compile(r"(罪悪感|責任|義務).*(感じ|持て)"),  # NG-6 罪悪感強要
    re.compile(r"(体型|病気|家族|人種|宗教|持病)"),  # NG-3
)


def is_safe(text: str) -> bool:
    """出力モデレーション: NG-6/NG-3 の禁止表現を含まないか（REEL-LABEL-06/07）。"""
    return not any(p.search(text) for p in _NG_PATTERNS)


def _template_pitch(product: ProductMeta) -> str:
    """ピッチの決定論フォールバック（必ず非空）。"""
    return f"{product.title}、あなた好みだと思う。"


def _template_label(product: ProductMeta, *, battle: bool) -> OwnershipLabel:
    """ラベルの決定論フォールバック（必ず非空、REEL-LABEL-08）。"""
    if battle:
        text = "今週もよく戦ってるね。これ、自分へのご褒美。"
    else:
        text = "確保しておきました"
    return OwnershipLabel(
        text=text,
        rationale=f"{product.brand or product.category}の傾向に合わせて選んだよ",
        source=LabelSource.TEMPLATE_FALLBACK,
    )


def generate_pitch(
    product: ProductMeta,
    ctx: RecommendationContext,
    generator: TextGenerator | None = None,
) -> str:
    """推薦コメントを生成する（FR-REEL-03、深夜×ストレスで疲労連動ブーストコピー優先）。

    LLM 失敗・モデレーション拒否はテンプレートにフォールバック。

    Args:
        product: 対象商品。
        ctx: 推薦コンテキスト。
        generator: LLM 注入（None はフォールバックのみ）。

    Returns:
        モデレーション済みの推薦コメント（必ず非空）。
    """
    if generator is None:
        return _template_pitch(product)
    prompt = _build_pitch_prompt(product, ctx)
    try:
        text = generator.generate(prompt).strip()
    except Exception:  # noqa: BLE001 - LLM 失敗は安全側でフォールバック
        return _template_pitch(product)
    if not text or not is_safe(text):
        return _template_pitch(product)
    return text


def generate_label(
    product: ProductMeta,
    ctx: RecommendationContext,
    *,
    recent_label_hashes: frozenset[str] = frozenset(),
    generator: TextGenerator | None = None,
) -> OwnershipLabel:
    """所有感ラベルを生成する（US-02-05）。

    カレンダー多忙度が高ければ「戦ってるね」系へ（AC-4）。LLM 失敗・モデレーション拒否・
    24h 重複はテンプレートにフォールバック（REEL-LABEL-02/03）。

    Args:
        product: 対象商品。
        ctx: 推薦コンテキスト。
        recent_label_hashes: 直近 24h 提示済みラベルのハッシュ集合。
        generator: LLM 注入（None はフォールバックのみ）。

    Returns:
        所有感ラベル（必ず非空・モデレーション済み・24h 非重複）。
    """
    battle = ctx.calendar_category is not None
    if generator is None:
        return _ensure_unique(_template_label(product, battle=battle), recent_label_hashes, product, battle)
    prompt = _build_label_prompt(product, ctx, battle=battle)
    try:
        text = generator.generate(prompt).strip()
    except Exception:  # noqa: BLE001
        return _template_label(product, battle=battle)
    if not text or not is_safe(text) or _hash(text) in recent_label_hashes:
        return _template_label(product, battle=battle)
    return OwnershipLabel(
        text=text,
        rationale=f"{product.brand or product.category}の傾向に合わせて選んだよ",
        source=LabelSource.LLM,
    )


def _ensure_unique(
    label: OwnershipLabel,
    recent: frozenset[str],
    product: ProductMeta,
    battle: bool,
) -> OwnershipLabel:
    """フォールバックラベルが 24h 重複する場合の代替（REEL-LABEL-03）。"""
    if _hash(label.text) not in recent:
        return label
    alt = "あなたのために、もう一度見つけといた" if not battle else "今日のあなたに、これ。"
    return label.model_copy(update={"text": alt})


def _hash(text: str) -> str:
    """ラベル重複判定用ハッシュ。"""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_pitch_prompt(product: ProductMeta, ctx: RecommendationContext) -> str:
    """ピッチ用プロンプト（M-2 連動の文脈を埋め込む）。"""
    if ctx.stress_level in ("mid", "high") and ctx.time_bucket.is_late_night:
        style = "疲労をねぎらいご褒美として薦める友達口調"
    elif ctx.calendar_category is not None:
        style = f"{ctx.calendar_category}の予定に向けたエージェント提案口調"
    else:
        style = "所有感を醸成する友達口調"
    return f"商品「{product.title}」を{style}で1文。脅迫・罪悪感・身体/家族への言及は禁止。"


def _build_label_prompt(product: ProductMeta, ctx: RecommendationContext, *, battle: bool) -> str:
    """ラベル用プロンプト。"""
    tone = "今週も戦うあなたへのご褒美" if battle else "確保しておいた所有感"
    return f"商品「{product.title}」に{tone}を表す短いラベルを1文。脅迫・罪悪感は禁止。"
