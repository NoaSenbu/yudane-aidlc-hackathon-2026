"""Unit-3 Debate MemoryContext DTO（Phase 2 Step 2.3 で追加）。

`compose_debate_prompt()` が必要とする Memory retrieve 結果の構造化型。
Phase 2 では P0 範囲（組み込み 2 Strategy）のみを表現、P1 の `m1m2_axis_extracted` は
Phase 4 で本格実装（Phase 2 では空 list でも動作する fail-safe 設計）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §7.3
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.src.debate.domain.results import DebateAxis

#: 翻意結果（'agreed' / 'refused' / 'ongoing'）
DebateOutcome = (
    "agreed",
    "refused",
    "ongoing",
)


class OutcomeRecord(BaseModel):
    """過去の論破セッションの結果 1 件。

    Attributes:
        axis: 翻意した軸。
        outcome: 結果（'agreed' / 'refused' / 'ongoing'）。
        turn: 翻意までのターン数。
        occurred_at: 発生時刻（ISO 8601）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    axis: DebateAxis
    outcome: str = Field(..., pattern=r"^(agreed|refused|ongoing)$")
    turn: int = Field(..., ge=1)
    occurred_at: datetime


class CalendarContext(BaseModel):
    """カレンダー文脈（Unit-6 連携、Phase 2 では empty で動作可能）。

    Attributes:
        upcoming_event_categories: 直近の予定カテゴリ（'work' / 'social' / 'travel' 等）。
        busy_hours_per_week: 1 週間の予定密度（0〜168 時間）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    upcoming_event_categories: list[str] = Field(default_factory=list)
    busy_hours_per_week: int = Field(default=0, ge=0, le=168)


class MemoryContext(BaseModel):
    """ALG-MEMORY-READ の戻り値（Phase 2 P0 範囲）。

    Attributes:
        recent_debate_outcomes: 直近の論破結果（最新 5 件まで、MEMORY-09 top_k <= 5）。
        preferred_axis: ユーザーが翻意した軸の傾向（既定 'fact'、PROMPT-CONFIG）。
        stress_signals: ストレス推定用 signals（low cardinality）。
        m1m2_axis_extracted: M-1/M-2 軸抽出（Phase 4 で本格、Phase 2 では空 list）。
        hourly_wage_yen: 時給換算値（既定 PROMPT_HOURLY_WAGE_FALLBACK_YEN=2500）。
        calendar_context: カレンダー文脈（Unit-6 連携、Phase 2 では empty）。
        preferred_affirmation_style: 肯定 FB のスタイル（既定 'casual'）。

    不変条件:
        - empty MemoryContext でも preferred_axis='fact' で動作（PROMPT-CONFIG）
        - recent_debate_outcomes は最新 5 件まで（MEMORY-09 top_k <= 5）
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    recent_debate_outcomes: list[OutcomeRecord] = Field(
        default_factory=list, max_length=5
    )
    preferred_axis: DebateAxis = "fact"
    stress_signals: list[str] = Field(default_factory=list)
    m1m2_axis_extracted: list[str] = Field(default_factory=list)
    hourly_wage_yen: int | None = Field(default=None, ge=500, le=100000)
    calendar_context: CalendarContext = Field(default_factory=CalendarContext)
    preferred_affirmation_style: str = Field(
        default="casual", pattern=r"^(casual|cool|caring)$"
    )


def empty_memory_context() -> MemoryContext:
    """fail-safe: 空の MemoryContext を返す（ローカルモード / Memory retrieve 失敗時）。

    PROMPT-CONFIG の既定値（preferred_axis='fact'）で動作するようにする。
    """
    return MemoryContext()
