"""GET /v1/reel ハンドラの単体テスト（200 / 401 / 400）。"""

from __future__ import annotations

import json
from typing import Any

from backend.src.reel.handlers.feed import handler


def _event(*, sub: str | None = "u1", query: dict[str, str] | None = None) -> dict[str, Any]:
    authorizer = {"claims": {"sub": sub}} if sub is not None else {}
    return {
        "requestContext": {"authorizer": authorizer},
        "queryStringParameters": query,
    }


def test_feed_200_returns_page() -> None:
    """認証済みはフィードページを 200 で返す。"""
    res = handler(_event(), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert "cards" in body
    assert isinstance(body["cards"], list)


def test_feed_401_when_unauthenticated() -> None:
    """sub 無しは 401（require_owner）。"""
    res = handler(_event(sub=None), None)
    assert res["statusCode"] == 401


def test_feed_400_on_bad_limit() -> None:
    """limit が範囲外なら 400。"""
    res = handler(_event(query={"limit": "999"}), None)
    assert res["statusCode"] == 400


def test_feed_400_on_non_numeric_limit() -> None:
    """limit が数値でなければ 400。"""
    res = handler(_event(query={"limit": "abc"}), None)
    assert res["statusCode"] == 400


def test_feed_cards_have_required_fields() -> None:
    """各カードに必須フィールド（label/pitch 同期確定）がある。"""
    res = handler(_event(), None)
    body = json.loads(res["body"])
    for card in body["cards"]:
        assert card["pitch"]
        assert card["ownership_label"]["text"]
        assert card["card_id"]
