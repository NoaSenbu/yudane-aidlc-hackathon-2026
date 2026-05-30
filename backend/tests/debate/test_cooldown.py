"""Unit-3 Debate Cooldown DDB Adapter のテスト（Phase 1 Step 4.1 Red）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 4
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §2 COOLDOWN
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import boto3
import pytest
from botocore.stub import Stubber

from backend.src.debate import cooldown


@pytest.fixture
def ddb_client_stub() -> tuple[object, Stubber]:
    """boto3 DynamoDB クライアントを Stubber でモックする。"""
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    stub = Stubber(client)
    stub.activate()
    return client, stub


@pytest.fixture
def now() -> datetime:
    """テスト用の現在時刻。"""
    return datetime(2026, 5, 30, 12, 0, 0, tzinfo=UTC)


def _table_name() -> str:
    """テスト用 DDB テーブル名（環境変数 COOLDOWNS_TABLE_NAME と合わせる）。"""
    return "yudane-debate-dev-cooldowns"


class TestCheckCooldown:
    """`check_cooldown` の挙動を検証する。"""

    def test_returns_inactive_when_no_record_exists(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """DDB GetItem で空 → 非クールダウン (active=False, consecutive_refuses=0)。"""
        client, stub = ddb_client_stub
        stub.add_response(
            "get_item",
            {},  # レコードなし
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "ConsistentRead": True,
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.check_cooldown(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
            )

        assert result.active is False
        assert result.consecutive_refuses == 0
        assert result.cooldown_until is None
        stub.assert_no_pending_responses()

    def test_returns_active_when_cooldown_until_in_future(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """cooldownUntil > now でクールダウン中（active=True）。"""
        client, stub = ddb_client_stub
        future = now + timedelta(hours=1)
        stub.add_response(
            "get_item",
            {
                "Item": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                    "consecutiveRefuses": {"N": "3"},
                    "lastRefuseAt": {"S": now.isoformat()},
                    "cooldownUntil": {"S": future.isoformat()},
                    "ttl": {"N": str(int((now + timedelta(days=30)).timestamp()))},
                }
            },
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "ConsistentRead": True,
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.check_cooldown(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
            )

        assert result.active is True
        assert result.consecutive_refuses == 3
        assert result.cooldown_until == future
        stub.assert_no_pending_responses()

    def test_returns_inactive_after_natural_release(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """cooldownUntil <= now（自然解除）→ active=False, consecutive_refuses=0（COOLDOWN-04）。"""
        client, stub = ddb_client_stub
        past = now - timedelta(minutes=1)
        stub.add_response(
            "get_item",
            {
                "Item": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                    "consecutiveRefuses": {"N": "3"},
                    "lastRefuseAt": {"S": (past - timedelta(hours=3)).isoformat()},
                    "cooldownUntil": {"S": past.isoformat()},
                    "ttl": {"N": str(int((now + timedelta(days=30)).timestamp()))},
                }
            },
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "ConsistentRead": True,
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.check_cooldown(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
            )

        # 自然解除：active=False、consecutive_refuses=0 でリセット表示（COOLDOWN-04 / M3-1 修正）
        assert result.active is False
        assert result.consecutive_refuses == 0
        assert result.cooldown_until is None
        stub.assert_no_pending_responses()


class TestIncrementRefuseCount:
    """`increment_refuse_count` の挙動を検証する（COOLDOWN-02 / 04 / PBT-03 重点）。"""

    def test_first_refuse_sets_count_to_one(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """初回拒否で consecutiveRefuses=1（cooldownUntil 未設定）。"""
        client, stub = ddb_client_stub
        ttl_value = int((now + timedelta(days=30)).timestamp())
        stub.add_response(
            "update_item",
            {
                "Attributes": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                    "consecutiveRefuses": {"N": "1"},
                    "lastRefuseAt": {"S": now.isoformat()},
                    "ttl": {"N": str(ttl_value)},
                }
            },
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "UpdateExpression": (
                    "SET consecutiveRefuses = if_not_exists(consecutiveRefuses, :zero) + :one, "
                    "lastRefuseAt = :now, #ttl = :ttl"
                ),
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": {
                    ":zero": {"N": "0"},
                    ":one": {"N": "1"},
                    ":now": {"S": now.isoformat()},
                    ":ttl": {"N": str(ttl_value)},
                    ":threshold": {"N": "3"},
                    ":cooldown_until": {"S": (now + timedelta(hours=3)).isoformat()},
                },
                "ConditionExpression": (
                    "attribute_not_exists(consecutiveRefuses) OR "
                    "consecutiveRefuses + :one < :threshold"
                ),
                "ReturnValues": "ALL_NEW",
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.increment_refuse_count(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
            )

        assert result.consecutive_refuses == 1
        assert result.cooldown_until is None
        stub.assert_no_pending_responses()

    def test_third_refuse_triggers_cooldown(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """3 回目の拒否で必ず cooldownUntil = now + 3h（COOLDOWN-02 / PBT-03 不変条件）。

        実装は ConditionalCheckFailedException を ConditionExpression で受け、
        threshold 到達ブランチで cooldownUntil を SET する 2 段クエリ構成。
        """
        client, stub = ddb_client_stub
        ttl_value = int((now + timedelta(days=30)).timestamp())
        cooldown_until = now + timedelta(hours=3)

        # 1. 1 回目の UpdateItem は ConditionalCheckFailedException で reject される
        stub.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            service_message="The conditional request failed",
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "UpdateExpression": (
                    "SET consecutiveRefuses = if_not_exists(consecutiveRefuses, :zero) + :one, "
                    "lastRefuseAt = :now, #ttl = :ttl"
                ),
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": {
                    ":zero": {"N": "0"},
                    ":one": {"N": "1"},
                    ":now": {"S": now.isoformat()},
                    ":ttl": {"N": str(ttl_value)},
                    ":threshold": {"N": "3"},
                    ":cooldown_until": {"S": cooldown_until.isoformat()},
                },
                "ConditionExpression": (
                    "attribute_not_exists(consecutiveRefuses) OR "
                    "consecutiveRefuses + :one < :threshold"
                ),
                "ReturnValues": "ALL_NEW",
            },
        )
        # 2. threshold 到達時の UpdateItem（cooldownUntil を SET）
        stub.add_response(
            "update_item",
            {
                "Attributes": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                    "consecutiveRefuses": {"N": "3"},
                    "lastRefuseAt": {"S": now.isoformat()},
                    "cooldownUntil": {"S": cooldown_until.isoformat()},
                    "ttl": {"N": str(ttl_value)},
                }
            },
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "UpdateExpression": (
                    "SET consecutiveRefuses = :threshold, lastRefuseAt = :now, "
                    "cooldownUntil = :cooldown_until, #ttl = :ttl"
                ),
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": {
                    ":threshold": {"N": "3"},
                    ":now": {"S": now.isoformat()},
                    ":cooldown_until": {"S": cooldown_until.isoformat()},
                    ":ttl": {"N": str(ttl_value)},
                },
                "ReturnValues": "ALL_NEW",
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.increment_refuse_count(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
            )

        assert result.consecutive_refuses == 3
        assert result.cooldown_until == cooldown_until
        stub.assert_no_pending_responses()

    def test_natural_release_resets_to_one(
        self,
        ddb_client_stub: tuple[object, Stubber],
        now: datetime,
    ) -> None:
        """自然解除後の最初の拒否で consecutiveRefuses = 1 にリセット（COOLDOWN-04 / M3-1）。

        実装方針: increment_refuse_count は事前に check_cooldown で自然解除を確認したうえで、
        自然解除時は通常の +1 加算ではなく **値を 1 に直接 SET** する。
        """
        client, stub = ddb_client_stub
        ttl_value = int((now + timedelta(days=30)).timestamp())

        # check_cooldown で得た「自然解除済み」フラグを呼び出し側が伝達する想定
        # increment_refuse_count(after_natural_release=True) で SET を直接実行
        stub.add_response(
            "update_item",
            {
                "Attributes": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                    "consecutiveRefuses": {"N": "1"},
                    "lastRefuseAt": {"S": now.isoformat()},
                    "ttl": {"N": str(ttl_value)},
                }
            },
            expected_params={
                "TableName": _table_name(),
                "Key": {
                    "PK": {"S": "USER#user-1"},
                    "SK": {"S": "COOLDOWN#current"},
                },
                "UpdateExpression": (
                    "SET consecutiveRefuses = :one, lastRefuseAt = :now, #ttl = :ttl "
                    "REMOVE cooldownUntil"
                ),
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": {
                    ":one": {"N": "1"},
                    ":now": {"S": now.isoformat()},
                    ":ttl": {"N": str(ttl_value)},
                },
                "ReturnValues": "ALL_NEW",
            },
        )

        with patch.object(cooldown, "_ddb_client", return_value=client):
            result = cooldown.increment_refuse_count(
                actor_id="user-1",
                now=now,
                table_name=_table_name(),
                after_natural_release=True,
            )

        assert result.consecutive_refuses == 1
        assert result.cooldown_until is None
        stub.assert_no_pending_responses()
