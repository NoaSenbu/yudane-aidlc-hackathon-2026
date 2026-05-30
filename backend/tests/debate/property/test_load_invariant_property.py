"""Phase 4 Step 4-3.4 PBT-06: Load invariant プロパティ。

PBT-06 (NFR-PBT-DEBATE-06) 負荷不変条件:
  compose_debate_prompt() を asyncio.gather で並列実行しても、各セッションの
  結果が独立 = 任意の同時実行数 N で各セッションの (text, axes) が逐次実行と同じ
  （純関数性 / load invariance）の不変条件を property 化。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-3.4
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md PROMPT-CONFIG
"""

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.debate.domain.memory_context import (
    CalendarContext,
    MemoryContext,
)
from backend.src.debate.domain.results import StressLevel
from backend.src.debate.prompts.compose import compose_debate_prompt

# ---------------------------------------------------------------------------
# Hypothesis Arbitrary
# ---------------------------------------------------------------------------

asin_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=10,
    max_size=10,
)
user_input_strategy = st.text(min_size=1, max_size=200).filter(
    lambda s: all(ord(c) >= 0x20 or c in "\n\t" for c in s)
)
stress_level_strategy = st.sampled_from(["low", "mid", "high"])


def _empty_memory_context() -> MemoryContext:
    return MemoryContext(
        recent_debate_outcomes=[],
        preferred_axis="fact",
        stress_signals=[],
        m1m2_axis_extracted=[],
        hourly_wage_yen=2000,
        calendar_context=CalendarContext(
            upcoming_event_categories=[],
            event_count=0,
        ),
    )


# ---------------------------------------------------------------------------
# PBT-06: compose_debate_prompt は純関数（並列実行で結果独立）
# ---------------------------------------------------------------------------
@settings(max_examples=30, deadline=None)
@given(
    sessions=st.lists(
        st.tuples(asin_strategy, user_input_strategy, stress_level_strategy),
        min_size=2,
        max_size=10,
    ),
)
def test_compose_debate_prompt_load_invariant(
    sessions: list[tuple[str, str, StressLevel]],
) -> None:
    """同時 N セッション分の compose を並列実行 ↔ 逐次実行で結果が同じ。"""
    memory_context = _empty_memory_context()

    # 逐次実行
    sequential_results = [
        compose_debate_prompt(
            user_input=user_input,
            asin=asin,
            stress_level=stress,
            memory_context=memory_context,
        )
        for asin, user_input, stress in sessions
    ]

    # 並列実行（純関数なので asyncio.gather + run_in_executor 風にスレッド化しなくても
    # 同期関数の repeated invocation で十分。ここでは「複数回呼ぶ → 同じ結果」を検証）。
    async def _parallel() -> list:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None,
                lambda a=asin, u=user_input, s=stress: compose_debate_prompt(
                    user_input=u,
                    asin=a,
                    stress_level=s,
                    memory_context=memory_context,
                ),
            )
            for asin, user_input, stress in sessions
        ]
        return await asyncio.gather(*tasks)

    parallel_results = asyncio.run(_parallel())

    assert len(parallel_results) == len(sequential_results)
    for seq, par in zip(sequential_results, parallel_results, strict=True):
        assert seq.text == par.text
        assert seq.axes == par.axes


# ---------------------------------------------------------------------------
# PBT-06: 同一入力での複数回 compose は完全一致（決定的）
# ---------------------------------------------------------------------------
@settings(max_examples=30, deadline=None)
@given(
    asin=asin_strategy,
    user_input=user_input_strategy,
    stress=stress_level_strategy,
    invocations=st.integers(min_value=2, max_value=10),
)
def test_compose_debate_prompt_deterministic(
    asin: str,
    user_input: str,
    stress: StressLevel,
    invocations: int,
) -> None:
    """同じ入力で N 回呼んでも text / axes が完全一致（決定的、純関数）。"""
    memory_context = _empty_memory_context()
    results = [
        compose_debate_prompt(
            user_input=user_input,
            asin=asin,
            stress_level=stress,
            memory_context=memory_context,
        )
        for _ in range(invocations)
    ]
    first = results[0]
    for result in results[1:]:
        assert result.text == first.text
        assert result.axes == first.axes
