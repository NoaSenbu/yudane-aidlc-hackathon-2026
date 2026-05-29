"""B-12 Allowlist Sanitizer の単体テスト + PBT（NFR-PBT-04 / fail-safe）。"""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.common.logging.sanitizer import (
    ALLOWED_FIELDS,
    PII_FIELDS,
    classify_field,
    mask_message,
    sanitize,
)

_MASK = "***"


def test_allowed_field_passthrough() -> None:
    """allowlist のキーは素通し。"""
    result = sanitize({"correlationId": "abc-123"})
    assert result["correlationId"] == "abc-123"


def test_pii_email_partial_mask() -> None:
    """email は partial-email マスク。"""
    result = sanitize({"email": "yusuke@example.com"})
    assert result["email"] == "y***@example.com"


def test_pii_other_full_mask() -> None:
    """その他 PII は full-mask。"""
    result = sanitize({"token": "secret-token-value"})
    assert result["token"] == _MASK


def test_unclassified_full_mask() -> None:
    """未登録キーは full-mask（fail-safe の核心）。"""
    result = sanitize({"deviceFingerprint": "xyz", "lineUserId": "U123"})
    assert result["deviceFingerprint"] == _MASK
    assert result["lineUserId"] == _MASK


def test_nested_unclassified_masked() -> None:
    """unclassified キー配下のツリーはまるごとマスク。"""
    result = sanitize({"payload": {"email": "a@b.com", "x": 1}})
    assert result["payload"] == _MASK


def test_nested_allowed_recurses() -> None:
    """allowed キー配下は再帰して個別評価。"""
    # source は allowed。その配下の email はマスクされる
    result = sanitize({"source": {"email": "a@b.com", "screen": "home"}})
    assert result["source"]["email"] == "a***@b.com"
    assert result["source"]["screen"] == "home"


def test_mask_message_secondary_defense() -> None:
    """message 本文のメール/電話/カード番号を二次マスク。"""
    masked = mask_message("連絡先 taro@example.com / 090-1234-5678")
    assert "taro@example.com" not in masked
    assert "090-1234-5678" not in masked


# --- PBT: fail-safe invariant ---

# 既知キー（allowed + pii）と未知キーを混ぜた辞書を生成
_known_keys = sorted(ALLOWED_FIELDS | PII_FIELDS)
_unknown_keys = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=1,
    max_size=12,
).filter(lambda k: k not in ALLOWED_FIELDS and k not in PII_FIELDS)

_values = st.one_of(st.text(max_size=20), st.integers(), st.booleans())


@given(
    record=st.dictionaries(
        keys=st.one_of(st.sampled_from(_known_keys), _unknown_keys),
        values=_values,
        max_size=10,
    )
)
@settings(max_examples=300)
def test_unclassified_always_masked(record: dict[str, Any]) -> None:
    """PBT: 未分類キーの値は必ずマスクされる（fail-safe、PII-02）。"""
    result = sanitize(record)
    for key, value in record.items():
        if classify_field(key) == "unclassified":
            assert result[key] == _MASK, f"未分類キー {key} がマスクされていない: {value!r}"


@given(
    record=st.dictionaries(
        keys=st.one_of(st.sampled_from(_known_keys), _unknown_keys),
        values=_values,
        max_size=10,
    )
)
@settings(max_examples=200)
def test_sanitize_idempotent(record: dict[str, Any]) -> None:
    """PBT: sanitize は冪等（二重適用しても結果が変わらない）。"""
    once = sanitize(record)
    twice = sanitize(once)
    assert once == twice
