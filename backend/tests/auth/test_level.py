"""委ね Lv / 称号判定の単体テスト + PBT（LV-01〜04）。"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.auth.level import compute_level, titles_for_level


def test_level_examples() -> None:
    """代表値での Lv 算出。"""
    assert compute_level(0) == 1
    assert compute_level(100) == 2
    assert compute_level(400) == 3


def test_titles_thresholds() -> None:
    """称号は閾値到達で付与（LV-03）。"""
    assert titles_for_level(4) == []
    assert titles_for_level(5) == ["本日の湯水使い"]
    assert titles_for_level(40) == ["本日の湯水使い", "静かな信徒", "伝道師"]


@given(exp=st.integers(min_value=0, max_value=10_000_000))
@settings(max_examples=200)
def test_level_monotonic(exp: int) -> None:
    """PBT: EXP が増えれば Lv は減少しない（LV-04 単調増加）。"""
    assert compute_level(exp) <= compute_level(exp + 100)


@given(exp=st.integers(min_value=-1000, max_value=10_000_000))
@settings(max_examples=200)
def test_level_at_least_one(exp: int) -> None:
    """PBT: Lv は常に 1 以上（負 EXP でも）。"""
    assert compute_level(exp) >= 1
