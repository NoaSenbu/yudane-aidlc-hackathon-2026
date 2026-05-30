"""Unit-3 Debate Store Protocol 定義（Phase 2 Step 4.2 Green）。

`local_mode.py` の LocalCooldownStore / LocalMemoryStore と本番実装（cooldown.py / Memory Hook）が
同じインターフェースを満たすことを型レベルで保証する。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 4
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.src.debate.domain.memory_context import MemoryContext
from backend.src.debate.domain.results import CooldownDecision, CooldownState


class CooldownStoreProtocol(Protocol):
    """Cooldown DDB Adapter のインターフェース。

    本番実装は `backend.src.debate.cooldown` の `check_cooldown` / `increment_refuse_count`、
    ローカル実装は `LocalCooldownStore` がこの Protocol を満たす。
    """

    def check_cooldown(
        self,
        actor_id: str,
        now: datetime,
    ) -> CooldownDecision:
        """ユーザーの現在のクールダウン状態を判定する。"""
        ...  # pragma: no cover

    def increment_refuse_count(
        self,
        actor_id: str,
        now: datetime,
        *,
        after_natural_release: bool = False,
    ) -> CooldownState:
        """拒否カウントをインクリメントする。"""
        ...  # pragma: no cover


class MemoryStoreProtocol(Protocol):
    """AgentCore Memory Hook のインターフェース。

    本番実装は Strands `MemoryHook` 経由（Phase 3 で完成）、ローカル実装は
    `LocalMemoryStore` が empty MemoryContext を返す。
    """

    async def build_memory_context(self, actor_id: str) -> MemoryContext:
        """Memory retrieve 結果から MemoryContext を構築する。"""
        ...  # pragma: no cover

    async def record_event(
        self,
        actor_id: str,
        session_id: str,
        axis: str,
        outcome: str,
        turn: int,
    ) -> None:
        """論破セッションの 1 turn 結果を Memory に記録する。"""
        ...  # pragma: no cover
