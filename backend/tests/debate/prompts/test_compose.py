"""Unit-3 Debate Prompt Composition のテスト（Phase 2 Step 2.1 Red）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §3 PROMPT-01〜10
"""

from __future__ import annotations

import pytest

from backend.src.debate.domain.memory_context import (
    CalendarContext,
    MemoryContext,
    empty_memory_context,
)
from backend.src.debate.prompts.compose import (
    PROMPT_DEFAULT_PREFERRED_AXIS,
    PROMPT_HOURLY_WAGE_FALLBACK_YEN,
    PROMPT_MAX_LENGTH_CHARS,
    compose_debate_prompt,
)


def _full_context(preferred_axis: str = "fact") -> MemoryContext:
    """テスト用にフィールドが埋まった MemoryContext を生成する。"""
    return MemoryContext(
        recent_debate_outcomes=[],
        preferred_axis=preferred_axis,  # type: ignore[arg-type]
        stress_signals=[],
        m1m2_axis_extracted=[],
        hourly_wage_yen=2500,
        calendar_context=CalendarContext(
            upcoming_event_categories=["work"],
            busy_hours_per_week=20,
        ),
        preferred_affirmation_style="casual",
    )


class TestComposeDebatePrompt:
    """`compose_debate_prompt` の挙動を検証する。"""

    def test_low_stress_excludes_reward_axis(self) -> None:
        """stress_level='low' では axes に 'reward' が含まれない（PROMPT-02 不変条件）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert "reward" not in result.axes
        assert "fact" in result.axes
        assert "psychology" in result.axes

    def test_mid_stress_includes_reward_axis(self) -> None:
        """stress_level='mid' で axes に 'reward' が含まれる（FR-DEBATE-09 / PROMPT-02 不変条件）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="mid",
            memory_context=_full_context(),
        )
        assert "reward" in result.axes

    def test_high_stress_includes_reward_axis(self) -> None:
        """stress_level='high' で axes に 'reward' が含まれる（PROMPT-02 不変条件）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="high",
            memory_context=_full_context(),
        )
        assert "reward" in result.axes

    def test_text_length_within_limit(self) -> None:
        """合成プロンプトの長さが PROMPT_MAX_LENGTH_CHARS 以下（PROMPT-07 不変条件）。"""
        result = compose_debate_prompt(
            user_input="あ" * 2000,  # 最大長
            asin="B01ABC1234",
            stress_level="high",
            memory_context=_full_context(),
        )
        assert len(result.text) <= PROMPT_MAX_LENGTH_CHARS

    def test_text_contains_fact_marker(self) -> None:
        """合成プロンプトに [FACT] セクションマーカーが含まれる（PROMPT-08）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert "[FACT]" in result.text

    def test_text_contains_psychology_marker(self) -> None:
        """合成プロンプトに [PSYCHOLOGY] セクションマーカーが含まれる（PROMPT-08）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert "[PSYCHOLOGY]" in result.text

    def test_high_stress_text_contains_reward_marker(self) -> None:
        """stress_level='high' では [REWARD] マーカーが含まれる。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="high",
            memory_context=_full_context(),
        )
        assert "[REWARD]" in result.text

    def test_low_stress_text_does_not_contain_reward_marker(self) -> None:
        """stress_level='low' では m2_reward_axis ブロック（[REWARD] セクション見出し）が含まれない。

        注: base.py の説明文中には「セクションマーカー [FACT] / [PSYCHOLOGY] / [REWARD] を行頭に付ける」
        という指示文が含まれるため、文字列としての `[REWARD]` 出現は許容する。
        論破軸として `axes` に 'reward' が含まれないことが本質的な不変条件。
        """
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        # axes ベースで判定（PROMPT-02 不変条件、PBT-03 重点）
        assert "reward" not in result.axes
        # m2_reward_axis ブロックの先頭文（# [REWARD] ストレス × ご褒美軸の論破指示）が無い
        assert "ストレス × ご褒美軸の論破指示" not in result.text

    def test_pure_function(self) -> None:
        """compose_debate_prompt は純関数（同一入力 → 同一出力、PROMPT-09）。"""
        ctx = _full_context()
        result_a = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="mid",
            memory_context=ctx,
        )
        result_b = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="mid",
            memory_context=ctx,
        )
        assert result_a.text == result_b.text
        assert result_a.axes == result_b.axes

    def test_empty_memory_context_works(self) -> None:
        """empty MemoryContext でも preferred_axis='fact' の既定値で動作（PROMPT-CONFIG）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=empty_memory_context(),
        )
        assert "fact" in result.axes
        assert "psychology" in result.axes
        # empty でも text に既定の時給フォールバックが反映される
        assert str(PROMPT_HOURLY_WAGE_FALLBACK_YEN) in result.text

    def test_user_input_embedded_in_prompt(self) -> None:
        """ユーザー入力がプロンプト本文に埋め込まれる。"""
        result = compose_debate_prompt(
            user_input="お金ない",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert "お金ない" in result.text

    def test_asin_embedded_in_prompt(self) -> None:
        """ASIN がプロンプト本文に埋め込まれる（base block）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert "B01ABC1234" in result.text

    def test_axes_order_is_stable(self) -> None:
        """axes の順序は安定（fact → psychology → reward の順、PROMPT-01）。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="high",
            memory_context=_full_context(),
        )
        assert result.axes == ["fact", "psychology", "reward"]

    def test_preferred_axis_default_is_fact(self) -> None:
        """preferred_axis 未指定時の既定値が 'fact'（PROMPT-CONFIG）。"""
        assert PROMPT_DEFAULT_PREFERRED_AXIS == "fact"

    def test_max_length_constant(self) -> None:
        """PROMPT_MAX_LENGTH_CHARS が business-rules カタログと整合（=8000）。"""
        assert PROMPT_MAX_LENGTH_CHARS == 8000


class TestNgGuardrails:
    """base block の NG-1〜8 ガードレール指示の検証。"""

    @pytest.mark.parametrize("ng_id", ["NG-1", "NG-2", "NG-3", "NG-6", "NG-8"])
    def test_base_block_mentions_ng_constraints(self, ng_id: str) -> None:
        """合成プロンプトに NG-1〜8 のうち主要なガードレール指示が含まれる。"""
        result = compose_debate_prompt(
            user_input="迷う",
            asin="B01ABC1234",
            stress_level="low",
            memory_context=_full_context(),
        )
        assert (
            ng_id in result.text
        ), f"{ng_id} ガードレール指示が base block に含まれていない"
