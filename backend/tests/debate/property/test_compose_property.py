"""Prompt Composition の PBT-03 / PBT-08 プロパティ（Phase 2 Step 2.4 PBT 補強）。

PBT-03: 任意の stress_level='mid' or 'high' で必ず 'reward' in composed.axes
        （PROMPT-02 不変条件、FR-DEBATE-09）。
PBT-08: 任意のユーザー入力 + ASIN で text 長さ <= PROMPT_MAX_LENGTH_CHARS、
        text に [FACT] / [PSYCHOLOGY] マーカーが必ず含まれる。

参照: aidlc-docs/construction/unit-3-debate/nfr-requirements/nfr-requirements.md
      NFR-PBT-DEBATE-03 / NFR-PBT-DEBATE-08
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from backend.src.debate.domain.memory_context import (
    CalendarContext,
    MemoryContext,
)
from backend.src.debate.prompts.compose import (
    PROMPT_MAX_LENGTH_CHARS,
    compose_debate_prompt,
)

# ---------------------------------------------------------------------------
# Hypothesis Arbitrary
# ---------------------------------------------------------------------------

asin_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=10,
    max_size=10,
)

# user_input は 1〜2000 文字、制御文字を除く（ValidationError 回避）
user_input_strategy = st.text(min_size=1, max_size=200).filter(
    lambda s: all(ord(c) >= 0x20 or c in "\n\t" for c in s)
)

stress_level_mid_or_high_strategy = st.sampled_from(["mid", "high"])
stress_level_all_strategy = st.sampled_from(["low", "mid", "high"])

axis_strategy = st.sampled_from(["fact", "psychology", "reward"])
affirmation_style_strategy = st.sampled_from(["casual", "cool", "caring"])


@st.composite
def memory_context_strategy(draw: st.DrawFn) -> MemoryContext:
    """有効な MemoryContext を生成する Arbitrary。"""
    return MemoryContext(
        recent_debate_outcomes=[],
        preferred_axis=draw(axis_strategy),  # type: ignore[arg-type]
        stress_signals=[],
        m1m2_axis_extracted=[],
        hourly_wage_yen=draw(st.integers(min_value=500, max_value=10000)),
        calendar_context=CalendarContext(
            upcoming_event_categories=draw(
                st.lists(
                    st.sampled_from(["work", "social", "travel", "family"]),
                    min_size=0,
                    max_size=3,
                )
            ),
            busy_hours_per_week=draw(st.integers(min_value=0, max_value=80)),
        ),
        preferred_affirmation_style=draw(affirmation_style_strategy),
    )


# ---------------------------------------------------------------------------
# PBT-03: M-2 reward axis 必須含有
# ---------------------------------------------------------------------------


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    stress_level=stress_level_mid_or_high_strategy,
    memory_context=memory_context_strategy(),
)
def test_mid_or_high_stress_always_includes_reward_axis(
    user_input: str,
    asin: str,
    stress_level: str,
    memory_context: MemoryContext,
) -> None:
    """PBT-03: stress_level='mid' or 'high' で必ず 'reward' in axes（PROMPT-02 不変条件）。"""
    result = compose_debate_prompt(
        user_input=user_input,
        asin=asin,
        stress_level=stress_level,  # type: ignore[arg-type]
        memory_context=memory_context,
    )
    assert (
        "reward" in result.axes
    ), f"PBT-03 violation: 'reward' missing for stress_level={stress_level}"


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    memory_context=memory_context_strategy(),
)
def test_low_stress_never_includes_reward_axis(
    user_input: str,
    asin: str,
    memory_context: MemoryContext,
) -> None:
    """PBT-03 逆: stress_level='low' では 'reward' not in axes（PROMPT-02 逆向き）。"""
    result = compose_debate_prompt(
        user_input=user_input,
        asin=asin,
        stress_level="low",
        memory_context=memory_context,
    )
    assert "reward" not in result.axes


# ---------------------------------------------------------------------------
# PBT-08: text 長さ + マーカー
# ---------------------------------------------------------------------------


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    stress_level=stress_level_all_strategy,
    memory_context=memory_context_strategy(),
)
def test_text_length_always_within_limit(
    user_input: str,
    asin: str,
    stress_level: str,
    memory_context: MemoryContext,
) -> None:
    """PBT-08: 任意の入力で len(text) <= PROMPT_MAX_LENGTH_CHARS。"""
    result = compose_debate_prompt(
        user_input=user_input,
        asin=asin,
        stress_level=stress_level,  # type: ignore[arg-type]
        memory_context=memory_context,
    )
    assert len(result.text) <= PROMPT_MAX_LENGTH_CHARS


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    stress_level=stress_level_all_strategy,
    memory_context=memory_context_strategy(),
)
def test_text_always_contains_fact_and_psychology_markers(
    user_input: str,
    asin: str,
    stress_level: str,
    memory_context: MemoryContext,
) -> None:
    """PBT-08: 任意の入力で text に [FACT] と [PSYCHOLOGY] マーカーが含まれる（PROMPT-08）。"""
    result = compose_debate_prompt(
        user_input=user_input,
        asin=asin,
        stress_level=stress_level,  # type: ignore[arg-type]
        memory_context=memory_context,
    )
    assert "[FACT]" in result.text
    assert "[PSYCHOLOGY]" in result.text


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    stress_level=stress_level_all_strategy,
    memory_context=memory_context_strategy(),
)
def test_axes_always_contains_fact_and_psychology(
    user_input: str,
    asin: str,
    stress_level: str,
    memory_context: MemoryContext,
) -> None:
    """PBT-08 関連: 任意の入力で axes に 'fact' と 'psychology' が必ず含まれる。"""
    result = compose_debate_prompt(
        user_input=user_input,
        asin=asin,
        stress_level=stress_level,  # type: ignore[arg-type]
        memory_context=memory_context,
    )
    assert "fact" in result.axes
    assert "psychology" in result.axes
