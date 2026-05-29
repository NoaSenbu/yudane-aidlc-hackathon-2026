"""委ね Lv / 称号判定ロジック（ALG-LEVEL、純関数）。

EXP は Unit-4/B-13 の Amazon 遷移で加算され、Unit-2 は判定・保存を担う（LV-01〜04）。
"""

from __future__ import annotations

import math

# 称号付与の閾値（level ベース）
_TITLE_BY_LEVEL: tuple[tuple[int, str], ...] = (
    (5, "本日の湯水使い"),
    (15, "静かな信徒"),
    (40, "伝道師"),
)


def compute_level(exp: int) -> int:
    """EXP から委ね Lv を算出する（LV-01、単調増加）。

    level = floor(sqrt(exp / 100)) + 1。

    Args:
        exp: 累積散財 EXP（0 以上）。

    Returns:
        委ね Lv（1 以上）。
    """
    if exp < 0:
        exp = 0
    return math.floor(math.sqrt(exp / 100)) + 1


def titles_for_level(level: int) -> list[str]:
    """到達 level に応じた称号一覧を返す（LV-03、重複なし）。

    Args:
        level: 委ね Lv。

    Returns:
        付与される称号のリスト（昇順）。
    """
    return [title for threshold, title in _TITLE_BY_LEVEL if level >= threshold]
