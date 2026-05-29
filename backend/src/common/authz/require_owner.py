"""require_owner デコレータ（PAT-SEC-01 / SECURITY-08 / IDOR 対策）。

API Gateway Lambda Authorizer が JWT を検証した後、各 Lambda の冒頭で
JWT claim の `sub` とパスパラメータの `userId` が一致することを検証する。
不一致は auth.idor（403）で fail-closed（REQ-04/05）。
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from backend.src.common.exceptions import DomainError, ErrorCategory

F = TypeVar("F", bound=Callable[..., Any])

# API Gateway proxy event の型は dict として扱う（生成モデルに依存しない）
ApiGatewayEvent = dict[str, Any]


def extract_sub(event: ApiGatewayEvent) -> str | None:
    """API Gateway イベントから JWT claim の sub を取り出す。

    Cognito Authorizer は `requestContext.authorizer.claims.sub` に格納する。

    Args:
        event: API Gateway proxy event。

    Returns:
        sub。取得できない場合は None。
    """
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
    except (KeyError, TypeError):
        return None
    sub = claims.get("sub")
    return sub if isinstance(sub, str) else None


def _path_user_id(event: ApiGatewayEvent) -> str | None:
    """パスパラメータ userId を取り出す。"""
    params = event.get("pathParameters") or {}
    user_id = params.get("userId")
    return user_id if isinstance(user_id, str) else None


def require_owner(handler: F) -> F:
    """ハンドラ冒頭で sub ↔ path userId の一致を強制するデコレータ。

    パスに `userId` が無いエンドポイントでは認証（sub 存在）のみ確認する。

    Raises:
        DomainError: 未認証（auth.unauthenticated, 401）/ 不一致（auth.idor, 403）。
    """

    @wraps(handler)
    def wrapper(event: ApiGatewayEvent, context: Any) -> Any:  # noqa: ANN401
        sub = extract_sub(event)
        if sub is None:
            raise DomainError(
                ErrorCategory.AUTH,
                "auth.unauthenticated",
                "JWT claim sub が存在しません",
                user_message="認証が必要です",
                status=401,
            )
        path_user_id = _path_user_id(event)
        if path_user_id is not None and path_user_id != sub:
            # IDOR: 他人の userId を指定（fail-closed）
            raise DomainError(
                ErrorCategory.AUTH,
                "auth.idor",
                f"sub と path userId が不一致: {sub} != {path_user_id}",
                user_message="このリソースにアクセスする権限がありません",
                status=403,
            )
        return handler(event, context)

    return wrapper  # type: ignore[return-value]
