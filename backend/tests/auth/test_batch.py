"""B-08 バッチ集計ロジックの単体テスト（ALG-PREF / ALG-WEEKLY）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.src.auth.debt_safeguard import declare_debt, request_debt_release
from backend.src.auth.models import SafeguardStateEntity
from backend.src.auth.preference_updater import (
    evaluate_debt_for_user,
    merge_preference_labels,
)
from backend.src.auth.weekly_report import WeeklyMetricsInput, compute_weekly_metrics


def test_merge_preference_labels_dedup_and_limit() -> None:
    """ラベル統合は重複除去 + 上限。"""
    result = merge_preference_labels(["a", "b"], ["b", "c"], max_labels=3)
    assert result == ["b", "c", "a"]


def test_daily_debt_evaluation() -> None:
    """日次内の負債クーリングオフ遅延評価が機能する（DEBT-05）。"""
    now = datetime.fromisoformat("2026-05-30T00:00:00")
    state = request_debt_release(declare_debt(SafeguardStateEntity(user_id="u1")), now)
    released = evaluate_debt_for_user(state, now + timedelta(hours=72))
    assert not released.flags.has_debt


def test_weekly_metrics() -> None:
    """北極星指標の算出（§6.1）。"""
    metrics = compute_weekly_metrics(
        WeeklyMetricsInput(
            debate_sessions=100,
            debate_to_amazon_transitions=35,
            cart_intercepts=40,
            cart_conversions=10,
            total_sessions=200,
            late_night_sessions=60,
            monthly_spend_yen=148_000,
        )
    )
    assert metrics["debateToAmazonRate"] == 0.35
    assert metrics["cartInterceptConversionRate"] == 0.25
    assert metrics["lateNightUsageRatio"] == 0.3
    assert metrics["monthlySpendYen"] == 148_000.0


def test_weekly_metrics_zero_division() -> None:
    """分母 0 は 0 を返す（落ちない）。"""
    metrics = compute_weekly_metrics(
        WeeklyMetricsInput(0, 0, 0, 0, 0, 0, 0)
    )
    assert metrics["debateToAmazonRate"] == 0.0
