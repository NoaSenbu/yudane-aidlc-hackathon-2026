"""M-1 / M-2 軸の翻意パターン抽出プロンプト（Phase 4 Step 4-1 Green）。

目的:
  Bedrock Haiku 4.5 で論破セッション履歴から「どの軸（fact / psychology / reward）が
  ヒットして翻意したか」を構造化抽出するプロンプトとレスポンスパース純関数を提供する。
  AgentCore Memory custom Strategy `m1_m2_axis_extractor`（B-303 採用済）が起動時に
  本プロンプトを使用し、抽出結果を `/user/m1m2/{actorId}/` namespace に保存する。

実 Memory custom Strategy の deploy は AWS デプロイ前提（Phase 4 Step 4-2 で CDK
Snapshot のみ追加）。本ファイルは抽出プロンプトとパース純関数のみを提供。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-1
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md MEMORY-04
"""

from __future__ import annotations

import json
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

#: 抽出対象の軸（fact / psychology / reward）。
M1M2Axis = Literal["fact", "psychology", "reward"]

#: 抽出対象の outcome（ユーザーの最終反応）。
M1M2Outcome = Literal["agreed", "refused", "ongoing"]


M1_M2_EXTRACTION_PROMPT_TEMPLATE: Final[
    str
] = """あなたは「YUDANE（委ね）」の M-1 / M-2 軸抽出器です。
以下の論破セッション履歴を読んで、ユーザーの翻意パターンを構造化抽出してください。

# 抽出対象

- axis: ヒットした論破軸（fact / psychology / reward のいずれか 1 つ）
  - fact: 事実 / コスト論証 / データ要求型に反応した
  - psychology: 自己甘やかしの肯定 / 投資・成長フレーミングに反応した
  - reward: ストレス × ご褒美フレーミングに反応した
- outcome: ユーザーの最終反応
  - agreed: 翻意して購買意欲が高まった
  - refused: 拒否し続けた
  - ongoing: まだセッション継続中
- turn: 翻意（または拒否確定）した会話ターン番号（1 始まり、N >= 1）

# 出力スキーマ（JSON 厳守）

```json
{{"axis": "fact" | "psychology" | "reward", "outcome": "agreed" | "refused" | "ongoing", "turn": <整数>}}
```

JSON 以外の前置きや解説は一切出力しないでください。

# 論破セッション履歴

{conversation_history}
"""


class M1M2Extraction(BaseModel):
    """M-1 / M-2 軸抽出結果（value object）。

    Attributes:
        axis: ヒットした論破軸。
        outcome: ユーザー最終反応。
        turn: 翻意 / 拒否確定したターン番号（>= 1）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    axis: M1M2Axis
    outcome: M1M2Outcome
    turn: int = Field(ge=1)


class M1M2ExtractionError(ValueError):
    """`parse_m1_m2_extraction` のパース失敗時に raise される例外。

    呼び出し側は本例外を catch し、抽出失敗としてログ出力 + Memory 書き込みスキップする
    （安全側 fail）。リトライ判定も呼び出し側に委ねる。
    """


def render_extraction_prompt(*, conversation_history: str) -> str:
    """抽出プロンプトを組み立てる純関数。

    Args:
        conversation_history: 論破セッションの会話履歴（システム / ユーザー / アシスタントの
            ターンをそのまま連結した文字列）。

    Returns:
        抽出プロンプトテキスト（{conversation_history} を埋め込み済み）。
    """
    return M1_M2_EXTRACTION_PROMPT_TEMPLATE.format(
        conversation_history=conversation_history
    )


def parse_m1_m2_extraction(json_response: str) -> M1M2Extraction:
    """Bedrock Haiku 4.5 の JSON 応答をパースして M1M2Extraction を返す純関数。

    Args:
        json_response: Bedrock 応答の生 JSON 文字列。

    Returns:
        M1M2Extraction value object。

    Raises:
        M1M2ExtractionError: JSON 解析失敗 / 必須キー欠損 / 不正な axis or outcome 値 /
            turn が int でない / turn < 1。

    不変条件:
        - 戻り値の axis は必ず {'fact', 'psychology', 'reward'} のいずれか
        - 戻り値の outcome は必ず {'agreed', 'refused', 'ongoing'} のいずれか
        - 戻り値の turn は >= 1
    """
    try:
        data = json.loads(json_response)
    except json.JSONDecodeError as exc:
        raise M1M2ExtractionError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise M1M2ExtractionError(f"expected JSON object, got {type(data).__name__}")

    try:
        return M1M2Extraction.model_validate(data)
    except ValidationError as exc:
        raise M1M2ExtractionError(f"validation failed: {exc.errors()}") from exc


__all__ = [
    "M1_M2_EXTRACTION_PROMPT_TEMPLATE",
    "M1M2Axis",
    "M1M2Extraction",
    "M1M2ExtractionError",
    "M1M2Outcome",
    "parse_m1_m2_extraction",
    "render_extraction_prompt",
]
