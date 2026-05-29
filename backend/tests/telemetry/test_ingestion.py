"""B-14 TelemetryIngestion コアロジックの単体テスト + idempotency。"""

from __future__ import annotations

from backend.src.common.models import TelemetryEnvelope, TelemetryEvent
from backend.src.telemetry.ingestion import filter_known_events

_KNOWN = frozenset({"screen_view", "app_foreground"})


def _envelope(*names: str) -> TelemetryEnvelope:
    return TelemetryEnvelope(
        events=[TelemetryEvent(name=n, occurredAt="2026-05-30T00:00:00Z") for n in names],
        clientSentAt="2026-05-30T00:00:00Z",
        schemaVersion="1.0.0",
    )


def test_accepts_known_events() -> None:
    """既知イベントは accepted。"""
    outcome = filter_known_events(_envelope("screen_view", "app_foreground"), _KNOWN)
    assert outcome.accepted == 2
    assert outcome.dropped == 0


def test_drops_unknown_events() -> None:
    """未知イベントは dropped（TEL-01）。"""
    outcome = filter_known_events(_envelope("screen_view", "evil_event"), _KNOWN)
    assert outcome.accepted == 1
    assert outcome.dropped == 1


def test_idempotent_counting() -> None:
    """同一封筒を二度処理しても件数は同じ（純関数、PBT-04 相当）。"""
    envelope = _envelope("screen_view", "x", "app_foreground")
    assert filter_known_events(envelope, _KNOWN) == filter_known_events(envelope, _KNOWN)
