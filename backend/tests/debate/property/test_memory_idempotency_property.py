"""Phase 4 Step 4-3.3 PBT-05: Memory write Idempotency プロパティ。

PBT-05 (NFR-PBT-DEBATE-05) 冪等性:
  LocalMemoryStore.record_event を同一 (actor_id, session_id, turn) で 2 回呼んでも
  Memory state（build_memory_context の戻り値）が変わらない不変条件を property 化。

  Phase 2 では LocalMemoryStore は record_event でログ出力のみ + build_memory_context は
  常に empty MemoryContext を返す fail-safe 設計。よって冪等性は trivial に成立するが、
  property 化することで「将来の実装変更時に Memory write の冪等性を保つ」ガードレールになる。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-3.3
"""

from __future__ import annotations

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.debate.local_mode import LocalMemoryStore

# ---------------------------------------------------------------------------
# Hypothesis Arbitrary
# ---------------------------------------------------------------------------

actor_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=8,
    max_size=36,
)
session_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=ord("0"), max_codepoint=ord("9")),
    min_size=26,
    max_size=32,
)
axis_strategy = st.sampled_from(["fact", "psychology", "reward"])
outcome_strategy = st.sampled_from(["agreed", "refused", "ongoing"])
turn_strategy = st.integers(min_value=1, max_value=20)


# ---------------------------------------------------------------------------
# PBT-05: record_event を 2 回呼んでも MemoryContext は変わらない（冪等）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    actor_id=actor_id_strategy,
    session_id=session_id_strategy,
    axis=axis_strategy,
    outcome=outcome_strategy,
    turn=turn_strategy,
)
def test_record_event_double_call_does_not_change_state(
    actor_id: str,
    session_id: str,
    axis: str,
    outcome: str,
    turn: int,
) -> None:
    """record_event を 2 回呼んでも build_memory_context の結果は同一（idempotent）。"""

    async def _scenario() -> None:
        store = LocalMemoryStore()
        # 1 回目の record_event
        await store.record_event(actor_id, session_id, axis, outcome, turn)
        ctx_a = await store.build_memory_context(actor_id)
        # 2 回目の record_event（同一 (actor_id, session_id, turn)）
        await store.record_event(actor_id, session_id, axis, outcome, turn)
        ctx_b = await store.build_memory_context(actor_id)
        assert ctx_a == ctx_b

    asyncio.run(_scenario())


# ---------------------------------------------------------------------------
# PBT-05: build_memory_context は actor_id 非依存性（empty 返却）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(actor_a=actor_id_strategy, actor_b=actor_id_strategy)
def test_build_memory_context_actor_independent(actor_a: str, actor_b: str) -> None:
    """build_memory_context は actor_id によらず empty を返す（fail-safe）。"""

    async def _scenario() -> None:
        store = LocalMemoryStore()
        ctx_a = await store.build_memory_context(actor_a)
        ctx_b = await store.build_memory_context(actor_b)
        assert ctx_a == ctx_b

    asyncio.run(_scenario())
