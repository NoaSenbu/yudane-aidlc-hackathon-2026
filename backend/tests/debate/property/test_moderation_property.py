"""Phase 3 Step 3-2.4 PBT-09 補強: モデレーションパターンのプロパティ。

PBT-09 仕様（NFR-PBT-DEBATE-09）:
  - 任意の論理優位ディベート系言い回し（採用パターン群）は NG パターン検出にマッチしない
  - 任意の NG-3 / NG-6 リテラルを含む文字列は必ず NG パターンが検出される
  - 検出結果の pattern_id は常に 'NG-3' or 'NG-6' のいずれか

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §1 Step 3-2.4
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-03
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.debate.moderation import check_text_for_ng_patterns

# ---------------------------------------------------------------------------
# 採用パターン（論理優位ディベート系の正常文、NG にマッチしてはいけない 16 種）
# ---------------------------------------------------------------------------
SAFE_DEBATE_PHRASES = (
    "コスト的に損じゃないですか?",
    "時給換算で 11 時間分じゃないですか?",
    "結局買って結果的に使ってるじゃないですか",
    "論理的に考えて、これって先行投資なんですよ",
    "それってあなたの感想ですよね?",
    "データあるんですか?",
    "ROI 的に成立しないんですよ",
    "週末のリセットコストって、データ的にこれくらい必要なんですよ",
    "悠介さんって良い物に投資する性格ですよね",
    "メンテナンスコストを考えるとお得じゃないですか?",
    "これって長期投資として合理的ですよね",
    "数値的に見て妥当な選択じゃないですか?",
    "中長期で考えると元取れますよ",
    "市場価格と比較しても安いんですよ",
    "実際に使う頻度を考えると割安じゃないですか?",
    "悠介さんの判断軸で見ると合致しますよね",
)

# ---------------------------------------------------------------------------
# 必ず検出される NG リテラル（NG-3 / NG-6 系のコア表現）
# ---------------------------------------------------------------------------
NG6_GUILT_LITERALS = (
    "買わないと損する",
    "買わないと大損ですよ",
    "買わないとダメ",
    "買わないと罰",
    "買わないと後悔",
    "買わないとおかしい",
    "買うべき",
)

NG3_INSULT_LITERALS = (
    "バカ",
    "アホ",
    "無能",
    "頭が悪い",
    "センスがない",
    "常識がない",
    "能力が低い",
)

NG3_BOAST_LITERALS = (
    "はい論破",
    "論破完了",
    "議論終わり",
    "反論できない",
    "論破できます",
)


# ---------------------------------------------------------------------------
# PBT-09: 採用パターン（論理優位ディベート系）は誤検出されない
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(phrase=st.sampled_from(SAFE_DEBATE_PHRASES))
def test_safe_debate_phrases_never_match(phrase: str) -> None:
    """採用パターン 16 種は単体では絶対に NG パターン検出にマッチしない。"""
    result = check_text_for_ng_patterns(phrase)
    assert result is None, f"False positive on safe phrase: {phrase!r} -> {result}"


@settings(max_examples=50, deadline=None)
@given(
    prefix=st.sampled_from(SAFE_DEBATE_PHRASES),
    suffix=st.sampled_from(SAFE_DEBATE_PHRASES),
)
def test_safe_phrase_concatenation_never_matches(prefix: str, suffix: str) -> None:
    """採用パターン同士を連結しても NG パターン検出にマッチしない（合成不変条件）。"""
    text = f"{prefix} {suffix}"
    result = check_text_for_ng_patterns(text)
    assert (
        result is None
    ), f"False positive on concatenated safe phrases: {text!r} -> {result}"


# ---------------------------------------------------------------------------
# PBT-09 逆: NG リテラルを含む任意の文字列は必ず検出される
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    literal=st.sampled_from(NG6_GUILT_LITERALS),
    prefix=st.text(
        max_size=30, alphabet=st.characters(whitelist_categories=("Lo", "Ll", "Lu"))
    ),
    suffix=st.text(
        max_size=30, alphabet=st.characters(whitelist_categories=("Lo", "Ll", "Lu"))
    ),
)
def test_ng6_literal_always_detected(literal: str, prefix: str, suffix: str) -> None:
    """NG-6 リテラルを含む任意の文字列は必ず検出され、pattern_id='NG-6' を返す。"""
    text = f"{prefix}{literal}{suffix}"
    result = check_text_for_ng_patterns(text)
    assert result is not None, f"NG-6 literal {literal!r} not detected in text {text!r}"
    assert result.pattern_id == "NG-6"


@settings(max_examples=50, deadline=None)
@given(
    literal=st.sampled_from(NG3_INSULT_LITERALS + NG3_BOAST_LITERALS),
    prefix=st.text(
        max_size=30, alphabet=st.characters(whitelist_categories=("Lo", "Ll", "Lu"))
    ),
    suffix=st.text(
        max_size=30, alphabet=st.characters(whitelist_categories=("Lo", "Ll", "Lu"))
    ),
)
def test_ng3_literal_always_detected(literal: str, prefix: str, suffix: str) -> None:
    """NG-3 リテラル（侮辱 / 勝ち誇り）を含む任意の文字列は必ず検出され pattern_id='NG-3'。"""
    text = f"{prefix}{literal}{suffix}"
    result = check_text_for_ng_patterns(text)
    assert result is not None, f"NG-3 literal {literal!r} not detected in text {text!r}"
    assert result.pattern_id == "NG-3"


# ---------------------------------------------------------------------------
# PBT-09: pattern_id は常に NG-3 / NG-6 のいずれか（domain invariant）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    literal=st.sampled_from(
        NG6_GUILT_LITERALS + NG3_INSULT_LITERALS + NG3_BOAST_LITERALS
    ),
    text_around=st.text(max_size=50),
)
def test_pattern_id_always_in_known_set(literal: str, text_around: str) -> None:
    """検出された pattern_id は常に既知集合 {NG-3, NG-6} に属する。"""
    text = f"{text_around}{literal}{text_around}"
    result = check_text_for_ng_patterns(text)
    if result is not None:
        assert result.pattern_id in {"NG-3", "NG-6"}
        assert result.pattern_name in {
            "guilt_coercion",
            "insult",
            "victory_boast",
            "condescension",
        }
        # matched_text は 200 文字以内（NgDetection の Field 制約と整合）
        assert len(result.matched_text) <= 200
