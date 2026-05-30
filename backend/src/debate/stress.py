"""LC-D-05 Stress Estimator（Phase 2 Step 1.2 Green）。

Memory + ヒューリスティックでストレスレベルを `low | mid | high` の 3 種に判定する純粋関数。
プロンプト合成（Step 2）が `stress_level` を入力として受け取る前段で実行される。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §4 STRESS-01〜06
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-logic-model.md ALG-STRESS

不変条件（PBT-07 重点）:
    - 戻り値の `level` は必ず 'low' / 'mid' / 'high' のいずれか
    - `score >= 0`
    - Memory retrieve が None / [] / 例外でも動作（fail-safe、STRESS-04）
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from backend.src.debate.domain.payloads import ClientSignals
from backend.src.debate.domain.results import StressLevel, StressLevelResult

# ---------------------------------------------------------------------------
# STRESS-CONFIG（business-rules.md §4 STRESS-03 / 05 と整合）
# ---------------------------------------------------------------------------

#: 深夜帯（23-04 時 JST）の加算スコア
_LATE_NIGHT_SCORE: Final[int] = 2

#: 残業帯（18-23 時 JST、深夜帯と重複しない時間帯）の加算スコア
_OVERTIME_SCORE: Final[int] = 1

#: cart_intercepts 閾値（>= で +1）
_CART_INTERCEPT_THRESHOLD: Final[int] = 3

#: debate_refuses 閾値（>= で +1）
_DEBATE_REFUSE_THRESHOLD: Final[int] = 1

#: Memory signal の最大加算（'stress_high' のような high-stress signal が複数あっても +2 まで）
_MEMORY_HIGH_SIGNAL_MAX: Final[int] = 2

#: スコア → レベル変換閾値
_HIGH_THRESHOLD: Final[int] = 4
_MID_THRESHOLD: Final[int] = 2

#: Memory signal キーワード（'stress_high' / 'fatigue_chronic' / 'sleep_deprivation' 等）
_HIGH_STRESS_SIGNAL_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"stress_high", "fatigue_chronic", "sleep_deprivation", "burnout", "overload"}
)


def estimate_stress_level(
    actor_id: str,
    now: datetime,
    client_signals: ClientSignals,
    memory_signals: list[str] | None = None,
) -> StressLevelResult:
    """ALG-STRESS: ヒューリスティック + Memory 検索結果でストレスレベルを推定する。

    business-rules.md §4 STRESS-03 のスコア配点を実装:
        - 深夜帯（23-04 時 JST）= +2
        - 残業帯（18-23 時 JST、深夜帯と重複しない時間帯）= +1
        - Memory 'high' signals = 最大 +2（最大上限あり）
        - cart_intercepts >= 3 = +1
        - recent_debate_refuses >= 1 = +1
        - last_signin_at_late_night = +1

    レベル変換（STRESS-05）:
        - score >= 4 → 'high'
        - score >= 2 → 'mid'
        - それ以外 → 'low'

    Args:
        actor_id: Cognito JWT.sub。signals_used に含めない（PII）。
        now: 現在時刻（UTC、テスト容易性のため引数化）。本番では `datetime.now(UTC)`。
        client_signals: Mobile 側の信号。
        memory_signals: AgentCore Memory `semanticMemoryStrategy` retrieve の結果サマリ。
            None / [] でも fail-safe で動作（STRESS-04）。

    Returns:
        StressLevelResult: level / score / signals_used（debug 用、Telemetry には level のみ送信）。

    不変条件:
        任意の入力に対し result.level in {'low', 'mid', 'high'}（PBT-07）。
    """
    score = 0
    signals_used: list[str] = []

    # 1. 時間帯加算（actor_id に依存しない、PII なし）
    hour_jst = client_signals.current_hour_jst
    if _is_late_night(hour_jst):
        score += _LATE_NIGHT_SCORE
        signals_used.append(f"late_night_hour={hour_jst}")
    elif _is_overtime(hour_jst):
        score += _OVERTIME_SCORE
        signals_used.append(f"overtime_hour={hour_jst}")

    # 2. cart_intercepts 閾値判定
    if client_signals.recent_cart_intercepts >= _CART_INTERCEPT_THRESHOLD:
        score += 1
        signals_used.append(f"cart_intercepts>={_CART_INTERCEPT_THRESHOLD}")

    # 3. debate_refuses 閾値判定
    if client_signals.recent_debate_refuses >= _DEBATE_REFUSE_THRESHOLD:
        score += 1
        signals_used.append(f"debate_refuses>={_DEBATE_REFUSE_THRESHOLD}")

    # 4. last_signin_at_late_night
    if client_signals.last_signin_at_late_night:
        score += 1
        signals_used.append("late_night_signin")

    # 5. Memory signal 加算（fail-safe、None / [] でも動作）
    if memory_signals:
        memory_score = _evaluate_memory_signals(memory_signals)
        if memory_score > 0:
            score += memory_score
            signals_used.append(f"memory_high_signals={memory_score}")

    level = _score_to_level(score)
    return StressLevelResult(level=level, score=score, signals_used=signals_used)


def _is_late_night(hour_jst: int) -> bool:
    """深夜帯（23-04 時 JST）かを判定する。"""
    return hour_jst >= 23 or hour_jst < 4


def _is_overtime(hour_jst: int) -> bool:
    """残業帯（18-22 時 JST、深夜帯と重複しない範囲）かを判定する。"""
    return 18 <= hour_jst < 23


def _evaluate_memory_signals(memory_signals: list[str]) -> int:
    """Memory signals から 'high stress' 系キーワードをカウントし、上限 _MEMORY_HIGH_SIGNAL_MAX で打ち切る。"""
    high_count = sum(
        1
        for sig in memory_signals
        if any(keyword in sig.lower() for keyword in _HIGH_STRESS_SIGNAL_KEYWORDS)
    )
    return min(high_count, _MEMORY_HIGH_SIGNAL_MAX)


def _score_to_level(score: int) -> StressLevel:
    """スコア → レベル変換（STRESS-05）。"""
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MID_THRESHOLD:
        return "mid"
    return "low"
