"""Strands graceful shutdown 80s のテスト（Phase 3-1.1 Red）。

90 秒 hard cutoff の前に 80 秒経過時点で graceful shutdown フックが発火し、
サマリ生成 + 綺麗な session_complete reason='graceful_timeout' を yield する。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §1 Step 3-1
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §1 DEBATE-03
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.src.debate import main
from backend.src.debate.domain.results import (
    ComposedPrompt,
    CooldownDecision,
    StressLevelResult,
)
from backend.src.debate.graceful_shutdown import (
    DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS,
    DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS,
    DEBATE_MAX_DURATION_SECONDS,
    check_graceful_shutdown_status,
)


def _ctx(sub: str = "user-1") -> object:
    return SimpleNamespace(user=SimpleNamespace(sub=sub))


def _payload() -> dict[str, Any]:
    return {
        "user_input": "でも欲しい",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }


class TestCheckGracefulShutdownStatus:
    """`check_graceful_shutdown_status` の純関数テスト。"""

    def test_under_80s_returns_streaming(self) -> None:
        started_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = started_at + timedelta(seconds=50)
        assert check_graceful_shutdown_status(started_at, now) == "streaming"

    def test_at_80s_returns_graceful_shutdown(self) -> None:
        started_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = started_at + timedelta(seconds=80)
        assert check_graceful_shutdown_status(started_at, now) == "graceful_shutdown"

    def test_between_80s_and_90s_returns_graceful_shutdown(self) -> None:
        started_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = started_at + timedelta(seconds=85)
        assert check_graceful_shutdown_status(started_at, now) == "graceful_shutdown"

    def test_at_90s_returns_hard_cutoff(self) -> None:
        started_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = started_at + timedelta(seconds=90)
        assert check_graceful_shutdown_status(started_at, now) == "hard_cutoff"

    def test_over_90s_returns_hard_cutoff(self) -> None:
        started_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        now = started_at + timedelta(seconds=120)
        assert check_graceful_shutdown_status(started_at, now) == "hard_cutoff"

    def test_constants_match_business_rules(self) -> None:
        """business-rules.md DEBATE-CONFIG カタログと整合する。"""
        assert DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS == 80
        assert DEBATE_MAX_DURATION_SECONDS == 90
        assert DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS == 10


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


class TestDebateHandlerGracefulShutdown:
    """debate_handler の graceful shutdown 統合テスト。"""

    async def test_under_80s_streams_normally(self, now: datetime) -> None:
        """80 秒未満なら通常 streaming（graceful shutdown 未発火）。"""
        composed = ComposedPrompt(text="P", axes=["fact", "psychology"])
        stress = StressLevelResult(level="low", score=0, signals_used=[])

        async def fast_stream(_prompt: str):
            yield {"data": "hello"}
            yield {"data": "world"}

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "_check_cooldown_dispatcher",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(main, "compose_debate_prompt", return_value=composed),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
            patch.object(main, "_now_for_session", return_value=now),
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = fast_stream
            mock_get_agent.return_value = mock_agent

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        # graceful_shutdown_initiated event が含まれない（速攻終了）
        types = [e["type"] for e in events]
        assert "graceful_shutdown_initiated" not in types
        assert types[-1] == "session_complete"
        # reason は agent_completed（graceful_timeout でも hard_timeout でもない）
        assert events[-1]["metadata"]["reason"] == "agent_completed"

    async def test_at_80s_yields_graceful_shutdown_initiated(
        self, now: datetime
    ) -> None:
        """80 秒経過時点で graceful_shutdown_initiated event を yield、その後 graceful_timeout で完了。"""
        composed = ComposedPrompt(text="P", axes=["fact", "psychology"])
        stress = StressLevelResult(level="low", score=0, signals_used=[])

        # 0 秒、20 秒、40 秒、60 秒、80 秒で chunk が来る想定（80s で graceful 発火）
        chunk_times = [0, 20, 40, 60, 80]
        chunk_index = [0]
        elapsed_at_chunk: list[int] = []

        async def slow_stream(_prompt: str):
            for i, t in enumerate(chunk_times):
                elapsed_at_chunk.append(t)
                chunk_index[0] = i
                yield {"data": f"chunk_{t}s"}

        # _now_for_session が呼ばれるたびに chunk_index に応じた時刻を返す
        def fake_now() -> datetime:
            i = chunk_index[0]
            t = chunk_times[i] if i < len(chunk_times) else chunk_times[-1]
            return now + timedelta(seconds=t)

        with (
            patch.object(main, "is_kill_switch_enabled", return_value=False),
            patch.object(
                main,
                "_check_cooldown_dispatcher",
                return_value=CooldownDecision(active=False, consecutive_refuses=0),
            ),
            patch.object(main, "estimate_stress_level", return_value=stress),
            patch.object(main, "compose_debate_prompt", return_value=composed),
            patch.object(main, "_get_strands_agent") as mock_get_agent,
            patch.object(main, "_now_for_session", side_effect=fake_now),
        ):
            mock_agent = MagicMock()
            mock_agent.stream_async = slow_stream

            # サマリ生成のモック（async）
            async def mock_invoke_summary(
                _prompt: str, *args: Any, **kwargs: Any
            ) -> str:
                return "ここまでの論破サマリ"

            mock_agent.invoke_async = mock_invoke_summary
            mock_get_agent.return_value = mock_agent

            events: list[dict[str, Any]] = []
            async for evt in main.debate_handler(_payload(), _ctx(), now=now):
                events.append(evt)

        types = [e["type"] for e in events]
        # graceful_shutdown_initiated が yield される
        assert "graceful_shutdown_initiated" in types
        # 最後は session_complete reason='graceful_timeout'
        assert events[-1]["type"] == "session_complete"
        assert events[-1]["metadata"]["reason"] == "graceful_timeout"
