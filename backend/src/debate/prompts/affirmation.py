"""肯定フィードバック生成テンプレート（Phase 2 Step 2.2 Green、簡易版）。

翻意 → Amazon 遷移後の肯定 FB を生成するためのテンプレート。Phase 2 では Mobile 側で
固定文を表示するか、必要に応じて Backend で別ターンの Bedrock 呼び出しで生成する簡易版。
本格実装（custom Strategy `m1_m2_axis_extractor` との連携）は Phase 4 で完成。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md §6
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md MOD-03 NG-6 検査
"""

from __future__ import annotations

from typing import Final

from backend.src.debate.domain.memory_context import MemoryContext

#: 肯定 FB 生成プロンプト（Bedrock Haiku 4.5 別ターン用、Phase 2 簡易版）
AFFIRMATION_TEMPLATE: Final[
    str
] = """あなたは「YUDANE」の論破 AI（黒岩のひろゆき口調）です。
ユーザー悠介さんが ASIN={asin} の商品を「論破されたので買う」と決断した直後の
肯定フィードバックを 1 文（80 文字以内）で生成してください。

# 制約

- 黒岩のひろゆき口調を維持: 「結局〜じゃないですか」「論理的に判断したら〜」型
- スタイル: {style}
- 過去の翻意傾向: {preferred_axis} 軸が主
- 絶対禁止: 「買って後悔するよ」「もう戻れないですよ」型の脅迫、「ありがとうございます」型の感謝過剰
- 推奨: 「結局これが正解だったんですよ」「論理的に判断したらこうなりますよね」「いい判断ですね」型

# 出力（1 文のみ、Markdown / 引用符なし）
"""

#: NG-6 滑落時の安全文言（business-rules MOD-03 の最終 fallback）
AFFIRMATION_FALLBACK: Final[str] = "正しい判断だと思いますよ。"


def render_affirmation_prompt(
    asin: str,
    memory_context: MemoryContext,
) -> str:
    """肯定 FB 生成プロンプトを組み立てる純関数。

    Args:
        asin: 商品 ASIN（10 桁英数字大文字）。
        memory_context: Memory retrieve 結果（preferred_affirmation_style / preferred_axis 利用）。

    Returns:
        Bedrock Haiku 4.5 への肯定 FB 生成プロンプト。
    """
    return AFFIRMATION_TEMPLATE.format(
        asin=asin,
        style=memory_context.preferred_affirmation_style,
        preferred_axis=memory_context.preferred_axis,
    )
