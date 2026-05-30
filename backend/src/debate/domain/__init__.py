"""Unit-3 Debate のドメインモデルパッケージ。"""

from backend.src.debate.domain.payloads import (
    ClientSignals,
    DebateAction,
    DebateInvocationPayload,
    DebateTrigger,
)
from backend.src.debate.domain.results import (
    ComposedPrompt,
    CooldownDecision,
    CooldownState,
    DebateAxis,
    StressLevel,
    StressLevelResult,
)

__all__ = [
    "ClientSignals",
    "ComposedPrompt",
    "CooldownDecision",
    "CooldownState",
    "DebateAction",
    "DebateAxis",
    "DebateInvocationPayload",
    "DebateTrigger",
    "StressLevel",
    "StressLevelResult",
]
