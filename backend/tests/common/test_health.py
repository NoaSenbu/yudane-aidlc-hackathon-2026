"""ヘルスチェックの単体テスト（PAT-RESIL-04 / NFR-AVAIL-01）。"""

from __future__ import annotations

from backend.src.common.health import evaluate_health


def test_all_ok_is_healthy() -> None:
    """全依存 ok なら healthy。"""
    status = evaluate_health({"dynamodb": lambda: True, "redis": lambda: True})
    assert status["status"] == "healthy"
    assert status["dependencies"] == {"dynamodb": "ok", "redis": "ok"}


def test_any_failure_is_degraded() -> None:
    """1 つでも失敗すれば degraded。"""
    status = evaluate_health({"dynamodb": lambda: True, "redis": lambda: False})
    assert status["status"] == "degraded"
    assert status["dependencies"]["redis"] == "error"


def test_exception_is_error() -> None:
    """プローブ例外は error 集約（落ちない）。"""

    def _boom() -> bool:
        raise RuntimeError("connection refused")

    status = evaluate_health({"redis": _boom})
    assert status["status"] == "degraded"
    assert status["dependencies"]["redis"] == "error"


def test_empty_checks_is_healthy() -> None:
    """チェックなしは healthy（土台のみ）。"""
    assert evaluate_health({})["status"] == "healthy"
