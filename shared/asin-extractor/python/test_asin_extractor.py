"""S-01 AsinExtractor の単体テスト + PBT（NFR-PBT-01 / NFR-COV-01）。"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from asin_extractor import extract_asin, is_valid_asin

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "golden-cases.json"

# 有効な ASIN を生成する戦略（10 桁英数字、大文字）
asin_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=10,
    max_size=10,
)


def test_is_valid_asin() -> None:
    """10 桁英数字のみ有効。"""
    assert is_valid_asin("B0CABCDE12")
    assert not is_valid_asin("B0CABCDE1")
    assert not is_valid_asin("b0cabcde12")
    assert not is_valid_asin("B0CABCDE-2")


def test_golden_cases_cross_language() -> None:
    """golden fixtures で TS 実装とのクロス言語一致を検証する（ASIN-07）。"""
    data = json.loads(_FIXTURES.read_text(encoding="utf-8"))
    for case in data["cases"]:
        result = extract_asin(case["url"])
        assert result.ok is case["ok"], case["url"]
        if case["ok"]:
            assert result.asin == case["asin"], case["url"]
            assert result.source == case["source"], case["url"]
        else:
            assert result.reason == case["reason"], case["url"]


@given(asin=asin_strategy)
@settings(max_examples=200)
def test_round_trip_dp(asin: str) -> None:
    """PBT-02: 任意の有効 ASIN を含む /dp/ URL から元の ASIN を復元する。"""
    url = f"https://www.amazon.co.jp/dp/{asin}"
    result = extract_asin(url)
    assert result.ok
    assert result.asin == asin


@given(asin=asin_strategy, slash=st.booleans(), query=st.booleans())
@settings(max_examples=200)
def test_normalization_stability(asin: str, slash: bool, query: bool) -> None:
    """末尾スラッシュ・追加クエリの有無で結果が変わらない。"""
    base = f"https://www.amazon.co.jp/dp/{asin}"
    url = base + ("/" if slash else "") + ("?ref=abc" if query else "")
    result = extract_asin(url)
    assert result.ok
    assert result.asin == asin
