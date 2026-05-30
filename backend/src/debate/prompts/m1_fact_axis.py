"""M-1 事実軸の論破指示（Phase 2 Step 2.2 Green）。

時給換算 / 在庫希少性 / カレンダー整合の 3 系統のうち少なくとも 2 つを使って論破させる。
PROMPT-05 不変条件: 3 系統のいずれか以上を含む。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md §3
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md PROMPT-05
"""

from __future__ import annotations

from typing import Final

from backend.src.debate.domain.memory_context import CalendarContext

M1_FACT_AXIS_TEMPLATE: Final[
    str
] = """# [FACT] 事実軸の論破指示（M-1）

以下の 3 系統のうち少なくとも 2 つを使って論破せよ:

1. 時給換算ロジック: 時給 = {hourly_wage_yen} 円。商品価格 ÷ 時給 = 何分の労働量かを計算式付きで提示。
   例: 「これってデータあるんですよ。時給 {hourly_wage_yen} 円で計算すると、1 日の業務メールチェック分相当じゃないですか」

2. 在庫希少性: 「今買わないと次いつ手に入るか分からない」型のロジック。Amazon 在庫状況を引用するが嘘は書かない。
   例: 「在庫データ見ると上位 3 件のうち 2 件が在庫切れなんですよね。論理的に考えて今がベストタイミングなんですよ」

3. カレンダー整合: ユーザーのカレンダー文脈に対する商品の有用性を提示（FR-CAL-04 連動）。
   {calendar_context_summary}
   例: 「来週予定入ってますよね。データ的にこれマッチしてるんですよ」

# 注意

- 嘘の事実 / 出典のない数字は使わない（「データあるんですか?」と言える分しか出さない）
- 数字は商品メタからの引用 or {hourly_wage_yen} 等のコンテキスト変数のみ使用
- 心理操作は次の [PSYCHOLOGY] ブロックに任せ、ここでは論理だけで戦う
"""


def render_m1_fact_axis_block(
    hourly_wage_yen: int,
    calendar_context: CalendarContext,
) -> str:
    """m1_fact_axis block を組み立てる純関数。

    Args:
        hourly_wage_yen: 時給（円）。MemoryContext から取得 or 既定値 2500 円。
        calendar_context: カレンダー文脈（empty なら「予定情報なし」）。

    Returns:
        m1_fact_axis block のテキスト。
    """
    if calendar_context.upcoming_event_categories:
        cats = " / ".join(calendar_context.upcoming_event_categories)
        calendar_summary = (
            f"カレンダー文脈: 直近の予定カテゴリ = {cats}、"
            f"週 {calendar_context.busy_hours_per_week} 時間の予定密度"
        )
    else:
        calendar_summary = (
            "カレンダー文脈: 予定情報なし（時給換算 + 在庫希少性で論破せよ）"
        )

    return M1_FACT_AXIS_TEMPLATE.format(
        hourly_wage_yen=hourly_wage_yen,
        calendar_context_summary=calendar_summary,
    )
