"""B-08 PreferenceVectorUpdater — 日次バッチ（ALG-PREF、PAT2-BATCH-01）。

日次で嗜好ベクトルを更新し、負債 72h クーリングオフの遅延評価も実行する（取りこぼし防止）。
集計の純ロジックは別関数に分離してテスト可能にする。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.src.auth.debt_safeguard import evaluate_debt_release
from backend.src.auth.models import SafeguardStateEntity
from backend.src.common.logging import AuditLogger

_LOGGER = AuditLogger(service="auth-preference-updater")


def merge_preference_labels(
    existing: list[str],
    signals: list[str],
    max_labels: int = 30,
) -> list[str]:
    """嗜好ラベルを更新する（純ロジック、ALG-PREF の簡易版）。

    既存ラベルと新シグナルを統合し、重複除去・上限 max_labels で打ち切る。

    Args:
        existing: 既存ラベル。
        signals: 新たな購買/スキップ由来のシグナルラベル。
        max_labels: 保持上限。

    Returns:
        更新後ラベル（新しいものを優先、上限まで）。
    """
    merged = list(dict.fromkeys([*signals, *existing]))
    return merged[:max_labels]


def evaluate_debt_for_user(
    state: SafeguardStateEntity,
    now: datetime,
) -> SafeguardStateEntity:
    """日次内で負債クーリングオフを遅延評価する（DEBT-05 取りこぼし防止）。"""
    return evaluate_debt_release(state, now)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ANN401, ARG001
    """日次バッチの Lambda ハンドラ（EventBridge cron）。"""
    # 実バッチでは全ユーザーを走査して update_preference / evaluate_debt を実行する。
    # 実装統合時に DynamoDB scan + 並列処理を結線する。
    _LOGGER.log("info", "daily preference batch invoked", {"source": "eventbridge"})
    _LOGGER.metric("auth.batch.daily_runs", 1, "Count", {})
    return {"status": "ok", "ranAt": datetime.now(UTC).isoformat()}
