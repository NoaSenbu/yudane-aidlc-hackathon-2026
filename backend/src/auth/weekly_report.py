"""B-08 — 週次集計バッチ（ALG-WEEKLY、PAT2-BATCH-01）。

北極星指標（論破→Amazon 遷移率等）を集計して WeeklyReports に出力する（services.md 経路）。
集計の純ロジックを分離してテスト可能にする。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.src.common.logging import AuditLogger

_LOGGER = AuditLogger(service="auth-weekly-report")


@dataclass(frozen=True)
class WeeklyMetricsInput:
    """週次集計の入力（CloudWatch Metrics / DynamoDB 由来）。"""

    debate_sessions: int
    debate_to_amazon_transitions: int
    cart_intercepts: int
    cart_conversions: int
    total_sessions: int
    late_night_sessions: int
    monthly_spend_yen: int


def compute_weekly_metrics(data: WeeklyMetricsInput) -> dict[str, float]:
    """北極星指標を算出する（§6.1、ゼロ除算は 0 を返す）。

    Args:
        data: 週次の生カウント。

    Returns:
        指標辞書（遷移率 / 成約率 / 深夜比率 / 支出）。
    """

    def _rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator > 0 else 0.0

    return {
        "debateToAmazonRate": _rate(data.debate_to_amazon_transitions, data.debate_sessions),
        "cartInterceptConversionRate": _rate(data.cart_conversions, data.cart_intercepts),
        "lateNightUsageRatio": _rate(data.late_night_sessions, data.total_sessions),
        "monthlySpendYen": float(data.monthly_spend_yen),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """週次バッチの Lambda ハンドラ（EventBridge cron、日曜 22 時）。"""
    _LOGGER.log("info", "weekly report batch invoked", {"source": "eventbridge"})
    _LOGGER.metric("auth.batch.weekly_runs", 1, "Count", {})
    return {"status": "ok", "ranAt": datetime.now(UTC).isoformat()}
