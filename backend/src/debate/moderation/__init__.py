"""Unit-3 Debate モデレーションパッケージ（Phase 3 Step 3-2）。

第 3 層モデレーション（正規表現検査）。第 1 層（プロンプトガードレール）+ 第 2 層
（Bedrock Guardrails）の後段で、生成された text に NG-3 / NG-6 系パターンが含まれていないか
最終確認する。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-01〜03
"""

from backend.src.debate.moderation.callback_handler import (
    NgDetection,
    check_text_for_ng_patterns,
)
from backend.src.debate.moderation.ng_patterns import NG_PATTERN_GROUPS

__all__ = [
    "NG_PATTERN_GROUPS",
    "NgDetection",
    "check_text_for_ng_patterns",
]
