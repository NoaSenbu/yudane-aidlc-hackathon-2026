"""ReelCursor の不透明エンコード/デコード（Q9=A / REEL-PAGE-01/02）。

カーソルに既出カード集合・ランキング位置・ブースト消費フラグを base64url で詰める。
クライアントには opaque（解釈・改変しない）。serialize ⇔ deserialize は round-trip 一致（NFR-PBT-05）。
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ReelCursor:
    """リールのページングカーソル。"""

    seen_card_keys: tuple[str, ...] = ()
    rank_position: int = 0
    boost_consumed: bool = False
    session_id: str = ""

    def advance(self, new_keys: tuple[str, ...], consumed_boost: bool) -> ReelCursor:
        """ページ送り後の新カーソルを返す（seen は単調増加、boost は一方向）。"""
        merged = tuple(dict.fromkeys((*self.seen_card_keys, *new_keys)))
        return ReelCursor(
            seen_card_keys=merged,
            rank_position=self.rank_position + len(new_keys),
            boost_consumed=self.boost_consumed or consumed_boost,
            session_id=self.session_id,
        )


def encode_cursor(cursor: ReelCursor) -> str:
    """カーソルを不透明 base64url 文字列へ。"""
    payload = {
        "s": list(cursor.seen_card_keys),
        "p": cursor.rank_position,
        "b": cursor.boost_consumed,
        "sid": cursor.session_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(token: str | None) -> ReelCursor:
    """不透明トークンをカーソルへ。None/不正は初期カーソルにフォールバック。"""
    if not token:
        return ReelCursor()
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(raw)
        return ReelCursor(
            seen_card_keys=tuple(payload.get("s", [])),
            rank_position=int(payload.get("p", 0)),
            boost_consumed=bool(payload.get("b", False)),
            session_id=str(payload.get("sid", "")),
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return ReelCursor()
