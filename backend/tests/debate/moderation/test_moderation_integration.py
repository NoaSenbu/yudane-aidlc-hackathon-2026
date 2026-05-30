"""Phase 3 Step 3-2.3 Red: main.py の _convert_strands_event への NG パターン検出統合テスト。

`_convert_strands_event` は Strands native event を Mobile 互換 dict に変換する純関数だが、
Phase 3 で第 3 層モデレーション（NG-3 / NG-6 系正規表現）を組み込み、
NG パターン検出時は `moderation_blocked` event を返す（token への変換は行わない）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §1 Step 3-2.3
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-01〜03
"""

from __future__ import annotations

from datetime import UTC, datetime
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


class TestConvertStrandsEventNgDetection:
    """`_convert_strands_event` の NG パターン検出を純関数レベルで検証。"""

    def test_clean_text_returns_token(self) -> None:
        """NG パターンを含まない text は通常通り token に変換される。"""
        result = main._convert_strands_event({"data": "コスト的に損じゃないですか?"})
        assert result == {"type": "token", "delta_text": "コスト的に損じゃないですか?"}

    def test_ng6_text_returns_moderation_blocked(self) -> None:
        """NG-6 罪悪感強要を含む text は moderation_blocked event に変換される。"""
        result = main._convert_strands_event({"data": "今買わないと損するよ"})
        assert result is not None
        assert result["type"] == "moderation_blocked"
        assert result["metadata"]["pattern_id"] == "NG-6"
        assert result["metadata"]["pattern_name"] == "guilt_coercion"

    def test_ng3_insult_returns_moderation_blocked(self) -> None:
        """NG-3 侮辱を含む text は moderation_blocked event に変換される。"""
        result = main._convert_strands_event({"data": "あなたバカじゃないですか"})
        assert result is not None
        assert result["type"] == "moderation_blocked"
        assert result["metadata"]["pattern_id"] == "NG-3"
        assert result["metadata"]["pattern_name"] == "insult"

    def test_victory_boast_returns_moderation_blocked(self) -> None:
        """勝ち誇り型を含む text は moderation_blocked event に変換される。"""
        result = main._convert_strands_event({"data": "はい論破"})
        assert result is not None
        assert result["type"] == "moderation_blocked"
        assert result["metadata"]["pattern_id"] == "NG-3"
        assert result["metadata"]["pattern_name"] == "victory_boast"

    def test_moderation_blocked_metadata_does_not_include_full_text(self) -> None:
        """moderation_blocked metadata に matched_text が含まれない（PII / 内容秘匿）。

        SECURITY-08 と整合: PII / NG 文言の Telemetry 流出を防ぐ。matched_text は
        callback_handler の NgDetection には残るが、Mobile に返す event には含めない。
        """
        result = main._convert_strands_event({"data": "今買わないと損するよ"})
        assert result is not None
        assert "matched_text" not in result["metadata"]
        assert "delta_text" not in result

    def test_non_data_event_returns_none(self) -> None:
        """data 以外の Strands native event は None を返す（既存挙動を維持）。"""
        result = main._convert_strands_event({"event": "tool_use", "tool_name": "x"})
        assert result is None

    def test_empty_data_returns_none(self) -> None:
        """空文字列の data は None を返す（既存挙動を維持）。"""
        result = main._convert_strands_event({"data": ""})
        assert result is None


class TestStrandsAgentNgDetectionEndToEnd:
    """Strands Agent streaming 中に NG パターンを含む chunk が来たら moderation_blocked が yield される。"""

    async def test_ng_chunk_yields_moderation_blocked(self, now: datetime) -> None:
        """Strands Agent から NG-6 含む chunk が来たら moderation_blocked event が yield される。"""

        async def fake_stream(_prompt: str):
            yield {"data": "コスト的に損じゃないですか?"}  # 通常 token
            yield {"data": "今買わないと損する"}  # NG-6 → moderation_blocked
            yield {"data": " 続きの文"}  # 通常 token

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

        moderation_events = [e for e in events if e.get("type") == "moderation_blocked"]
        token_events = [e for e in events if e.get("type") == "token"]
        assert len(moderation_events) == 1
        assert moderation_events[0]["metadata"]["pattern_id"] == "NG-6"
        # NG chunk 自体は token として流さない
        assert all("今買わないと損する" not in e["delta_text"] for e in token_events)
