"""ALG-PITCH / ALG-LABEL の単体テスト（フォールバック非空 / 24h 重複 / モデレーション）。"""

from __future__ import annotations

import hashlib

from backend.src.reel.labels import generate_label, generate_pitch, is_safe
from backend.src.reel.models import (
    LabelSource,
    ProductMeta,
    RecommendationContext,
    TimeBucket,
)


class _FakeGenerator:
    """テスト用 TextGenerator（固定応答 or 例外）。"""

    def __init__(self, text: str = "", *, raise_exc: bool = False) -> None:
        self._text = text
        self._raise = raise_exc

    def generate(self, prompt: str) -> str:
        if self._raise:
            raise RuntimeError("bedrock down")
        return self._text


def _product() -> ProductMeta:
    return ProductMeta(
        asin="B0EXAMPLE1", title="イヤホン", price_yen=30000, image_url="https://e.invalid/i", category="audio", brand="SoundCore"
    )


def _ctx(**kwargs: object) -> RecommendationContext:
    base: dict[str, object] = {"user_id": "u1"}
    base.update(kwargs)
    return RecommendationContext(**base)  # type: ignore[arg-type]


def test_moderation_rejects_threat() -> None:
    """NG-6 脅迫型表現は is_safe=false（REEL-LABEL-06）。"""
    assert is_safe("買わないと後悔するよ") is False
    assert is_safe("今日のあなたにご褒美") is True


def test_moderation_rejects_ng3() -> None:
    """NG-3 身体・家族等の言及は is_safe=false（REEL-LABEL-07）。"""
    assert is_safe("あなたの体型にぴったり") is False


def test_pitch_fallback_when_no_generator() -> None:
    """generator なしはテンプレートフォールバック（必ず非空）。"""
    pitch = generate_pitch(_product(), _ctx())
    assert pitch
    assert "イヤホン" in pitch


def test_pitch_fallback_on_llm_failure() -> None:
    """LLM 例外時はテンプレートにフォールバック。"""
    pitch = generate_pitch(_product(), _ctx(), generator=_FakeGenerator(raise_exc=True))
    assert pitch


def test_pitch_fallback_on_unsafe_output() -> None:
    """モデレーション拒否（NG-6）時はテンプレートにフォールバック。"""
    pitch = generate_pitch(_product(), _ctx(), generator=_FakeGenerator("買わないと損するよ"))
    assert "損する" not in pitch


def test_pitch_uses_llm_when_safe() -> None:
    """安全な LLM 出力はそのまま採用。"""
    pitch = generate_pitch(_product(), _ctx(), generator=_FakeGenerator("これ、あなた好みだと思う"))
    assert pitch == "これ、あなた好みだと思う"


def test_label_battle_style_when_calendar() -> None:
    """カレンダー多忙時は戦闘ねぎらい系（AC-4）。フォールバックでも非空。"""
    label = generate_label(_product(), _ctx(calendar_category="presentation"))
    assert label.text
    assert label.source is LabelSource.TEMPLATE_FALLBACK


def test_label_dedup_fallback_changes_text() -> None:
    """直近 24h と重複するフォールバック文言は代替に差し替え（REEL-LABEL-03）。"""
    default = generate_label(_product(), _ctx())
    recent = frozenset({hashlib.sha256(default.text.encode("utf-8")).hexdigest()})
    alt = generate_label(_product(), _ctx(), recent_label_hashes=recent)
    assert alt.text != default.text


def test_label_llm_dedup_falls_back() -> None:
    """LLM 出力が 24h 重複ならテンプレートにフォールバック。"""
    text = "確保しておきました（LLM）"
    recent = frozenset({hashlib.sha256(text.encode("utf-8")).hexdigest()})
    label = generate_label(_product(), _ctx(), recent_label_hashes=recent, generator=_FakeGenerator(text))
    assert label.source is LabelSource.TEMPLATE_FALLBACK


def test_pitch_fatigue_boost_prompt_does_not_crash() -> None:
    """深夜×高ストレスでも生成が成立（疲労連動コピー経路、REEL-LABEL-05）。"""
    ctx = _ctx(stress_level="high", time_bucket=TimeBucket(local_hour=23, is_late_night=True))
    pitch = generate_pitch(_product(), ctx, generator=_FakeGenerator("今日もよく戦った。ご褒美にどうぞ"))
    assert pitch
