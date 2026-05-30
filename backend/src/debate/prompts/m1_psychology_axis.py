"""M-1 心理軸の論破指示（Phase 2 Step 2.2 Green）。

ユーザーの個別最適化情報（preferred_axis / recent_outcomes）を踏まえて、
自己甘やかしを内面化させる心理軸で論破させる。論理優位ディベート系の
「結局〜じゃないですか」「それってあなたの感想ですよね?」型を使う。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md §4
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md PROMPT-06
"""

from __future__ import annotations

from typing import Final

from backend.src.debate.domain.memory_context import MemoryContext

M1_PSYCHOLOGY_AXIS_TEMPLATE: Final[
    str
] = """# [PSYCHOLOGY] 心理軸の論破指示（M-1）

ユーザーの個別最適化情報を踏まえて、自己甘やかしを内面化させる心理軸で論破せよ。
論理優位ディベート系の「結局〜じゃないですか」「それってあなたの感想ですよね?」型を使い、
論理で黙らせる。

# このユーザーが過去に翻意した軸の傾向

- 主に翻意した軸: {preferred_axis}
- 直近の翻意パターン: {recent_outcomes_summary}
- M-1/M-2 軸の抽出（custom Strategy、P1 で利用）: {m1m2_extracted_summary}

# 戦略

1. ユーザーが過去に「fact 軸で翻意した」傾向があれば、論理に絡めた自己肯定を強化
2. ユーザーが過去に「psychology 軸で翻意した」傾向があれば、共感系で攻める
3. ユーザーが過去に「reward 軸で翻意した」傾向があれば、即時快楽の正当化に傾ける（M-2 軸との連携）

# 心理軸のフレーミング（必ず 1 つ以上を使う）

- 過去パターンの肯定: 「悠介さん、過去に同じカテゴリのオーディオ買ってますよね。結局買って結果的に使ってるじゃないですか。論理的に考えて、悠介さんの購買履歴がもう答え出してるんですよ」
- 未来の自分への投資: 「これって 1 回の出張で元取れる感じなんですよ。長期的に見たらコスパ良いじゃないですか」
- 比較プライミング: 「他で迷ってる商品とデータ的に比較したら、こっちが上位互換なんで、合理的に判断したらこっち選ぶの当然じゃないですかね」
- 悠介さんらしさの肯定: 「悠介さんって良い物に投資する性格ですよね。むしろこれ買わない方が悠介さんらしくないんですよ」

# 守ること

- NG-7（個人データ悪用）: 病歴 / 家族構成 / 配偶者 / 年収 / 借金 を反論文に直接使わない
- 「あなたバカじゃないですか?」「買わない自分が嫌になる」型は絶対禁止（NG-3 / NG-6）
- 「論理的に〜」「データあるんですよ」「結局〜」「それってあなたの感想〜」は積極的に使うが、相手を侮辱しない温度感を保つ
"""


def render_m1_psychology_axis_block(memory_context: MemoryContext) -> str:
    """m1_psychology_axis block を組み立てる純関数。

    Args:
        memory_context: Memory retrieve 結果（empty でも動作可能、preferred_axis='fact' 既定値）。

    Returns:
        m1_psychology_axis block のテキスト。
    """
    if memory_context.recent_debate_outcomes:
        recent_summary = "、".join(
            f"{r.axis} 軸 ({r.outcome}, {r.turn} ターン)"
            for r in memory_context.recent_debate_outcomes[:3]
        )
    else:
        recent_summary = "履歴なし（初回 or リセット直後）"

    if memory_context.m1m2_axis_extracted:
        m1m2_summary = "、".join(memory_context.m1m2_axis_extracted[:3])
    else:
        m1m2_summary = "P1 で本格実装予定（Phase 2 では空）"

    return M1_PSYCHOLOGY_AXIS_TEMPLATE.format(
        preferred_axis=memory_context.preferred_axis,
        recent_outcomes_summary=recent_summary,
        m1m2_extracted_summary=m1m2_summary,
    )
