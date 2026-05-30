"""第 3 層モデレーション callback_handler（Phase 3-2.2 Green）。

Bedrock Guardrails（第 2 層）+ プロンプトガードレール（第 1 層）の後段で、
生成された text に NG-3 / NG-6 系パターンが含まれていないか正規表現で最終チェック。

検出時は `NgDetection` を返し、main.py が `moderation_blocked` event を yield する。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-01〜03
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.src.debate.moderation.ng_patterns import NG_PATTERN_GROUPS


class NgDetection(BaseModel):
    """NG パターン検出結果（value object）。

    Attributes:
        pattern_id: 'NG-3' / 'NG-6' 等。
        pattern_name: 'guilt_coercion' / 'insult' / 'victory_boast' / 'condescension'。
        matched_text: マッチした部分文字列（debug 用、Telemetry には送らない）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pattern_id: str = Field(..., min_length=1)
    pattern_name: str = Field(..., min_length=1)
    matched_text: str = Field(default="", max_length=200)


def check_text_for_ng_patterns(text: str) -> NgDetection | None:
    """text に NG-3 / NG-6 系パターンが含まれているか判定する純関数。

    Args:
        text: Bedrock Haiku 4.5 が生成した chunk テキスト。

    Returns:
        NG パターンが含まれていれば最初に検出した NgDetection、含まれていなければ None。

    優先順位（business-rules MOD-02 decisive 判定）:
        1. NG-6 罪悪感強要（最重要）
        2. NG-3 侮辱・侮蔑語
        3. 勝ち誇り型
        4. 過度な見下し
    """
    for pattern_id, pattern_name, patterns in NG_PATTERN_GROUPS:
        for pat in patterns:
            match = pat.search(text)
            if match is not None:
                return NgDetection(
                    pattern_id=pattern_id,
                    pattern_name=pattern_name,
                    matched_text=match.group(0)[:200],
                )
    return None
