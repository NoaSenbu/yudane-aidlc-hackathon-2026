"""POST /v1/amazon-transitions ハンドラの単体テスト（201 / 401 / 409 / 冪等）。"""

from __future__ import annotations

import json
from typing import Any

from backend.src.reel.handlers.transition import make_handler
from backend.src.reel.models import AmazonTransitionRequest

from safeguard_policy import SafeguardDecision


class _FakeGate:
    def __init__(self, decision: str, reason: str = "allowed") -> None:
        self._decision = decision
        self._reason = reason

    def evaluate(self, user_id: str) -> SafeguardDecision:
        return SafeguardDecision(
            decision=self._decision,  # type: ignore[arg-type]
            reason_code=self._reason,  # type: ignore[arg-type]
            effective_limit_yen=100_000,
            remaining_yen=50_000,
        )


class _FakeRepo:
    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.exp = 10

    def record_if_absent(self, req: AmazonTransitionRequest, month_bucket: str) -> bool:
        if req.client_transition_id in self.seen:
            return False
        self.seen.add(req.client_transition_id)
        return True

    def increment_exp(self, user_id: str, amount: int) -> int:
        self.exp += amount
        return self.exp

    def current_exp(self, user_id: str) -> int:
        return self.exp


def _event(*, sub: str | None = "u1", cid: str = "c1") -> dict[str, Any]:
    authorizer = {"claims": {"sub": sub}} if sub is not None else {}
    body = {"card_id": "card-1", "asin": "B0EXAMPLE1", "context": "reel", "client_transition_id": cid}
    return {"requestContext": {"authorizer": authorizer}, "body": json.dumps(body)}


def test_transition_201_awards_exp() -> None:
    """allow は 201 で EXP +1。"""
    h = make_handler(_FakeGate("allow"), _FakeRepo())
    res = h(_event(), None)
    assert res["statusCode"] == 201
    assert json.loads(res["body"])["awarded"] == 1


def test_transition_401_unauthenticated() -> None:
    """sub 無しは 401。"""
    h = make_handler(_FakeGate("allow"), _FakeRepo())
    res = h(_event(sub=None), None)
    assert res["statusCode"] == 401


def test_transition_409_on_safeguard_block() -> None:
    """Safeguard block は 409（記録しない）。"""
    h = make_handler(_FakeGate("block", "safeguard.monthly-limit-exceeded"), _FakeRepo())
    res = h(_event(), None)
    assert res["statusCode"] == 409
    body = json.loads(res["body"])
    assert body["status"] == 409
    assert "safeguard" in body["type"]


def test_transition_idempotent_duplicate() -> None:
    """同一 clientTransitionId の再送は duplicate=true / awarded=0。"""
    repo = _FakeRepo()
    h = make_handler(_FakeGate("allow"), repo)
    first = json.loads(h(_event(cid="dup"), None)["body"])
    second = json.loads(h(_event(cid="dup"), None)["body"])
    assert first["awarded"] == 1
    assert second["awarded"] == 0
    assert second["duplicate"] is True
