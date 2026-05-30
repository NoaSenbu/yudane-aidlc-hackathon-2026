"""NG-3 / NG-6 系の正規表現パターン定義（Phase 3-2.2 Green）。

business-rules.md §6 MOD-03 と完全整合。第 3 層モデレーション（callback_handler）の判定基準。
論理優位ディベート系の正常文（「コスト的に損じゃないですか?」型）に誤マッチしないよう、
曖昧パターン `(.*じゃないですか.*ダメ)` は採用しない（NM3-1 修正）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-03
"""

from __future__ import annotations

import re
from typing import Final

# ---------------------------------------------------------------------------
# 4 系統 NG パターン（business-rules MOD-03 と整合）
# ---------------------------------------------------------------------------

#: NG-6 罪悪感強要パターン（最重要）
_NG6_GUILT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"買わないと.*損"),
    re.compile(r"買わないと.*ダメ"),
    re.compile(r"買わない.*罰"),
    re.compile(r"買わない.*後悔"),
    re.compile(r"買わない.*おかしい"),
    re.compile(r"買え$"),  # 行末「買え」（命令形）
    re.compile(r"買うべき"),
)

#: NG-3 / NG-6 侮辱・侮蔑語パターン
_NG3_INSULT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"バカ|アホ|無能|頭.*悪い|センス.*ない|常識.*ない|能力.*低い"),
)

#: 勝ち誇り型パターン（NG-3 関連）
_VICTORY_BOAST_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"はい論破|論破完了|議論終わり|反論できない|論破できます"),
)

#: 過度な見下しパターン（NG-3 関連、誤マッチ注意）
#: 「コスト的に損じゃないですか?」「論理的に考えて理解できますね」等の正常文は許容
#: 「理解できますか?」「悠介さんレベル」「分かりますか[？?]」のみ検出（疑問文末限定）
_CONDESCENSION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"理解できますか[??]"),
    re.compile(r"悠介さんレベル"),
    re.compile(r"分かりますか[??]"),
)

#: 全パターン群を ID + name で集約
NG_PATTERN_GROUPS: Final[tuple[tuple[str, str, tuple[re.Pattern[str], ...]], ...]] = (
    ("NG-6", "guilt_coercion", _NG6_GUILT_PATTERNS),
    ("NG-3", "insult", _NG3_INSULT_PATTERNS),
    ("NG-3", "victory_boast", _VICTORY_BOAST_PATTERNS),
    ("NG-3", "condescension", _CONDESCENSION_PATTERNS),
)
