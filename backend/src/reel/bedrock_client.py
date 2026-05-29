"""Bedrock Runtime（Claude Haiku 4.5）の薄いラッパ（B-03 ラベル/コピー生成）。

実 SDK 呼び出しは本クラスに閉じ込め、labels.py へは Protocol で注入する
（テストはフェイク差し替え、NFR R-PAT-LLM-01）。モデル ID は SSM 由来を想定。
ハードタイムアウト 1.5s（呼び出し側で制御）。
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class TextGenerator(Protocol):
    """テキスト生成の抽象（labels.py が依存）。"""

    def generate(self, prompt: str) -> str:
        """プロンプトから 1 応答テキストを生成する。"""
        ...


class BedrockTextGenerator:
    """boto3 bedrock-runtime を用いた実装（薄いラッパ）。

    実 AWS 呼び出しのため単体テストでは使わず、フェイクを注入する。
    """

    def __init__(self, client: Any, model_id: str) -> None:  # noqa: ANN401
        """Bedrock runtime クライアントとモデル ID を受け取る。

        Args:
            client: boto3.client("bedrock-runtime") 相当。
            model_id: SSM 由来のモデル ID（Haiku 4.5）。
        """
        self._client = client
        self._model_id = model_id

    def generate(self, prompt: str) -> str:
        """Messages API でテキスト生成する（最小実装）。"""
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 256,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = self._client.invoke_model(modelId=self._model_id, body=body)
        payload = json.loads(response["body"].read())
        blocks = payload.get("content", [])
        return "".join(b.get("text", "") for b in blocks)
