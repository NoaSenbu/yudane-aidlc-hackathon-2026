"""Cooldown DDB Adapter の PBT-03 不変条件プロパティ（Step 4.4 PBT 補強）。

PBT-03: 任意の actor_id / now で increment_refuse_count を 3 回呼ぶと必ず
        cooldown_until が SET される（COOLDOWN-02 不変条件）。
PBT-03': 自然解除後の最初の拒否で必ず consecutive_refuses == 1（COOLDOWN-04）。

参照: aidlc-docs/construction/unit-3-debate/nfr-requirements/nfr-requirements.md NFR-PBT-DEBATE-03
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import boto3
from botocore.stub import Stubber
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from backend.src.debate import cooldown

_TABLE_NAME = "yudane-debate-dev-cooldowns"

# 安全なタイムゾーン（UTC）の任意 datetime。極端な値は除外し、業務帯域に絞る
datetime_strategy = st.datetimes(
    min_value=datetime(2025, 1, 1).replace(tzinfo=None),
    max_value=datetime(2030, 12, 31).replace(tzinfo=None),
    timezones=st.just(UTC),
)
# actor_id は Cognito sub 形式（UUID 風）に近い任意の英数字
actor_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=8,
    max_size=36,
)


@given(actor_id=actor_id_strategy, now=datetime_strategy)
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_third_refuse_always_sets_cooldown_until(actor_id: str, now: datetime) -> None:
    """PBT-03: 任意の actor_id / now で 3 回目の拒否で必ず cooldown_until = now + 3h。

    実装パスを 1 stub で再現するのは複雑なので、3 回目の threshold 到達時の
    UpdateItem 呼び出しが「必ず cooldown_until = now + 3h を含む ExpressionAttributeValues
    で発行される」ことを property 化する。
    """
    # 1 回目の UpdateItem は ConditionalCheckFailedException で reject される（threshold 到達想定）
    # 2 回目の UpdateItem で threshold = 3 + cooldown_until = now + 3h を SET
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    stub = Stubber(client)
    stub.activate()

    cooldown_until = now + timedelta(hours=3)
    ttl_value = int((now + timedelta(days=30)).timestamp())

    stub.add_client_error(
        "update_item",
        service_error_code="ConditionalCheckFailedException",
        service_message="The conditional request failed",
    )
    stub.add_response(
        "update_item",
        {
            "Attributes": {
                "PK": {"S": f"USER#{actor_id}"},
                "SK": {"S": "COOLDOWN#current"},
                "consecutiveRefuses": {"N": "3"},
                "lastRefuseAt": {"S": now.isoformat()},
                "cooldownUntil": {"S": cooldown_until.isoformat()},
                "ttl": {"N": str(ttl_value)},
            }
        },
        expected_params={
            "TableName": _TABLE_NAME,
            "Key": {
                "PK": {"S": f"USER#{actor_id}"},
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
            actor_id=actor_id,
            now=now,
            table_name=_TABLE_NAME,
        )

    # 不変条件: 3 回目で必ず cooldown_until = now + 3h
    assert (
        result.consecutive_refuses == 3
    ), f"Expected consecutive_refuses=3 for actor_id={actor_id}, got {result.consecutive_refuses}"
    assert result.cooldown_until == cooldown_until, (
        f"Expected cooldown_until={cooldown_until} for actor_id={actor_id}, "
        f"got {result.cooldown_until}"
    )
    stub.assert_no_pending_responses()
    stub.deactivate()


@given(actor_id=actor_id_strategy, now=datetime_strategy)
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_natural_release_always_resets_to_one(actor_id: str, now: datetime) -> None:
    """PBT-03': 自然解除後の最初の拒否で必ず consecutive_refuses == 1（COOLDOWN-04 / M3-1）。"""
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    stub = Stubber(client)
    stub.activate()

    ttl_value = int((now + timedelta(days=30)).timestamp())

    stub.add_response(
        "update_item",
        {
            "Attributes": {
                "PK": {"S": f"USER#{actor_id}"},
                "SK": {"S": "COOLDOWN#current"},
                "consecutiveRefuses": {"N": "1"},
                "lastRefuseAt": {"S": now.isoformat()},
                "ttl": {"N": str(ttl_value)},
            }
        },
        expected_params={
            "TableName": _TABLE_NAME,
            "Key": {
                "PK": {"S": f"USER#{actor_id}"},
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
            actor_id=actor_id,
            now=now,
            table_name=_TABLE_NAME,
            after_natural_release=True,
        )

    # 不変条件: 自然解除後 → 必ず 1 にリセット
    assert result.consecutive_refuses == 1, (
        f"Expected consecutive_refuses=1 after natural release for actor_id={actor_id}, "
        f"got {result.consecutive_refuses}"
    )
    assert result.cooldown_until is None, (
        f"Expected cooldown_until=None after natural release for actor_id={actor_id}, "
        f"got {result.cooldown_until}"
    )
    stub.assert_no_pending_responses()
    stub.deactivate()
