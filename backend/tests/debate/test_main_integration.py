"""Unit-3 Debate main.py の Strands Agent 統合テスト（Phase 2 Step 3.1 Red）。

Strands SDK / bedrock-agentcore SDK の実 import はテストでモック差し替え。
Strands Agent native event の dict 形式（`{"data": "..."}` / tool_use / etc.）から
Mobile 互換の StrandsStreamEvent dict（`{"type": "token", "delta_text": "..."}`）への変換を検証。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 3
参照: aidlc-docs/construction/unit-3-debate/functional-design/strands-agent-design.md §1 main.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.debate import main
from backend.src.debate.domain.results import (
    ComposedPrompt,
    CooldownDecision,
    StressLevelResult,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def _ctx(sub: str = "user-1") -> object:
    return SimpleNamespace(user=SimpleNamespace(sub=sub))


def _payload() -> dict[str, Any]:
    return {
        "user_input": "でも欲しい",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }


async def _mock_agent_stream(
    events: list[dict[str, Any]],
):
    """Strands Agent.stream_async() をモックする async generator。"""
    for evt in events:
        yield evt


class TestStrandsAgentIntegration:
    """Strands Agent 経由の論破セッション統合テスト。"""

    async def test_compose_prompt_passed_to_strands_agent(
        self,
        now: datetime,
    ) -> None:
        """compose_debate_prompt() の出力 text が Strands Agent.stream_async() に渡される。"""
        captured_prompt: list[str] = []

        async def fake_stream(prompt: str):
            captured_prompt.append(prompt)
            yield {"data": "test"}

        composed = ComposedPrompt(
            text="COMPOSED_PROMPT_TEXT", axes=["fact", "psychology"]
        )
        stress = StressLevelResult(level="low", score=0, signals_used=[])

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "check_cooldown",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(main, "compose_debate_prompt", return_value=composed),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = fake_stream
            mock_get_agent.return_value = mock_agent

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        assert captured_prompt == ["COMPOSED_PROMPT_TEXT"]

    async def test_strands_data_event_converts_to_token(self, now: datetime) -> None:
        """Strands `{"data": "hello"}` event が StrandsStreamEvent token に変換される。"""

        async def fake_stream(_prompt: str):
            yield {"data": "[FACT] hello"}
            yield {"data": " world"}

        composed = ComposedPrompt(text="P", axes=["fact", "psychology"])
        stress = StressLevelResult(level="low", score=0, signals_used=[])

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "check_cooldown",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(main, "compose_debate_prompt", return_value=composed),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = fake_stream
            mock_get_agent.return_value = mock_agent

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        token_events = [e for e in events if e.get("type") == "token"]
        assert len(token_events) >= 2
        assert token_events[0]["delta_text"] == "[FACT] hello"
        assert token_events[1]["delta_text"] == " world"

    async def test_session_complete_emitted_at_end(self, now: datetime) -> None:
        """ストリーム終了後に session_complete event が yield される。"""

        async def fake_stream(_prompt: str):
            yield {"data": "test"}

        composed = ComposedPrompt(text="P", axes=["fact", "psychology"])
        stress = StressLevelResult(level="low", score=0, signals_used=[])

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "check_cooldown",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(main, "compose_debate_prompt", return_value=composed),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = fake_stream
            mock_get_agent.return_value = mock_agent

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        last = events[-1]
        assert last["type"] == "session_complete"
        assert last["metadata"]["reason"] == "agent_completed"

    async def test_kill_switch_skips_strands_agent(self, now: datetime) -> None:
        """kill_switch enabled で Strands Agent を呼ばずに kill_switch event を yield。"""
        with (
            patch.object(main, "is_kill_switch_enabled", return_value=True),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        assert not mock_get_agent.called
        assert events[0]["type"] == "error"
        assert events[0]["metadata"]["reason"] == "kill_switch.enabled"

    async def test_cooldown_active_skips_strands_agent(self, now: datetime) -> None:
        """クールダウン中で Strands Agent を呼ばずに cooldown_triggered event を yield。"""
        cooldown_until = now + timedelta(hours=1)
        decision = CooldownDecision(
            active=True,
            cooldown_until=cooldown_until,
            consecutive_refuses=3,
        )

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(main, "check_cooldown", return_value=decision),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        assert not mock_get_agent.called
        assert events[0]["type"] == "debate.cooldown_triggered"

    async def test_stress_level_passed_to_compose(self, now: datetime) -> None:
        """estimate_stress_level の結果が compose_debate_prompt の引数に渡される。"""
        stress = StressLevelResult(level="high", score=5, signals_used=[])
        composed = ComposedPrompt(text="P", axes=["fact", "psychology", "reward"])

        async def fake_stream(_prompt: str):
            yield {"data": "test"}

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "check_cooldown",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(
                main, "compose_debate_prompt", return_value=composed
            ) as mock_compose,
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = fake_stream
            mock_get_agent.return_value = mock_agent

            async for _ in main.debate_handler(_payload(), _ctx(), now=now):
                pass

        # compose_debate_prompt が stress_level='high' で呼ばれた
        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["stress_level"] == "high"

    async def test_action_refuse_calls_increment_refuse_count(
        self, now: datetime
    ) -> None:
        """action='refuse' payload で increment_refuse_count が呼ばれる（PBT-04 idempotency 関連）。"""
        refuse_payload = {
            "action": "refuse",
            "user_input": "やっぱりいらない",
            "asin": "B01ABC1234",
            "trigger": "reel_skip",
        }

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "check_cooldown",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "increment_refuse_count") as mock_inc,
            patch.object(main, "_get_strands_agent") as mock_get_agent,
        ):
            from backend.src.debate.domain.results import CooldownState

            mock_inc.return_value = CooldownState(
                PK="USER#user-1",
                SK="COOLDOWN#current",
                consecutiveRefuses=1,
                lastRefuseAt=now.isoformat(),
                ttl=int((now + timedelta(days=30)).timestamp()),
            )

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(refuse_payload, _ctx(), now=now):
                events.append(evt)

        # increment_refuse_count が呼ばれ、Strands Agent は呼ばれない
        assert mock_inc.called
        assert not mock_get_agent.called
        # debate.refused または refuse_recorded 系の event が yield される
        assert any(
            e.get("type") in ("debate.refused", "refuse_recorded") for e in events
        )
