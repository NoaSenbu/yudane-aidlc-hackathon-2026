"""ALG-LINK の単体テスト + PBT-02（Special Link ↔ ASIN round-trip / 短縮禁止 / 環境ガード）。"""

from __future__ import annotations

from hypothesis import given, settings

from backend.src.reel.special_link import generate_special_link
from backend.tests.reel.strategies import asins

# S-01 正本（shared/asin-extractor/python）で逆抽出して一致を検証
from asin_extractor import AsinSuccess, extract_asin

_TAG = "yudane-22"


def test_dev_returns_placeholder_link() -> None:
    """dev は仮リンク（blocked=false、識別子付き）。"""
    link = generate_special_link("B0EXAMPLE1", "user-1", env="dev", associates_tag=_TAG, creators_approved=False)
    assert link.blocked is False
    assert "yudane_env=dev" in link.url


def test_prd_unapproved_blocked() -> None:
    """prd 未承認は遷移ブロック（US-03-04 AC-4）。"""
    link = generate_special_link("B0EXAMPLE1", "user-1", env="prd", associates_tag=_TAG, creators_approved=False)
    assert link.blocked is True


def test_prd_approved_not_blocked() -> None:
    """prd 承認済みは通常リンク。"""
    link = generate_special_link("B0EXAMPLE1", "user-1", env="prd", associates_tag=_TAG, creators_approved=True)
    assert link.blocked is False
    assert link.url.startswith("https://www.amazon.co.jp/dp/B0EXAMPLE1")


def test_no_url_shortener() -> None:
    """短縮 URL を使わない（NG-8 / REEL-LINK-03）。"""
    link = generate_special_link("B0EXAMPLE1", "user-1", env="prd", associates_tag=_TAG, creators_approved=True)
    assert "amzn.to" not in link.url
    assert "amzn.asia" not in link.url
    assert link.url.startswith("https://www.amazon.co.jp/")


def test_deterministic_pure_function() -> None:
    """同一入力 → 同一 URL（純関数、REEL-LINK-01）。"""
    a = generate_special_link("B0EXAMPLE1", "user-1", env="prd", associates_tag=_TAG, creators_approved=True)
    b = generate_special_link("B0EXAMPLE1", "user-1", env="prd", associates_tag=_TAG, creators_approved=True)
    assert a == b


# --- PBT-02 round-trip ---

@given(asin=asins)
@settings(max_examples=200)
def test_round_trip_extract_asin(asin: str) -> None:
    """PBT: 生成 URL を S-01 で逆抽出すると元 ASIN に戻る（REEL-LINK-02）。"""
    link = generate_special_link(asin, "user-1", env="prd", associates_tag=_TAG, creators_approved=True)
    result = extract_asin(link.url)
    assert isinstance(result, AsinSuccess)
    assert result.asin == asin
