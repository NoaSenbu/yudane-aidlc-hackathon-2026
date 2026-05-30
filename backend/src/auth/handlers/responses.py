"""auth API ハンドラ共通のレスポンスヘルパ。

DomainError → ProblemDetails（Unit-1）の変換を API Gateway proxy response 形式にまとめる。
"""

from __future__ import annotations

import json
from typing import Any

from backend.src.common.exceptions import DomainError, to_problem_details


def json_response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    """JSON 成功レスポンスを返す。"""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def problem_response(error: DomainError) -> dict[str, Any]:
    """DomainError を RFC 7807 レスポンスに変換する（Unit-1 ERR-05 準拠）。"""
    return {
        "statusCode": error.status,
        "headers": {"Content-Type": "application/problem+json"},
        "body": json.dumps(to_problem_details(error)),
    }
