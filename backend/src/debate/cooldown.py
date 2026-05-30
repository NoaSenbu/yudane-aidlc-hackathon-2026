"""LC-D-06 Cooldown DDB Adapter（Phase 1 Step 4.2 Green）。

DDB `yudane-debate-<env>-cooldowns` の CRUD 操作 + 自然解除リセット + COOLDOWN-02 / 04 不変条件。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §2 COOLDOWN
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-logic-model.md ALG-COOLDOWN-CHECK / ALG-COOLDOWN-INC
参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §4

不変条件:
    - consecutive_refuses == 3 に達した瞬間に必ず cooldown_until = now + 3h（PBT-03）
    - 自然解除後の最初の拒否で consecutive_refuses = 1（COOLDOWN-04 / M3-1）
    - ttl == int((now + 30d).timestamp())
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.src.debate.domain.results import CooldownDecision, CooldownState

_LOGGER = logging.getLogger(__name__)
_REGION = "ap-northeast-1"

#: COOLDOWN-CONFIG（business-rules.md §2 に整合）
COOLDOWN_TRIGGER_THRESHOLD = 3
COOLDOWN_DURATION_SECONDS = 3 * 60 * 60  # 3 hours
COOLDOWN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


@lru_cache(maxsize=1)
def _ddb_client() -> Any:
    """DynamoDB クライアントを 1 回だけ生成する（Lambda コールドスタート最適化）。"""
    return boto3.client("dynamodb", region_name=_REGION)


def _build_key(actor_id: str) -> dict[str, dict[str, str]]:
    """Cooldowns DDB の Composite Key（PK + SK）を構築する。"""
    return {
        "PK": {"S": f"USER#{actor_id}"},
        "SK": {"S": "COOLDOWN#current"},
    }


def check_cooldown(
    actor_id: str,
    now: datetime,
    table_name: str,
) -> CooldownDecision:
    """ALG-COOLDOWN-CHECK: ユーザーの現在のクールダウン状態を判定する（純関数）。

    Args:
        actor_id: Cognito JWT.sub（PAT-D-SEC-01）。
        now: 現在時刻（テスト容易性のため引数化、UTC 推奨）。
        table_name: DDB テーブル名（環境変数 COOLDOWNS_TABLE_NAME と一致）。

    Returns:
        CooldownDecision:
            - active=False: クールダウン未発動（レコードなし or 自然解除済み）
            - active=True:  クールダウン中、cooldown_until に解除時刻
        自然解除（cooldown_until <= now）の場合は active=False, consecutive_refuses=0 として返す
        （COOLDOWN-04 / M3-1）。実際の DDB リセットは increment_refuse_count(after_natural_release=True) で実施。
    """
    client = _ddb_client()
    response = client.get_item(
        TableName=table_name,
        Key=_build_key(actor_id),
        ConsistentRead=True,
    )
    item = response.get("Item")
    if item is None:
        return CooldownDecision(
            active=False, cooldown_until=None, consecutive_refuses=0
        )

    state = _parse_cooldown_state(item)

    if state.cooldown_until is None:
        # クールダウン未発動だが、レコード自体は存在（連続拒否カウント途中）
        return CooldownDecision(
            active=False,
            cooldown_until=None,
            consecutive_refuses=state.consecutive_refuses,
        )

    if state.cooldown_until <= now:
        # 自然解除済み（cooldown_until 期限切れ）→ COOLDOWN-04: 次回拒否で 1 にリセット表示
        return CooldownDecision(
            active=False, cooldown_until=None, consecutive_refuses=0
        )

    # まだクールダウン中
    return CooldownDecision(
        active=True,
        cooldown_until=state.cooldown_until,
        consecutive_refuses=state.consecutive_refuses,
    )


def increment_refuse_count(
    actor_id: str,
    now: datetime,
    table_name: str,
    *,
    after_natural_release: bool = False,
) -> CooldownState:
    """ALG-COOLDOWN-INC: 拒否カウントをインクリメントする。

    3 回目の拒否で必ず cooldown_until = now + 3h を SET（COOLDOWN-02、PBT-03 不変条件）。
    自然解除後の場合は consecutive_refuses を 1 に直接リセット（COOLDOWN-04 / M3-1）。

    Args:
        actor_id: Cognito JWT.sub。
        now: 現在時刻。
        table_name: DDB テーブル名。
        after_natural_release: True なら自然解除後の最初の拒否として 1 にリセット。
            呼び出し側は事前に check_cooldown で自然解除を確認すること。

    Returns:
        更新後の CooldownState。
    """
    client = _ddb_client()
    ttl_value = int((now + timedelta(days=30)).timestamp())
    cooldown_until = now + timedelta(hours=3)

    if after_natural_release:
        # 自然解除後 → consecutive_refuses=1 / cooldown_until を REMOVE（COOLDOWN-04）
        response = client.update_item(
            TableName=table_name,
            Key=_build_key(actor_id),
            UpdateExpression=(
                "SET consecutiveRefuses = :one, lastRefuseAt = :now, #ttl = :ttl "
                "REMOVE cooldownUntil"
            ),
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={
                ":one": {"N": "1"},
                ":now": {"S": now.isoformat()},
                ":ttl": {"N": str(ttl_value)},
            },
            ReturnValues="ALL_NEW",
        )
        return _parse_cooldown_state(response["Attributes"])

    # 通常パス: +1 加算（threshold 未満なら ConditionalCheck pass）
    try:
        response = client.update_item(
            TableName=table_name,
            Key=_build_key(actor_id),
            UpdateExpression=(
                "SET consecutiveRefuses = if_not_exists(consecutiveRefuses, :zero) + :one, "
                "lastRefuseAt = :now, #ttl = :ttl"
            ),
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={
                ":zero": {"N": "0"},
                ":one": {"N": "1"},
                ":now": {"S": now.isoformat()},
                ":ttl": {"N": str(ttl_value)},
                ":threshold": {"N": str(COOLDOWN_TRIGGER_THRESHOLD)},
                ":cooldown_until": {"S": cooldown_until.isoformat()},
            },
            ConditionExpression=(
                "attribute_not_exists(consecutiveRefuses) OR "
                "consecutiveRefuses + :one < :threshold"
            ),
            ReturnValues="ALL_NEW",
        )
        return _parse_cooldown_state(response["Attributes"])
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            _LOGGER.error("cooldown_update_unexpected_error", extra={"error": str(exc)})
            raise

    # threshold 到達: cooldown_until を SET（COOLDOWN-02 / PBT-03 不変条件）
    response = client.update_item(
        TableName=table_name,
        Key=_build_key(actor_id),
        UpdateExpression=(
            "SET consecutiveRefuses = :threshold, lastRefuseAt = :now, "
            "cooldownUntil = :cooldown_until, #ttl = :ttl"
        ),
        ExpressionAttributeNames={"#ttl": "ttl"},
        ExpressionAttributeValues={
            ":threshold": {"N": str(COOLDOWN_TRIGGER_THRESHOLD)},
            ":now": {"S": now.isoformat()},
            ":cooldown_until": {"S": cooldown_until.isoformat()},
            ":ttl": {"N": str(ttl_value)},
        },
        ReturnValues="ALL_NEW",
    )
    return _parse_cooldown_state(response["Attributes"])


def _parse_cooldown_state(item: dict[str, Any]) -> CooldownState:
    """DDB low-level item を CooldownState に変換する。

    DDB の low-level 形式（`{"S": "..."}` / `{"N": "..."}`）を Python 型に変換し、
    Pydantic alias で CooldownState インスタンス化。
    """
    raw: dict[str, Any] = {
        "PK": item["PK"]["S"],
        "SK": item["SK"]["S"],
        "consecutiveRefuses": int(item["consecutiveRefuses"]["N"]),
        "lastRefuseAt": item["lastRefuseAt"]["S"],
        "ttl": int(item["ttl"]["N"]),
    }
    if "cooldownUntil" in item:
        raw["cooldownUntil"] = item["cooldownUntil"]["S"]
    return CooldownState.model_validate(raw)
