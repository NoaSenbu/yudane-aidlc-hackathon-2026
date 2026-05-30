"""Unit-3 Debate main.py の最小 smoke test（Phase 1 Step 5.1 Red）。

Phase 1 では Strands Agent / Bedrock の実呼び出しはモックで代替し、
parse_jwt_actor_id / debate_handler のフロー制御のみを検証する。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 5
参照: aidlc-docs/construction/unit-3-debate/functional-design/strands-agent-design.md §1
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from backend.src.debate import main


@pytest.fixture
def now() -> datetime:
    """テスト用の現在時刻。"""
    return datetime(2026, 5, 30, 12, 0, 0, tzinfo=UTC)


def _mock_context_with_user_sub(sub: str | None) -> object:
    """AgentCore Runtime context をモックする。

    Strands Agent で `context.user.sub` でアクセスする想定（PAT-D-SEC-01）。
    """
    if sub is None:
        return SimpleNamespace(user=None)
    return SimpleNamespace(user=SimpleNamespace(sub=sub))


class TestParseJwtActorId:
    """parse_jwt_actor_id の挙動を検証する（PAT-D-SEC-01 / NFR-SEC-DEBATE-01）。"""

    def test_returns_user_sub_from_context(self) -> None:
        """context.user.sub を返す。"""
        ctx = _mock_context_with_user_sub("user-1")
        assert main.parse_jwt_actor_id(ctx) == "user-1"

    def test_returns_none_when_user_is_missing(self) -> None:
        """context.user が None で None を返す（fail-safe）。"""
        ctx = _mock_context_with_user_sub(None)
        assert main.parse_jwt_actor_id(ctx) is None

    def test_returns_none_when_context_has_no_user_attr(self) -> None:
        """context が user 属性を持たないとき None。"""

        class CtxWithoutUser:
            pass

        assert main.parse_jwt_actor_id(CtxWithoutUser()) is None


@pytest.mark.asyncio
async def test_debate_handler_yields_auth_error_when_actor_unresolved(
    now: datetime,
) -> None:
    """actor_id 未解決で auth.unauthenticated エラーを yield する。"""
    pytest.importorskip(
        "pytest_asyncio", reason="pytest-asyncio 必須（async iterator のテスト）"
    )

    ctx = _mock_context_with_user_sub(None)
    payload: dict[str, Any] = {
        "user_input": "迷う",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }

    events: list[dict[str, Any]] = []
    async for evt in main.debate_handler(payload, ctx, now=now):
        events.append(evt)

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["metadata"]["reason"] == "auth.unauthenticated"


@pytest.mark.asyncio
async def test_debate_handler_yields_cooldown_event_when_active(now: datetime) -> None:
    """クールダウン中に Bedrock を呼ばずに cooldown_triggered を yield する（PAT-D-COST-01）。"""
    pytest.importorskip("pytest_asyncio", reason="pytest-asyncio 必須")

    ctx = _mock_context_with_user_sub("user-cooled-down")
    payload: dict[str, Any] = {
        "user_input": "迷う",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }
    cooldown_until = now + timedelta(hours=1)

    from backend.src.debate.domain.results import CooldownDecision

    decision = CooldownDecision(
        active=True,
        cooldown_until=cooldown_until,
        consecutive_refuses=3,
    )

    with (
        patch.object(main, "check_cooldown", return_value=decision) as mock_check,
        patch.object(main, "_run_streaming_agent") as mock_stream,
    ):
        events: list[dict[str, Any]] = []
        async for evt in main.debate_handler(payload, ctx, now=now):
            events.append(evt)

    assert mock_check.called
    assert not mock_stream.called  # Bedrock を呼んでいない（コスト保護）
    assert len(events) == 1
    assert events[0]["type"] == "debate.cooldown_triggered"
    assert events[0]["metadata"]["cooldown_until"] == cooldown_until.isoformat()


@pytest.mark.asyncio
async def test_debate_handler_yields_validation_error_on_invalid_payload(
    now: datetime,
) -> None:
    """payload 検証エラーで error event を yield する。"""
    pytest.importorskip("pytest_asyncio", reason="pytest-asyncio 必須")

    ctx = _mock_context_with_user_sub("user-1")
    invalid_payload: dict[str, Any] = {
        "user_input": "",  # 空文字 = ValidationError
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }

    events: list[dict[str, Any]] = []
    async for evt in main.debate_handler(invalid_payload, ctx, now=now):
        events.append(evt)

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["metadata"]["reason"] == "payload.invalid"


@pytest.mark.asyncio
async def test_debate_handler_ignores_actor_id_in_payload(now: datetime) -> None:
    """payload に actor_id を入れても context 由来の値が使われる（SECURITY-08 不変条件）。

    Phase 1 では Strands Agent をモック、cooldown は inactive 想定で
    streaming dummy が走るパスをテストする。
    """
    pytest.importorskip("pytest_asyncio", reason="pytest-asyncio 必須")

    ctx = _mock_context_with_user_sub("user-real-from-jwt")
    payload: dict[str, Any] = {
        "actor_id": "user-attacker-spoofed",  # 攻撃者の偽装
        "user_input": "迷う",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }

    from backend.src.debate.domain.results import CooldownDecision

    captured_actor_id: list[str] = []

    async def _fake_stream(actor_id: str, invocation: Any, now_arg: datetime) -> Any:
        captured_actor_id.append(actor_id)
        yield {"type": "token", "delta_text": "test"}

    with (
        patch.object(
            main,
            "check_cooldown",
            return_value=CooldownDecision(active=False, consecutive_refuses=0),
        ),
        patch.object(main, "_run_streaming_agent", side_effect=_fake_stream),
        patch.object(main, "is_kill_switch_enabled", return_value=False),
    ):
        events: list[dict[str, Any]] = []
        async for evt in main.debate_handler(payload, ctx, now=now):
            events.append(evt)

    assert captured_actor_id == ["user-real-from-jwt"]  # JWT.sub のみが使われる
    assert events[0]["type"] == "token"


@pytest.mark.asyncio
async def test_debate_handler_yields_kill_switch_event_when_enabled(
    now: datetime,
) -> None:
    """SSM kill-switch=enabled で Bedrock を呼ばずに kill_switch event を yield（PAT-D-COST-04）。"""
    pytest.importorskip("pytest_asyncio", reason="pytest-asyncio 必須")

    ctx = _mock_context_with_user_sub("user-1")
    payload: dict[str, Any] = {
        "user_input": "迷う",
        "asin": "B01ABC1234",
        "trigger": "reel_skip",
    }

    with (
        patch.object(main, "is_kill_switch_enabled", return_value=True) as mock_ks,
        patch.object(main, "check_cooldown") as mock_check,
        patch.object(main, "_run_streaming_agent") as mock_stream,
    ):
        events: list[dict[str, Any]] = []
        async for evt in main.debate_handler(payload, ctx, now=now):
            events.append(evt)

    assert mock_ks.called
    assert not mock_check.called
    assert not mock_stream.called
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["metadata"]["reason"] == "kill_switch.enabled"
