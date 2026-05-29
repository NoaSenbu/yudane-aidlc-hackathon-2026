"""require_owner デコレータの単体テスト（SECURITY-08 / IDOR）。"""

from __future__ import annotations

from typing import Any

import pytest

from backend.src.common.authz import require_owner
from backend.src.common.exceptions import DomainError


def _event(sub: str | None, path_user_id: str | None) -> dict[str, Any]:
    event: dict[str, Any] = {"requestContext": {"authorizer": {"claims": {}}}}
    if sub is not None:
        event["requestContext"]["authorizer"]["claims"]["sub"] = sub
    if path_user_id is not None:
        event["pathParameters"] = {"userId": path_user_id}
    return event


@require_owner
def _handler(event: dict[str, Any], context: Any) -> str:  # noqa: ANN401, ARG001
    return "ok"


def test_allows_matching_sub() -> None:
    """sub と path userId が一致すれば通過。"""
    assert _handler(_event("user-1", "user-1"), None) == "ok"


def test_allows_when_no_path_user_id() -> None:
    """userId パスが無いエンドポイントは sub 存在のみ確認。"""
    assert _handler(_event("user-1", None), None) == "ok"


def test_blocks_unauthenticated() -> None:
    """sub が無ければ 401。"""
    with pytest.raises(DomainError) as exc:
        _handler(_event(None, "user-1"), None)
    assert exc.value.status == 401
    assert exc.value.code == "auth.unauthenticated"


def test_blocks_idor() -> None:
    """sub と path userId 不一致は 403 idor（fail-closed）。"""
    with pytest.raises(DomainError) as exc:
        _handler(_event("user-1", "user-2"), None)
    assert exc.value.status == 403
    assert exc.value.code == "auth.idor"
