"""ALG-PROMPT: M-1 + M-2 併走プロンプト合成エントリ（Phase 2 Step 2.2 Green）。

純関数 `compose_debate_prompt(user_input, asin, stress_level, memory_context)` を提供。
**stress_level=mid/high のとき必ず m2_reward_axis を含める**（PROMPT-02 不変条件、PBT-03 重点）。

ブロック序列（PROMPT-01 固定）:
    base → m1_fact_axis → m1_psychology_axis → (条件付き) m2_reward_axis

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-logic-model.md ALG-PROMPT
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §3 PROMPT-01〜10
"""

from __future__ import annotations

from typing import Final

from backend.src.debate.domain.memory_context import MemoryContext
from backend.src.debate.domain.results import (
    ComposedPrompt,
    DebateAxis,
    StressLevel,
)
from backend.src.debate.prompts.base import render_base_block
from backend.src.debate.prompts.m1_fact_axis import render_m1_fact_axis_block
from backend.src.debate.prompts.m1_psychology_axis import (
    render_m1_psychology_axis_block,
)
from backend.src.debate.prompts.m2_reward_axis import render_m2_reward_axis_block

# ---------------------------------------------------------------------------
# PROMPT-CONFIG（business-rules.md §3 と整合）
# ---------------------------------------------------------------------------

#: 合成プロンプトの最大長（PROMPT-07 不変条件、概算 token 数として）
PROMPT_MAX_LENGTH_CHARS: Final[int] = 8000

#: 初回ユーザー（Memory empty）の既定軸
PROMPT_DEFAULT_PREFERRED_AXIS: Final[str] = "fact"

#: profile 未設定時の時給換算既定値（円）
PROMPT_HOURLY_WAGE_FALLBACK_YEN: Final[int] = 2500


def compose_debate_prompt(
    user_input: str,
    asin: str,
    stress_level: StressLevel,
    memory_context: MemoryContext,
) -> ComposedPrompt:
    """M-1 + M-2 併走プロンプトを合成する純関数（ALG-PROMPT）。

    PROMPT-01 ブロック序列: base → m1_fact → m1_psychology → (mid/high 時) m2_reward

    Args:
        user_input: ユーザーの自然文入力。
        asin: Amazon ASIN（10 桁英数字大文字）。
        stress_level: 'low' / 'mid' / 'high'（estimate_stress_level の戻り値）。
        memory_context: Memory retrieve 結果（empty でも動作可能、preferred_axis='fact' 既定）。

    Returns:
        ComposedPrompt:
            - text: 合成プロンプト全文（max PROMPT_MAX_LENGTH_CHARS）
            - axes: 含まれる軸のリスト（fact / psychology は必須、reward は条件付き）

    不変条件（PBT-03 / PBT-08 重点）:
        - 'reward' in axes  ⟺  stress_level in {'mid', 'high'}
        - 'fact' in axes（必須）
        - 'psychology' in axes（必須）
        - len(text) <= PROMPT_MAX_LENGTH_CHARS
    """
    hourly_wage = memory_context.hourly_wage_yen or PROMPT_HOURLY_WAGE_FALLBACK_YEN

    blocks: list[str] = []
    axes: list[DebateAxis] = []

    # 1. base block（NG-1〜8 ガードレール、トーン指示、ASIN + user_input 埋め込み）
    blocks.append(render_base_block(user_input=user_input, asin=asin))

    # 2. m1_fact_axis block（PROMPT-01 ブロック序列）
    blocks.append(
        render_m1_fact_axis_block(
            hourly_wage_yen=hourly_wage,
            calendar_context=memory_context.calendar_context,
        )
    )
    axes.append("fact")

    # 3. m1_psychology_axis block
    blocks.append(render_m1_psychology_axis_block(memory_context=memory_context))
    axes.append("psychology")

    # 4. m2_reward_axis block（stress_level=mid/high のときのみ、PROMPT-02 不変条件）
    if stress_level in ("mid", "high"):
        blocks.append(
            render_m2_reward_axis_block(
                stress_level=stress_level,
                calendar_context=memory_context.calendar_context,
            )
        )
        axes.append("reward")

    text = "\n\n".join(blocks)

    # PROMPT-07 不変条件: 万一テンプレート展開で 8000 文字超過した場合は切り詰める
    if len(text) > PROMPT_MAX_LENGTH_CHARS:
        text = text[:PROMPT_MAX_LENGTH_CHARS]

    return ComposedPrompt(text=text, axes=axes)
