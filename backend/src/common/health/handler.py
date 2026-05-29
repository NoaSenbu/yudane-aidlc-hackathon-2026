"""ヘルスチェック Lambda（GET /v1/health、PAT-RESIL-04 / NFR-AVAIL-01）。

依存サービス（DynamoDB / Redis）の浅い疎通を返す。Q6=B によりサーキットブレーカ等は
持たず、状態の可視化に責務を限定する。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any


def evaluate_health(checks: Mapping[str, Callable[[], bool]]) -> dict[str, Any]:
    """依存チェックを実行して HealthStatus 辞書を返す。

    Args:
        checks: 依存名 → 疎通関数（True=ok）。例外は error 扱い。

    Returns:
        HealthStatus 辞書（status / checkedAt / dependencies）。
    """
    dependencies: dict[str, str] = {}
    healthy = True
    for name, probe in checks.items():
        try:
            ok = probe()
        except Exception:  # noqa: BLE001 - ヘルスチェックは全例外を error 集約
            ok = False
        dependencies[name] = "ok" if ok else "error"
        if not ok:
            healthy = False
    return {
        "status": "healthy" if healthy else "degraded",
        "checkedAt": datetime.now(UTC).isoformat(),
        "dependencies": dependencies,
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """ヘルスチェックの Lambda ハンドラ。

    実際の依存プローブ（DynamoDB/Redis）は Infrastructure 層から注入する想定。
    本実装では疎通土台のみ提供し、空チェック時は healthy を返す。
    """
    status = evaluate_health({})
    code = 200 if status["status"] == "healthy" else 503
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(status),
    }
