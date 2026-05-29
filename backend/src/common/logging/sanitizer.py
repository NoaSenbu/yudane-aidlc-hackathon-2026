"""Allowlist Sanitizer（PAT-SEC-02 / Q4=refinedA / default-deny）。

ログ・テレメトリに渡る構造体を再帰走査し、S-04 の allowlist にないキーは
full-mask する（fail-safe）。新規 PII 列が追加されても allowlist に足さない限り
自動でマスクされる（PII-01〜06）。
"""

from __future__ import annotations

import re
from typing import Any, Final, Literal

# S-04 TelemetryContracts と一致させる（クロス言語、PII-01/02/03）
ALLOWED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "correlationId",
        "sessionId",
        "userId",
        "screen",
        "eventName",
        "durationMs",
        "statusCode",
        "source",
        "category",
        "decision",
        "reasonCode",
    }
)

PII_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "email",
        "password",
        "token",
        "secret",
        "apiKey",
        "address",
        "phone",
        "creditCard",
    }
)

_MASK: Final[str] = "***"

# message 本文の二次防御（PII-06）
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b0\d{1,4}-?\d{1,4}-?\d{3,4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")

FieldClassification = Literal["allowed", "pii", "unclassified"]


def classify_field(key: str) -> FieldClassification:
    """フィールド名を分類する（default-deny、PII 優先）。"""
    if key in PII_FIELDS:
        return "pii"
    if key in ALLOWED_FIELDS:
        return "allowed"
    return "unclassified"


def _mask_value(key: str, value: Any) -> Any:  # noqa: ANN401
    """1 つの値にマスク戦略を適用する（PII-04）。"""
    classification = classify_field(key)
    if classification == "allowed":
        return value
    if classification == "pii" and key == "email" and isinstance(value, str) and "@" in value:
        # partial-email: 先頭1文字 + *** + @ 以降
        local, _, domain = value.partition("@")
        head = local[0] if local else ""
        return f"{head}{_MASK}@{domain}"
    # pii(その他) / unclassified → full-mask（fail-safe）
    return _MASK


def sanitize(record: Any) -> Any:  # noqa: ANN401
    """構造体を再帰走査し default-deny でマスクする（PII-01〜05）。

    Args:
        record: 任意のネスト構造（dict / list / プリミティブ）。

    Returns:
        マスク適用済みの新しい構造体（入力は破壊しない）。
    """
    if isinstance(record, dict):
        return {key: _sanitize_entry(key, value) for key, value in record.items()}
    if isinstance(record, list):
        return [sanitize(item) for item in record]
    return record


def _sanitize_entry(key: str, value: Any) -> Any:  # noqa: ANN401
    """dict の 1 エントリを処理する。ネストは再帰、リーフはマスク。"""
    if isinstance(value, (dict, list)):
        # ネストはまず再帰。ただしキー自体が PII/unclassified ならツリーごとマスク
        if classify_field(key) != "allowed":
            return _MASK
        return sanitize(value)
    return _mask_value(key, value)


def mask_message(message: str) -> str:
    """ログ message 本文の二次防御（PII-06）。"""
    masked = _EMAIL_RE.sub(_MASK, message)
    masked = _PHONE_RE.sub(_MASK, masked)
    masked = _CARD_RE.sub(_MASK, masked)
    return masked
