"""S-01 AsinExtractor（Python 実装）。

Amazon URL から ASIN を抽出・検証する。TypeScript 実装（extract-asin.ts）と
同一入力に対し同一出力を返す（ASIN-07、クロス言語一致）。
設計: business-logic-model.md ALG-ASIN / business-rules.md ASIN-01〜07。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, urlparse

AsinSource = Literal[
    "path-dp",
    "path-gp-product",
    "path-gp-aw",
    "query-asin",
    "short-url",
]

FailureReason = Literal["no-match", "invalid-checksum-format", "unsupported-host"]


@dataclass(frozen=True)
class AsinSuccess:
    """抽出成功の結果。"""

    asin: str
    source: AsinSource
    normalized_from: str
    ok: Literal[True] = True


@dataclass(frozen=True)
class AsinFailure:
    """抽出失敗の結果。"""

    reason: FailureReason
    input: str
    ok: Literal[False] = False


AsinResult = AsinSuccess | AsinFailure

_ALLOWED_AMAZON_HOST = re.compile(r"(^|\.)amazon\.[a-z.]+$")
_SHORT_HOSTS = frozenset({"amzn.to", "amzn.asia"})
_ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")

# パス抽出ルール（優先順位順、ASIN-04）
_PATH_RULES: tuple[tuple[AsinSource, re.Pattern[str]], ...] = (
    ("path-dp", re.compile(r"/dp/([A-Za-z0-9]{10})(?:[/?]|$)")),
    ("path-gp-product", re.compile(r"/gp/product/([A-Za-z0-9]{10})(?:[/?]|$)")),
    ("path-gp-aw", re.compile(r"/gp/aw/d/([A-Za-z0-9]{10})(?:[/?]|$)")),
)


def is_valid_asin(asin: str) -> bool:
    """ASIN が有効な形式（10 桁英数字、大文字正規化済み）かを判定する。

    Args:
        asin: 判定対象。

    Returns:
        10 桁英数字なら True。
    """
    return bool(_ASIN_PATTERN.match(asin))


def extract_asin(url: str) -> AsinResult:
    """Amazon URL から ASIN を抽出する。

    dp / gp-product / gp-aw / クエリ asin の順でマッチし、最初に見つかったものを
    大文字正規化して返す。短縮 URL（amzn.to / amzn.asia）は展開を呼び出し側に委ね、
    ここでは no-match として返す（ASIN-05）。

    Args:
        url: Amazon 共有 URL。

    Returns:
        抽出結果（AsinResult）。
    """
    trimmed = url.strip()
    parsed = urlparse(trimmed)
    if not parsed.scheme or not parsed.netloc:
        return AsinFailure(reason="no-match", input=url)

    host = parsed.hostname.lower() if parsed.hostname else ""

    if host in _SHORT_HOSTS:
        return AsinFailure(reason="no-match", input=url)

    if not _ALLOWED_AMAZON_HOST.search(host):
        return AsinFailure(reason="unsupported-host", input=url)

    for source, pattern in _PATH_RULES:
        match = pattern.search(parsed.path)
        if match:
            return _finalize(match.group(1), source, url)

    query_asin = parse_qs(parsed.query).get("asin", [None])[0]
    if query_asin:
        return _finalize(query_asin, "query-asin", url)

    return AsinFailure(reason="no-match", input=url)


def _finalize(candidate: str, source: AsinSource, original: str) -> AsinResult:
    """抽出した候補を正規化・検証して結果化する（ASIN-02）。"""
    asin = candidate.upper()
    if not is_valid_asin(asin):
        return AsinFailure(reason="invalid-checksum-format", input=original)
    return AsinSuccess(asin=asin, source=source, normalized_from=original)
