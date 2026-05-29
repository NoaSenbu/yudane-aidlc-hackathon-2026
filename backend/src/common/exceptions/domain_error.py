"""DomainError 体系（domain-entities.md §1 / business-rules.md ERR-01〜08）。

カテゴリ + コードの 2 階層（Q7=A）。API 境界では RFC 7807 ProblemDetails に変換する。
internal カテゴリは detail に内部情報を出さない（SECURITY-09 / ERR-05）。
"""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class ErrorCategory(str, Enum):
    """エラーカテゴリ（第1階層、ERR-02）。"""

    VALIDATION = "validation"
    AUTH = "auth"
    NOT_FOUND = "not-found"
    CONFLICT = "conflict"
    SAFEGUARD = "safeguard"
    EXTERNAL_API = "external-api"
    RATE_LIMIT = "rate-limit"
    INTERNAL = "internal"


# カテゴリ → 既定 HTTP ステータス（ERR-08）
_DEFAULT_STATUS: dict[ErrorCategory, int] = {
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.AUTH: 401,
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.SAFEGUARD: 409,
    ErrorCategory.EXTERNAL_API: 502,
    ErrorCategory.RATE_LIMIT: 429,
    ErrorCategory.INTERNAL: 500,
}

_ERROR_TYPE_BASE = "https://api.yudane.app/errors/"


class ProblemDetailsDict(TypedDict, total=False):
    """RFC 7807 ProblemDetails の辞書表現。"""

    type: str
    title: str
    status: int
    detail: str
    instance: str


class DomainError(Exception):
    """ドメインエラー（カテゴリ + コードの 2 階層）。

    Attributes:
        category: 第1階層カテゴリ。
        code: 第2階層コード（`<category>.<slug>` 形式）。
        message: 開発者向け内部メッセージ（ユーザー表示しない）。
        user_message: ユーザー表示用（任意、友達系トーン）。
        status: HTTP ステータス。未指定ならカテゴリ既定値。
        retryable: リトライ可能か（429/503 かつ冪等のみ true）。
    """

    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        *,
        user_message: str | None = None,
        status: int | None = None,
        retryable: bool = False,
        instance: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.user_message = user_message
        self.status = status if status is not None else _DEFAULT_STATUS[category]
        self.retryable = retryable
        self.instance = instance


def to_problem_details(error: DomainError) -> ProblemDetailsDict:
    """DomainError を RFC 7807 ProblemDetails に変換する（ERR-03/04/05）。

    internal カテゴリは detail に内部情報を出さず固定文言にする（SECURITY-09）。

    Args:
        error: 変換対象。

    Returns:
        ProblemDetails 辞書（API レスポンス body）。
    """
    problem: ProblemDetailsDict = {
        "type": f"{_ERROR_TYPE_BASE}{error.code}",
        "title": error.user_message or _safe_title(error),
        "status": error.status,
    }
    if error.category is not ErrorCategory.INTERNAL:
        # internal は detail を出さない（ERR-05）
        problem["detail"] = error.message
    if error.instance is not None:
        problem["instance"] = error.instance
    return problem


def _safe_title(error: DomainError) -> str:
    """ユーザー表示用タイトルの既定値（internal は汎用文言）。"""
    if error.category is ErrorCategory.INTERNAL:
        return "予期しないエラーが発生しました"
    return error.code
