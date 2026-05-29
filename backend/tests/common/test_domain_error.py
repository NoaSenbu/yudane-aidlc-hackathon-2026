"""DomainError → ProblemDetails 変換の単体テスト（ERR-03/04/05）。"""

from __future__ import annotations

from backend.src.common.exceptions import (
    DomainError,
    ErrorCategory,
    to_problem_details,
)


def test_problem_type_url_from_code() -> None:
    """type は code を URL 化したもの（ERR-04）。"""
    err = DomainError(
        ErrorCategory.SAFEGUARD,
        "safeguard.cooldown",
        "クールダウン中",
        user_message="論破クールダウン中です",
    )
    problem = to_problem_details(err)
    assert problem["type"] == "https://api.yudane.app/errors/safeguard.cooldown"
    assert problem["status"] == 409
    assert problem["title"] == "論破クールダウン中です"
    assert problem["detail"] == "クールダウン中"


def test_internal_hides_detail() -> None:
    """internal は detail を出さず汎用文言（ERR-05 / SECURITY-09）。"""
    err = DomainError(
        ErrorCategory.INTERNAL,
        "internal.unexpected",
        "stack trace with secrets",
    )
    problem = to_problem_details(err)
    assert problem["status"] == 500
    assert "detail" not in problem
    assert problem["title"] == "予期しないエラーが発生しました"


def test_default_status_by_category() -> None:
    """カテゴリ既定ステータスが適用される（ERR-08）。"""
    err = DomainError(ErrorCategory.NOT_FOUND, "not-found.resource", "なし")
    assert to_problem_details(err)["status"] == 404
