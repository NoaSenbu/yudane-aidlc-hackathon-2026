"""Unit-3 Debate プロンプト合成パッケージ。

Phase 2 Step 2 で 6 モジュール構造化（base / m1_fact_axis / m1_psychology_axis /
m2_reward_axis / affirmation / compose）を実装。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md
"""

from backend.src.debate.prompts.compose import (
    PROMPT_DEFAULT_PREFERRED_AXIS,
    PROMPT_HOURLY_WAGE_FALLBACK_YEN,
    PROMPT_MAX_LENGTH_CHARS,
    compose_debate_prompt,
)

__all__ = [
    "PROMPT_DEFAULT_PREFERRED_AXIS",
    "PROMPT_HOURLY_WAGE_FALLBACK_YEN",
    "PROMPT_MAX_LENGTH_CHARS",
    "compose_debate_prompt",
]
