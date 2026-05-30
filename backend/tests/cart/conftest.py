"""Unit-5 Cart Intercept のテスト共通 fixture。

moto + DynamoDB Local（in-memory）で AWS リソースをモックし、Backend Lambda を統合テスト可能にする。
Unit-1 `backend/conftest.py` の sys.path 設定を継承（リポジトリルートを sys.path に追加済み）。

2026-05-29 Issue Z1 修正: 1 つの mock_aws() context を全 fixture で共有することで、
複数テーブルを同時に使うテストでの moto context 分離問題を解消。
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """moto がデフォルト credentials を要求するため、ダミー値を環境変数で注入する。"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")


@pytest.fixture
def cart_watch_items_table_name() -> str:
    return "yudane-cart-test-watch-items"


@pytest.fixture
def notification_logs_table_name() -> str:
    return "yudane-cart-test-notification-logs"


@pytest.fixture
def aws_mock() -> Iterator[None]:
    """テスト関数毎に 1 つの moto context を起動し、関連 fixture が共有する。

    Issue Z1 修正: 各テーブル fixture が個別に `with mock_aws():` を持つと、
    複数テーブルを同時に使うテストで context が分離する問題があった。
    本 fixture を依存先として使うことで、同一 context を保証する。
    """
    with mock_aws():
        yield


@pytest.fixture
def cart_watch_items_table(
    aws_mock: None,  # noqa: ARG001
    cart_watch_items_table_name: str,
) -> Any:
    """CartWatchItems テーブルを moto 上に作成する。

    PK / SK / GSI1 のスキーマは
    `aidlc-docs/construction/unit-5-cart-intercept/functional-design/data-model.md` §1 に整合。
    """
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    client.create_table(
        TableName=cart_watch_items_table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1-status-createdAt",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    os.environ["CART_WATCH_ITEMS_TABLE"] = cart_watch_items_table_name
    return boto3.resource("dynamodb", region_name="ap-northeast-1").Table(
        cart_watch_items_table_name,
    )


@pytest.fixture
def notification_logs_table(
    aws_mock: None,  # noqa: ARG001
    notification_logs_table_name: str,
) -> Any:
    """NotificationLogs テーブルを moto 上に作成する。"""
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    client.create_table(
        TableName=notification_logs_table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "cartWatchItemId", "AttributeType": "S"},
            {"AttributeName": "sentAt", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1-cartWatchItemId",
                "KeySchema": [
                    {"AttributeName": "cartWatchItemId", "KeyType": "HASH"},
                    {"AttributeName": "sentAt", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    os.environ["NOTIFICATION_LOGS_TABLE"] = notification_logs_table_name
    return boto3.resource("dynamodb", region_name="ap-northeast-1").Table(
        notification_logs_table_name,
    )
