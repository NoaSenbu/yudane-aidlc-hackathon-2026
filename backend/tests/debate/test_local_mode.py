"""Unit-3 Debate ローカル開発モードのテスト（Phase 2 Step 4.1 Red）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 4
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.src.debate import local_mode
from backend.src.debate.local_mode import (
    LocalCooldownStore,
    LocalMemoryStore,
    is_local_mode,
    local_parse_jwt_actor_id,
    reset_local_stores_for_testing,
)


@pytest.fixture(autouse=True)
def _reset_stores() -> None:
    """各テストの前後でシングルトンをリセット。"""
    reset_local_stores_for_testing()
    yield
    reset_local_stores_for_testing()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


class TestIsLocalMode:
    """is_local_mode の判定挙動。"""

    def test_default_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEBATE_LOCAL_MODE", raising=False)
        assert is_local_mode() is False

    def test_empty_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_LOCAL_MODE", "")
        assert is_local_mode() is False

    def test_false_string_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_LOCAL_MODE", "false")
        assert is_local_mode() is False

    def test_true_string_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_LOCAL_MODE", "true")
        assert is_local_mode() is True

    def test_one_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_LOCAL_MODE", "1")
        assert is_local_mode() is True

    def test_yes_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBATE_LOCAL_MODE", "yes")
        assert is_local_mode() is True


class TestLocalParseJwtActorId:
    """JWT バイパス時の actor_id 取得。"""

    def test_default_local_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LOCAL_USER_ID", raising=False)
        assert local_parse_jwt_actor_id() == "local-user"

    def test_custom_local_user_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOCAL_USER_ID", "custom-local-user")
        assert local_parse_jwt_actor_id() == "custom-local-user"


class TestLocalCooldownStore:
    """LocalCooldownStore の挙動（本番 cooldown.py と同じ不変条件）。"""

    def test_check_cooldown_returns_inactive_when_no_record(
        self, now: datetime
    ) -> None:
        store = LocalCooldownStore()
        result = store.check_cooldown("user-1", now)
        assert result.active is False
        assert result.consecutive_refuses == 0

    def test_first_refuse_count_one(self, now: datetime) -> None:
        store = LocalCooldownStore()
        result = store.increment_refuse_count("user-1", now)
        assert result.consecutive_refuses == 1
        assert result.cooldown_until is None

    def test_third_refuse_triggers_cooldown(self, now: datetime) -> None:
        """3 回目で必ず cooldown_until = now + 3h（COOLDOWN-02 / PBT-03 不変条件）。"""
        store = LocalCooldownStore()
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)
        result = store.increment_refuse_count("user-1", now)

        assert result.consecutive_refuses == 3
        assert result.cooldown_until == now + timedelta(hours=3)

    def test_check_cooldown_returns_active_when_in_cooldown(
        self, now: datetime
    ) -> None:
        store = LocalCooldownStore()
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)

        result = store.check_cooldown("user-1", now)
        assert result.active is True
        assert result.consecutive_refuses == 3

    def test_natural_release_returns_inactive(self, now: datetime) -> None:
        """cooldown_until <= now で自然解除（COOLDOWN-04）。"""
        store = LocalCooldownStore()
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)

        # 4 時間後（cooldown_until = now+3h を超えた時刻）
        future = now + timedelta(hours=4)
        result = store.check_cooldown("user-1", future)
        assert result.active is False
        assert result.consecutive_refuses == 0

    def test_after_natural_release_resets_to_one(self, now: datetime) -> None:
        """自然解除後の最初の拒否で count=1（COOLDOWN-04 / M3-1）。"""
        store = LocalCooldownStore()
        future = now + timedelta(hours=4)
        result = store.increment_refuse_count(
            "user-1", future, after_natural_release=True
        )
        assert result.consecutive_refuses == 1
        assert result.cooldown_until is None

    def test_users_are_independent(self, now: datetime) -> None:
        """user-1 と user-2 のカウントは独立。"""
        store = LocalCooldownStore()
        store.increment_refuse_count("user-1", now)
        store.increment_refuse_count("user-1", now)

        result = store.check_cooldown("user-2", now)
        assert result.consecutive_refuses == 0


class TestLocalMemoryStore:
    """LocalMemoryStore の挙動（empty MemoryContext を返す）。"""

    async def test_build_memory_context_returns_empty(self) -> None:
        store = LocalMemoryStore()
        ctx = await store.build_memory_context("user-1")
        assert ctx.preferred_axis == "fact"  # PROMPT-CONFIG 既定値
        assert ctx.recent_debate_outcomes == []
        assert ctx.m1m2_axis_extracted == []

    async def test_record_event_does_not_raise(self) -> None:
        """ローカル record_event は例外を上げず、ログのみ。"""
        store = LocalMemoryStore()
        await store.record_event(
            actor_id="user-1",
            session_id="sess-1",
            axis="fact",
            outcome="agreed",
            turn=1,
        )


class TestSingletons:
    """get_local_cooldown_store / get_local_memory_store のシングルトン挙動。"""

    def test_cooldown_store_singleton(self) -> None:
        a = local_mode.get_local_cooldown_store()
        b = local_mode.get_local_cooldown_store()
        assert a is b

    def test_memory_store_singleton(self) -> None:
        a = local_mode.get_local_memory_store()
        b = local_mode.get_local_memory_store()
        assert a is b

    def test_reset_resets_singletons(self) -> None:
        a = local_mode.get_local_cooldown_store()
        reset_local_stores_for_testing()
        b = local_mode.get_local_cooldown_store()
        assert a is not b
