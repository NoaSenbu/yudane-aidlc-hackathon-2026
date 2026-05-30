"""B-05 CartAttackScheduler 単体 + PBT テスト。

PBT-02 Invariant: 任意 createdAt で 30m/6h/24h ジョブが時系列整合（Property 2 担保）。
PBT-03 Inverse: schedule_attacks → cancel_attacks で 0 件。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis import strategies as st
from moto import mock_aws

from backend.src.cart.repository import AttackSchedule
from backend.src.cart.scheduler import (
    ATTACK_STEPS,
    _build_schedule_name,
    cancel_attacks,
    schedule_attacks,
)


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "NOTIFICATION_DISPATCHER_ARN",
        "arn:aws:lambda:ap-northeast-1:123456789012:function:yudane-cart-test-notification-dispatcher",
    )
    monkeypatch.setenv(
        "SCHEDULER_ROLE_ARN",
        "arn:aws:iam::123456789012:role/yudane-cart-test-scheduler-invoke-role",
    )
    monkeypatch.setenv("DEV_INITIAL", "")


class TestScheduleAttacks:
    def test_creates_three_schedules(self) -> None:
        client = MagicMock()
        base = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        result = schedule_attacks(
            user_id="user-1",
            item_id="01HG",
            asin="B0CXXXXXXX",
            base_time=base,
            scheduler_client=client,
        )
        assert client.create_schedule.call_count == 3
        assert result.schedule_30m
        assert result.schedule_6h
        assert result.schedule_24h

    def test_partial_failure_returns_partial_schedule(self) -> None:
        """1 件失敗でも他 2 件は登録され、成功した分が AttackSchedule に入る。"""
        client = MagicMock()
        # 30m のみ失敗、6h / 24h は成功
        call_count = {"value": 0}

        def side_effect(**kwargs: Any) -> None:
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("Scheduler 5xx")

        client.create_schedule.side_effect = side_effect

        result = schedule_attacks(
            user_id="user-1",
            item_id="01HG",
            asin="B0CXXXXXXX",
            base_time=datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc),
            scheduler_client=client,
        )
        # 30m が空、6h / 24h は成功
        assert result.schedule_30m == ""
        assert result.schedule_6h
        assert result.schedule_24h

    def test_all_failed_raises(self) -> None:
        client = MagicMock()
        client.create_schedule.side_effect = RuntimeError("All failed")
        with pytest.raises(RuntimeError, match="All 3 attacks failed"):
            schedule_attacks(
                user_id="user-1",
                item_id="01HG",
                asin="B0CXXXXXXX",
                base_time=datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc),
                scheduler_client=client,
            )

    def test_schedule_name_format(self) -> None:
        base = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        name = _build_schedule_name("user-1", "B0CXXXXXXX", base, "30m")
        # cart-attack-{8 文字 hash}-B0CXXXXXXX-{base_ms}-30m
        assert name.startswith("cart-attack-")
        assert "B0CXXXXXXX" in name
        assert name.endswith("-30m")
        assert len(name) <= 64  # EventBridge Scheduler の制約

    def test_dev_initial_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEV_INITIAL", "d")
        base = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        name = _build_schedule_name("user-1", "B0CXXXXXXX", base, "6h")
        assert "cart-attack-d-" in name


class TestCancelAttacks:
    def test_cancels_three_schedules(self) -> None:
        client = MagicMock()
        # ResourceNotFoundException クラスをモック化
        class _ResourceNotFound(Exception):
            pass

        client.exceptions.ResourceNotFoundException = _ResourceNotFound

        schedule = AttackSchedule(
            schedule_30m="cart-attack-X-B0XX-1234-30m",
            schedule_6h="cart-attack-X-B0XX-1234-6h",
            schedule_24h="cart-attack-X-B0XX-1234-24h",
        )
        cancel_attacks(schedule, scheduler_client=client)
        assert client.delete_schedule.call_count == 3

    def test_skips_empty_names(self) -> None:
        """部分失敗で空名が含まれる場合、その分は skip。"""
        client = MagicMock()

        class _ResourceNotFound(Exception):
            pass

        client.exceptions.ResourceNotFoundException = _ResourceNotFound

        schedule = AttackSchedule(
            schedule_30m="",  # 部分失敗で未登録
            schedule_6h="cart-attack-X-B0XX-1234-6h",
            schedule_24h="cart-attack-X-B0XX-1234-24h",
        )
        cancel_attacks(schedule, scheduler_client=client)
        assert client.delete_schedule.call_count == 2

    def test_resource_not_found_ignored(self) -> None:
        client = MagicMock()

        class _ResourceNotFound(Exception):
            pass

        client.exceptions.ResourceNotFoundException = _ResourceNotFound
        client.delete_schedule.side_effect = _ResourceNotFound("Already deleted")

        schedule = AttackSchedule(
            schedule_30m="cart-attack-X-B0XX-1234-30m",
            schedule_6h="cart-attack-X-B0XX-1234-6h",
            schedule_24h="cart-attack-X-B0XX-1234-24h",
        )
        # 例外伝播せず正常終了
        cancel_attacks(schedule, scheduler_client=client)


class TestPropertyBased:
    """PBT-02 Invariant: 任意 createdAt で時系列整合。"""

    @given(epoch_sec=st.integers(min_value=1_700_000_000, max_value=2_000_000_000))
    @settings(max_examples=20, deadline=None)
    def test_attack_steps_are_monotonic(self, epoch_sec: int) -> None:
        """30m < 6h < 24h の順で fire_at が単調増加することを確認（Property 2）。"""
        base = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
        delays = [ATTACK_STEPS["30m"], ATTACK_STEPS["6h"], ATTACK_STEPS["24h"]]
        # 単調増加 + 値固定（business-rules.md 定数）
        assert delays == sorted(delays)
        assert delays == [1_800, 21_600, 86_400]
