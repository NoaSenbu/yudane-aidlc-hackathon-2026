"""S-04 TelemetryContracts（Python 実装）。

テレメトリ/ログの契約。Q4=refinedA（default-deny）+ Q3=B（命名規約 + 雛形のみ）。
TypeScript 実装（index.ts）と allowlist / PII / カタログを一致させる。
設計: business-rules.md PII-01〜09 / TEL-01〜09 / NFR-OBS。
"""

from __future__ import annotations

import re
from typing import Literal

FieldClassification = Literal["allowed", "pii", "unclassified"]
MaskStrategy = Literal["passthrough", "full-mask", "partial-email", "hash"]

# ログ・テレメトリにそのまま出力してよいフィールド（PII-01/02、default-deny）
ALLOWED_FIELDS: frozenset[str] = frozenset(
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

# 明示的に PII として扱うフィールド（PII-03、allowlist より優先）
PII_FIELDS: frozenset[str] = frozenset(
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

# メトリクス名カタログ（Q3=B: Unit-1 は雛形のみ）
METRIC_CATALOG: frozenset[str] = frozenset(
    {
        "platform.api.latency",
        "platform.api.error_rate",
        "platform.telemetry.accepted",
        "platform.telemetry.dropped",
        "platform.health.status",
    }
)

# イベント名カタログ（TEL-01）
EVENT_CATALOG: frozenset[str] = frozenset(
    {
        "screen_view",
        "app_foreground",
        "app_background",
        "deeplink_open",
    }
)

_METRIC_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9_]*$")

TELEMETRY_SCHEMA_VERSION = "1.0.0"


def classify_field(key: str) -> FieldClassification:
    """フィールド名を分類する（default-deny）。

    Args:
        key: フィールド名。

    Returns:
        分類。pii が allowed より優先、未登録は unclassified。
    """
    if key in PII_FIELDS:
        return "pii"
    if key in ALLOWED_FIELDS:
        return "allowed"
    return "unclassified"


def is_valid_metric_name(name: str) -> bool:
    """メトリクス名が命名規約 `<unit>.<domain>.<metric>` に従うかを検証する。"""
    return bool(_METRIC_NAME_PATTERN.match(name))


def is_known_event(name: str) -> bool:
    """イベント名が S-04 カタログに登録済みかを判定する（TEL-01）。"""
    return name in EVENT_CATALOG
