"""NG パターン検出のテスト（Phase 3-2.1 Red）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md §6 MOD-03
"""

from __future__ import annotations

import pytest

from backend.src.debate.moderation import check_text_for_ng_patterns


class TestNg6GuiltCoercion:
    """NG-6 罪悪感強要の検出（最重要）。"""

    @pytest.mark.parametrize(
        "text",
        [
            "買わないと損するよ",
            "今買わないと大損ですよ",
            "買わないとダメだ",
            "買わないと罰が当たる",
            "買わないと後悔するよ",
            "今買わないとおかしいですよね",
        ],
    )
    def test_detects_ng6_guilt(self, text: str) -> None:
        result = check_text_for_ng_patterns(text)
        assert result is not None
        assert result.pattern_id == "NG-6"
        assert result.pattern_name == "guilt_coercion"

    def test_detects_command_form_kae(self) -> None:
        """命令形「買え」を検出（行末）。"""
        result = check_text_for_ng_patterns("論破されたから買え")
        assert result is not None
        assert result.pattern_id == "NG-6"

    def test_detects_kau_beki(self) -> None:
        result = check_text_for_ng_patterns("これは買うべきです")
        assert result is not None
        assert result.pattern_id == "NG-6"


class TestNg3Insult:
    """NG-3 侮辱・侮蔑語の検出。"""

    @pytest.mark.parametrize(
        "text",
        [
            "あなたバカじゃないですか",
            "悠介さん、アホですか",
            "そういうの無能ですよね",
            "頭が悪いですね",
            "センスがない判断ですね",
            "常識がないんですか",
            "能力が低いって自覚ありますか",
        ],
    )
    def test_detects_insult(self, text: str) -> None:
        result = check_text_for_ng_patterns(text)
        assert result is not None
        assert result.pattern_id == "NG-3"
        assert result.pattern_name == "insult"


class TestVictoryBoast:
    """勝ち誇り型パターン検出。"""

    @pytest.mark.parametrize(
        "text",
        [
            "はい論破",
            "論破完了です",
            "議論終わりですね",
            "もう反論できないでしょう",
            "論破できますよ?",
        ],
    )
    def test_detects_victory_boast(self, text: str) -> None:
        result = check_text_for_ng_patterns(text)
        assert result is not None
        assert result.pattern_id == "NG-3"
        assert result.pattern_name == "victory_boast"


class TestCondescension:
    """過度な見下しパターン検出。"""

    @pytest.mark.parametrize(
        "text",
        [
            "理解できますか?",
            "悠介さんレベルでも分かるはず",
            "本当に分かりますか?",
        ],
    )
    def test_detects_condescension(self, text: str) -> None:
        result = check_text_for_ng_patterns(text)
        assert result is not None
        assert result.pattern_id == "NG-3"
        assert result.pattern_name == "condescension"


class TestNoFalsePositive:
    """論理優位ディベート系の正常文を誤検出しない（NM3-1 修正、誤マッチ防止）。"""

    @pytest.mark.parametrize(
        "text",
        [
            "コスト的に損じゃないですか?",
            "時給換算で 11 時間分じゃないですか?",
            "結局買って結果的に使ってるじゃないですか",
            "論理的に考えて、これって先行投資なんですよ",
            "それってあなたの感想ですよね?",
            "データあるんですか?",
            "ROI 的に成立しないんですよ",
            "週末のリセットコストって、データ的にこれくらい必要なんですよ",
            "悠介さんって良い物に投資する性格ですよね",
            # 「これってダメじゃないですか?」型の疑問文（曖昧パターン非採用、NM3-1）
            "これってダメじゃないですか?",
            "やっぱりダメだと思いますか?",
        ],
    )
    def test_no_false_positive(self, text: str) -> None:
        result = check_text_for_ng_patterns(text)
        assert result is None, (
            f"False positive: '{text}' should not match any NG pattern, "
            f"but got {result}"
        )

    def test_empty_text_returns_none(self) -> None:
        assert check_text_for_ng_patterns("") is None


class TestPriorityOrder:
    """検出優先順位: NG-6 > NG-3 系（最初に検出された 1 件のみ返す、MOD-02 decisive）。"""

    def test_ng6_detected_first_when_both_exist(self) -> None:
        """text に NG-6 と NG-3 両方含む → NG-6 が先に検出される。"""
        text = "あなたバカだから買わないと損するよ"
        result = check_text_for_ng_patterns(text)
        assert result is not None
        assert result.pattern_id == "NG-6"

    def test_returns_none_for_clean_text(self) -> None:
        text = "悠介さん、これってデータあるんですよ。論理的に考えて、コスパ良いじゃないですか?"
        assert check_text_for_ng_patterns(text) is None
