"""B-14 TelemetryIngestionService のコアロジック（ALG-TEL サーバー側）。

クライアントからのバッチイベントを受け取り、未知イベント名を drop した上で
EMF メトリクスへ集計する。Lambda ハンドラ本体（handler.py）から呼ばれる。
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.src.common.models import TelemetryEnvelope


@dataclass(frozen=True)
class IngestOutcome:
    """取込結果（accepted / dropped 件数）。"""

    accepted: int
    dropped: int


def filter_known_events(
    envelope: TelemetryEnvelope,
    known_event_names: frozenset[str],
) -> IngestOutcome:
    """既知イベント名のみを accepted とし、未知を dropped として数える（TEL-01）。

    Args:
        envelope: クライアントから受け取ったバッチ。
        known_event_names: S-04 イベントカタログ。

    Returns:
        accepted / dropped 件数。
    """
    accepted = 0
    dropped = 0
    for event in envelope.events:
        if event.name in known_event_names:
            accepted += 1
        else:
            dropped += 1
    return IngestOutcome(accepted=accepted, dropped=dropped)
