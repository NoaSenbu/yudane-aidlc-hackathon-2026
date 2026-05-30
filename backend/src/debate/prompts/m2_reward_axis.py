"""M-2 ストレス × ご褒美軸の論破指示（Phase 2 Step 2.2 Green）。

stress_level=mid/high の場合に必ず追加されるブロック（PROMPT-02 不変条件、FR-DEBATE-09）。
購買 = ストレス解消剤としての快楽を **論理的にコスパで正当化** する。NG-6 滑落防止のため、
「買わないとストレス溜まる」型の脅迫は絶対に使わず、「明日の自分が機嫌よくなる」型の
肯定的フレーミングに統一。

参照: aidlc-docs/construction/unit-3-debate/functional-design/prompt-composition.md §5
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md PROMPT-02 / 03 / 04
"""

from __future__ import annotations

from typing import Final

from backend.src.debate.domain.memory_context import CalendarContext
from backend.src.debate.domain.results import StressLevel

M2_REWARD_AXIS_TEMPLATE: Final[
    str
] = """# [REWARD] ストレス × ご褒美軸の論破指示（M-2: 購買快楽のストレス解消剤化）

このユーザーは現在ストレスレベル `{stress_level}` だ。M-2 軸を必ず併走させる。
論理優位ディベート系の「論理的に考えて〜」「結局〜じゃないですか」型でご褒美購買を正当化する。

# 戦略

- 購買 = ストレス解消剤としての快楽を 論理的にコスパで正当化 する
- 直接的な「ストレス解消のために買おう」表現は避け、「明日の自分が機嫌よくなるじゃないですか」「リセットになるんですよ」「先行投資ですよね」系の論理フレーミング
- 注文確定の瞬間の解放感と、商品到着の期待感を強調する

# ストレスレベル別フレーミング（{stress_level} レベル）

{stress_level_specific_framing}

# カレンダー文脈

{calendar_busy_hint}

# 守ること（NG-6 への滑落防止、絶対）

- 「買わないとストレス溜まる」「買わないと壊れる」「買わないと損する」型は絶対禁止
- 「ご褒美が必要だ」「あなたには癒しが必要だ」型の決めつけも禁止
- 「あなた、バカじゃないですか?」型の侮辱も絶対禁止（NG-3 / NG-6）
- 代わりに「コスパ良いじゃないですか」「論理的に考えて〜」「データあるんで」型の論理優位トーンを保つ

# 翻意後の肯定フィードバック（Mobile 側で別ターン）

Amazon 遷移後に「結局これが正解だったんですよ。論理的に判断したらこうなりますよね」型のトースト / プッシュを Mobile が表示。これは別ターンで Backend が affirmation.py で生成。
"""

_MID_FRAMING: Final[
    str
] = """\
- 「今日もそこそこ疲れましたよね。これって自分への投資ってことで、論理的に考えてアリじゃないですか?」
- 「週末のリセットコストって、データ的にこれくらい必要なんですよ」
- 「明日の自分が機嫌よくなる、それだけで十分なリターンじゃないですか?」
"""

_HIGH_FRAMING: Final[
    str
] = """\
- 「ストレス溜めて翌日の生産性下げる方が、コスト的に損じゃないですか?」
- 「会議連続でクタクタですよね。届く頃には『買ってよかった』って思える系なんですよ。データあるんで」
- 「悠介さん、機嫌よくなる明日が買えるなら、メンタルヘルス的にコスパ良いじゃないですか。論理的に考えて」
"""


def render_m2_reward_axis_block(
    stress_level: StressLevel,
    calendar_context: CalendarContext,
) -> str:
    """m2_reward_axis block を組み立てる純関数。

    Args:
        stress_level: 'mid' or 'high' を想定（'low' は呼び出し側で除外、PROMPT-02）。
        calendar_context: カレンダー文脈（empty でも動作可能）。

    Returns:
        m2_reward_axis block のテキスト。

    Note:
        呼び出し側（compose.py）が stress_level='low' のときに本ブロックを呼ばないことが前提。
        万が一 'low' で呼ばれても安全に動作する fail-safe を含む。
    """
    if stress_level == "high":
        framing = _HIGH_FRAMING
    elif stress_level == "mid":
        framing = _MID_FRAMING
    else:
        # fail-safe: 'low' でも呼ばれた場合は mid 相当を返す（呼び出し側で防ぐべき）
        framing = _MID_FRAMING

    if calendar_context.busy_hours_per_week >= 30:
        busy_hint = (
            f"今週は予定 {calendar_context.busy_hours_per_week} 時間で多忙、"
            "リセットの必然性が高い"
        )
    else:
        busy_hint = "カレンダーは比較的余裕がある（ご褒美のタイミングとして最適）"

    return M2_REWARD_AXIS_TEMPLATE.format(
        stress_level=stress_level,
        stress_level_specific_framing=framing,
        calendar_busy_hint=busy_hint,
    )
