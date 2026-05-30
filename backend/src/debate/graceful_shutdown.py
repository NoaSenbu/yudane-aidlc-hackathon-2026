"""Strands graceful shutdown 80s（Phase 3-1.2 Green）。

90 秒 hard cutoff の前に 80 秒経過時点で graceful shutdown フックを発火させる純関数。
business-rules.md §1 DEBATE-CONFIG の DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS と整合。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §1 DEBATE-03
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Literal

# ---------------------------------------------------------------------------
# DEBATE-CONFIG（business-rules.md §1 と整合）
# ---------------------------------------------------------------------------

#: 1 セッション上限（FR-DEBATE-06、business-rules DEBATE-CONFIG）
DEBATE_MAX_DURATION_SECONDS: Final[int] = 90

#: graceful shutdown 発火タイミング（business-rules DEBATE-CONFIG、v3.2 Q11）
DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS: Final[int] = 80

#: サマリ生成の最大待機（80→90s 内、business-rules DEBATE-CONFIG）
DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS: Final[int] = 10


#: 経過時間に応じたシャットダウン状態
ShutdownStatus = Literal["streaming", "graceful_shutdown", "hard_cutoff"]


def check_graceful_shutdown_status(
    started_at: datetime,
    now: datetime,
) -> ShutdownStatus:
    """経過時間に応じたシャットダウン状態を判定する純関数。

    Args:
        started_at: セッション開始時刻（UTC）。
        now: 現在時刻（UTC）。

    Returns:
        - 'streaming': 80 秒未満、通常 streaming
        - 'graceful_shutdown': 80〜89 秒、graceful shutdown フック発火
        - 'hard_cutoff': 90 秒以上、hard cutoff 必須
    """
    elapsed = (now - started_at).total_seconds()
    if elapsed >= DEBATE_MAX_DURATION_SECONDS:
        return "hard_cutoff"
    if elapsed >= DEBATE_GRACEFUL_SHUTDOWN_AT_SECONDS:
        return "graceful_shutdown"
    return "streaming"
