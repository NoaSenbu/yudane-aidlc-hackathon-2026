"""B-04 Lambda Handler 単体テスト（cart_intake / cart_dismiss / cart_list / push_token）。

Validates: NFR-PBT-04 (Idempotency) / Property 1 (重複登録の冪等性) / Property 6 (件数上限) /
PBT-08-local（ロジック単体 latency < 100ms 想定）。
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.src.cart.handlers.cart_dismiss import dismiss_lambda_handler
from backend.src.cart.handlers.cart_intake import lambda_handler as intake_handler
from backend.src.cart.handlers.cart_list import list_lambda_handler


def _api_event(
    *,
    user_id: str = "user-1",
    body: dict[str, Any] | None = None,
    path_params: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "requestContext": {"authorizer": {"claims": {"sub": user_id}}},
        "body": json.dumps(body) if body else None,
        "pathParameters": path_params,
        "queryStringParameters": query_params,
        "headers": {},
    }


@pytest.fixture(autouse=True)
def env_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_DUMMY_CATALOG", "true")
    monkeypatch.setenv(
        "NOTIFICATION_DISPATCHER_ARN",
        "arn:aws:lambda:ap-northeast-1:123456789012:function:test",
    )
    monkeypatch.setenv("SCHEDULER_ROLE_ARN", "arn:aws:iam::123456789012:role/test")
    monkeypatch.setenv("DEV_INITIAL", "")


class TestCartIntake:
    def test_invalid_request_body_returns_400(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        event = _api_event(body={"url": "not-a-url"})  # asin 欠落
        result = intake_handler(event, None)
        assert result["statusCode"] == 400

    def test_invalid_asin_format_returns_400(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        event = _api_event(body={"url": "https://www.amazon.co.jp/dp/B0CXXXXXXX", "asin": "invalid"})
        result = intake_handler(event, None)
        assert result["statusCode"] == 400

    @patch("backend.src.cart.handlers.cart_intake.schedule_attacks")
    def test_creates_new_watch_item(self, mock_schedule, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        from backend.src.cart.repository import AttackSchedule

        mock_schedule.return_value = AttackSchedule(
            schedule_30m="cart-attack-X-B0CXXXXXXX-1234-30m",
            schedule_6h="cart-attack-X-B0CXXXXXXX-1234-6h",
            schedule_24h="cart-attack-X-B0CXXXXXXX-1234-24h",
        )
        event = _api_event(
            body={"url": "https://www.amazon.co.jp/dp/B0CXXXXXXX", "asin": "B0CXXXXXXX"}
        )
        result = intake_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["isNewlyCreated"] is True
        assert body["item"]["asin"] == "B0CXXXXXXX"
        assert body["item"]["status"] == "watching"

    @patch("backend.src.cart.handlers.cart_intake.schedule_attacks")
    def test_duplicate_watching_returns_existing_200(
        self, mock_schedule, cart_watch_items_table  # type: ignore[no-untyped-def]
    ) -> None:
        from backend.src.cart.repository import AttackSchedule

        mock_schedule.return_value = AttackSchedule(
            schedule_30m="x", schedule_6h="y", schedule_24h="z"
        )
        event = _api_event(
            body={"url": "https://www.amazon.co.jp/dp/B0CXXXXXXX", "asin": "B0CXXXXXXX"}
        )
        # 1 回目: 201
        intake_handler(event, None)
        # 2 回目: 200 + isNewlyCreated=false
        result = intake_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["isNewlyCreated"] is False

    def test_dummy_catalog_404_when_unknown_asin(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        event = _api_event(
            body={"url": "https://www.amazon.co.jp/dp/B0XXXX9999", "asin": "B0XXXX9999"}
        )
        result = intake_handler(event, None)
        assert result["statusCode"] == 404

    @patch("backend.src.cart.handlers.cart_intake.schedule_attacks")
    def test_property_6_limit_returns_429(
        self, mock_schedule, cart_watch_items_table  # type: ignore[no-untyped-def]
    ) -> None:
        """Property 6 / SECURITY-15: active 100 件超過で 429。"""
        from backend.src.cart.repository import AttackSchedule, CartWatchItemsRepo, ProductMeta

        mock_schedule.return_value = AttackSchedule(
            schedule_30m="x", schedule_6h="y", schedule_24h="z"
        )
        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        # 100 件 watching を事前作成
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(100):
            asin = f"B0FILL{i:04d}"
            repo.create("user-1", asin, f"01HG{i}", ProductMeta("title", 100), "watching", now)

        # 101 件目で 429
        event = _api_event(
            body={"url": "https://www.amazon.co.jp/dp/B0CXXXXXXX", "asin": "B0CXXXXXXX"}
        )
        result = intake_handler(event, None)
        assert result["statusCode"] == 429


class TestCartDismiss:
    def test_invalid_asin_returns_400(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        event = _api_event(path_params={"asin": "invalid"})
        result = dismiss_lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_not_found_returns_404(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        # ASIN は 10 文字必須（正規表現 ^[A-Z0-9]{10}$）。存在しないが妥当な形式の ASIN を使う。
        event = _api_event(path_params={"asin": "B0NOTEXIST"})
        result = dismiss_lambda_handler(event, None)
        assert result["statusCode"] == 404

    @patch("backend.src.cart.handlers.cart_dismiss.cancel_attacks")
    def test_dismiss_watching_returns_204(
        self, mock_cancel, cart_watch_items_table  # type: ignore[no-untyped-def]
    ) -> None:
        from backend.src.cart.repository import CartWatchItemsRepo, ProductMeta

        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        repo.create("user-1", "B0CXXXXXXX", "01HG", ProductMeta("title", 100), "watching", now)

        event = _api_event(path_params={"asin": "B0CXXXXXXX"})
        result = dismiss_lambda_handler(event, None)
        assert result["statusCode"] == 204

    def test_already_dismissed_idempotent_204(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        from backend.src.cart.repository import CartWatchItemsRepo, ProductMeta

        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        repo.create("user-1", "B0CXXXXXXX", "01HG", ProductMeta("title", 100), "watching", now)
        repo.transition_to_dismissed("user-1", "B0CXXXXXXX")

        event = _api_event(path_params={"asin": "B0CXXXXXXX"})
        result = dismiss_lambda_handler(event, None)
        assert result["statusCode"] == 204  # 冪等返却


class TestCartList:
    def test_invalid_asin_path_returns_400(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        event = _api_event(path_params={"asin": "invalid"})
        result = list_lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_get_single_item(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        from backend.src.cart.repository import CartWatchItemsRepo, ProductMeta

        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        repo.create("user-1", "B0CXXXXXXX", "01HG", ProductMeta("title", 100), "watching", now)

        event = _api_event(path_params={"asin": "B0CXXXXXXX"})
        result = list_lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["asin"] == "B0CXXXXXXX"

    def test_list_active_filter(self, cart_watch_items_table) -> None:  # type: ignore[no-untyped-def]
        from backend.src.cart.repository import CartWatchItemsRepo, ProductMeta

        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        repo.create("user-1", "B0AAAA0001", "01HG1", ProductMeta("t", 100), "watching", now)
        repo.create("user-1", "B0AAAA0002", "01HG2", ProductMeta("t", 100), "watching", now)
        repo.transition_to_dismissed("user-1", "B0AAAA0002")

        event = _api_event(query_params={"status": "active"})
        result = list_lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["items"]) == 1  # dismissed は除外
        assert body["items"][0]["asin"] == "B0AAAA0001"


class TestPushToken:
    """push_token は Users テーブル + EUM 依存のため最小バリデーション のみテスト。"""

    def test_invalid_request_body(self) -> None:
        from backend.src.cart.handlers.push_token import register_lambda_handler

        event = _api_event(body={"token": "", "platform": "INVALID"})
        result = register_lambda_handler(event, None)
        assert result["statusCode"] == 400


class TestPropertyBasedLatency:
    """PBT-08-local: ロジック単体 latency < 100ms 想定（AWS Mock 上の計測）。"""

    @patch("backend.src.cart.handlers.cart_intake.schedule_attacks")
    def test_intake_latency_local(
        self, mock_schedule, cart_watch_items_table  # type: ignore[no-untyped-def]
    ) -> None:
        from backend.src.cart.repository import AttackSchedule

        mock_schedule.return_value = AttackSchedule(
            schedule_30m="x", schedule_6h="y", schedule_24h="z"
        )
        event = _api_event(
            body={"url": "https://www.amazon.co.jp/dp/B0CXXXXXXX", "asin": "B0CXXXXXXX"}
        )
        start = time.perf_counter()
        intake_handler(event, None)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 1_000, f"Intake handler too slow: {elapsed_ms}ms"  # CI 環境余裕で 1s
