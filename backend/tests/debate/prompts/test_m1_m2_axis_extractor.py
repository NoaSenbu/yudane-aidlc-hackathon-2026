"""M-1 / M-2 軸抽出プロンプト + パースのテスト（Phase 4 Step 4-1.1 Red→Green）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-1
"""

from __future__ import annotations

import json

import pytest

from backend.src.debate.prompts.m1_m2_axis_extractor import (
    M1_M2_EXTRACTION_PROMPT_TEMPLATE,
    M1M2Extraction,
    M1M2ExtractionError,
    parse_m1_m2_extraction,
    render_extraction_prompt,
)


class TestPromptTemplate:
    """抽出プロンプトテンプレートが必要な内容を含む。"""

    def test_template_contains_conversation_history_placeholder(self) -> None:
        assert "{conversation_history}" in M1_M2_EXTRACTION_PROMPT_TEMPLATE

    def test_template_contains_output_schema(self) -> None:
        assert "axis" in M1_M2_EXTRACTION_PROMPT_TEMPLATE
        assert "outcome" in M1_M2_EXTRACTION_PROMPT_TEMPLATE
        assert "turn" in M1_M2_EXTRACTION_PROMPT_TEMPLATE
        assert "fact" in M1_M2_EXTRACTION_PROMPT_TEMPLATE
        assert "psychology" in M1_M2_EXTRACTION_PROMPT_TEMPLATE
        assert "reward" in M1_M2_EXTRACTION_PROMPT_TEMPLATE

    def test_render_extraction_prompt_inserts_history(self) -> None:
        rendered = render_extraction_prompt(
            conversation_history="System: ...\nUser: でも欲しい\nAssistant: コスト的に損じゃないですか?"
        )
        assert "User: でも欲しい" in rendered
        assert "Assistant: コスト的に損じゃないですか?" in rendered


class TestParseM1M2ExtractionValid:
    """正常な JSON 応答 → M1M2Extraction 返却。"""

    def test_parses_fact_agreed(self) -> None:
        result = parse_m1_m2_extraction(
            json.dumps({"axis": "fact", "outcome": "agreed", "turn": 3})
        )
        assert result.axis == "fact"
        assert result.outcome == "agreed"
        assert result.turn == 3

    def test_parses_psychology_refused(self) -> None:
        result = parse_m1_m2_extraction(
            json.dumps({"axis": "psychology", "outcome": "refused", "turn": 5})
        )
        assert isinstance(result, M1M2Extraction)
        assert result.axis == "psychology"

    def test_parses_reward_ongoing(self) -> None:
        result = parse_m1_m2_extraction(
            json.dumps({"axis": "reward", "outcome": "ongoing", "turn": 1})
        )
        assert result.axis == "reward"
        assert result.outcome == "ongoing"
        assert result.turn == 1


class TestParseM1M2ExtractionInvalid:
    """不正な応答 → M1M2ExtractionError raise。"""

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction("not a json")

    def test_non_object_json_raises(self) -> None:
        """JSON object 以外（配列 / 文字列 / 数値）は raise。"""
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(json.dumps(["fact", "agreed", 3]))

    def test_missing_axis_raises(self) -> None:
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(json.dumps({"outcome": "agreed", "turn": 1}))

    def test_invalid_axis_value_raises(self) -> None:
        """axis が 'fact' / 'psychology' / 'reward' 以外で raise。"""
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(
                json.dumps({"axis": "unknown", "outcome": "agreed", "turn": 1})
            )

    def test_invalid_outcome_value_raises(self) -> None:
        """outcome が 'agreed' / 'refused' / 'ongoing' 以外で raise。"""
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(
                json.dumps({"axis": "fact", "outcome": "maybe", "turn": 1})
            )

    def test_turn_not_int_raises(self) -> None:
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(
                json.dumps({"axis": "fact", "outcome": "agreed", "turn": "three"})
            )

    def test_turn_zero_raises(self) -> None:
        """turn は 1 以上必須。"""
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction(
                json.dumps({"axis": "fact", "outcome": "agreed", "turn": 0})
            )

    def test_empty_string_raises(self) -> None:
        with pytest.raises(M1M2ExtractionError):
            parse_m1_m2_extraction("")
