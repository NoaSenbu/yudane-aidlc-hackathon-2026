"""ReelCursor encode/decode の round-trip テスト（NFR-PBT-05 / PBT-02）。"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.reel.cursor import ReelCursor, decode_cursor, encode_cursor


def test_decode_none_returns_initial() -> None:
    """None / 空文字は初期カーソル。"""
    assert decode_cursor(None) == ReelCursor()
    assert decode_cursor("") == ReelCursor()


def test_decode_invalid_falls_back() -> None:
    """不正トークンは初期カーソルにフォールバック（改変耐性）。"""
    assert decode_cursor("not-a-valid-cursor!!!") == ReelCursor()


def test_advance_monotonic_seen_and_one_way_boost() -> None:
    """seen は単調増加、boost_consumed は false→true の一方向（REEL-PAGE-04）。"""
    c0 = ReelCursor()
    c1 = c0.advance(("B000000001",), consumed_boost=True)
    c2 = c1.advance(("B000000002",), consumed_boost=False)
    assert c2.seen_card_keys == ("B000000001", "B000000002")
    assert c2.boost_consumed is True


_cursors = st.builds(
    ReelCursor,
    seen_card_keys=st.lists(st.from_regex(r"^[A-Z0-9]{10}$", fullmatch=True), max_size=10).map(tuple),
    rank_position=st.integers(min_value=0, max_value=1000),
    boost_consumed=st.booleans(),
    session_id=st.text(max_size=12),
)


@given(cursor=_cursors)
@settings(max_examples=200)
def test_round_trip(cursor: ReelCursor) -> None:
    """PBT: encode → decode で元のカーソルに一致（round-trip、NFR-PBT-05）。"""
    assert decode_cursor(encode_cursor(cursor)) == cursor
