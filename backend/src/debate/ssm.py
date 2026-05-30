"""LC-D-12 SSM Configuration Loader（Phase 1 Step 2.2 Green、Phase A1 ローカル拡張）。

Strands Agent 起動時に SSM `/yudane/<env>/debate/model-id` を 1 回取得し、
毎セッション開始時に SSM `/yudane/<env>/debate/kill-switch` を取得する薄ラッパー。

ローカルモード（`DEBATE_LOCAL_MODE=true`）では SSM 呼び出しをバイパスし、
環境変数 `DEBATE_LOCAL_MODEL_ID` から model-id を返す（A1 拡張）。

参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md §5
参照: aidlc-docs/construction/unit-3-debate/nfr-design/nfr-design-patterns.md PAT-D-COST-04
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

_LOGGER = logging.getLogger(__name__)
_REGION = "ap-northeast-1"

#: ローカル既定モデル（jp CRIS profile、apne1 で利用可能な Claude Haiku 4.5）
_LOCAL_DEFAULT_MODEL_ID = "jp.anthropic.claude-haiku-4-5-20251001-v1:0"


def _is_local_mode() -> bool:
    """ローカル開発モードか判定する（local_mode.py に依存しないため自前で判定）。"""
    value = os.environ.get("DEBATE_LOCAL_MODE", "").strip().lower()
    return value in ("true", "1", "yes")


@lru_cache(maxsize=1)
def _ssm_client() -> Any:
    """SSM クライアントを 1 回だけ生成する（Lambda コールドスタート最適化）。"""
    return boto3.client("ssm", region_name=_REGION)


def get_model_id(env_name: str) -> str:
    """SSM `/yudane/<env>/debate/model-id` の値を返す（Lambda 起動時 1 回呼び出し想定）。

    ローカルモードでは SSM をバイパスし、環境変数 `DEBATE_LOCAL_MODEL_ID` を返す。
    未設定なら既定値 `jp.anthropic.claude-haiku-4-5-20251001-v1:0`（apne1 CRIS profile）。

    Args:
        env_name: 環境名（dev / staging / prd）。

    Returns:
        Bedrock モデル ID（または inference profile ID）。

    Raises:
        ClientError: SSM 取得失敗時（クラウドモードのみ、model-id は必須）。
    """
    if _is_local_mode():
        return os.environ.get("DEBATE_LOCAL_MODEL_ID", _LOCAL_DEFAULT_MODEL_ID)

    client = _ssm_client()
    parameter_name = f"/yudane/{env_name}/debate/model-id"
    response = client.get_parameter(Name=parameter_name)
    value: str = response["Parameter"]["Value"]
    return value


def is_kill_switch_enabled(env_name: str) -> bool:
    """SSM `/yudane/<env>/debate/kill-switch` の値が 'enabled' なら True を返す。

    毎セッション開始時に呼び出し、リアルタイムで反映する。SSM 例外時は False を返す
    （fail-safe、kill-switch 未設定 = 'disabled' 既定動作、PAT-D-COST-04）。
    ローカルモードでは SSM をバイパスし、常に False を返す（緊急停止が必要な場合は
    プロセスを停止）。

    Args:
        env_name: 環境名（dev / staging / prd）。

    Returns:
        True なら緊急停止モード、False なら通常運用。
    """
    if _is_local_mode():
        return False

    client = _ssm_client()
    parameter_name = f"/yudane/{env_name}/debate/kill-switch"
    try:
        response = client.get_parameter(Name=parameter_name)
        value: str = response["Parameter"]["Value"]
        return value.strip().lower() == "enabled"
    except (ClientError, BotoCoreError) as exc:
        # 構造化ログ（B-12 AuditLogger Lambda Layer 経由を Phase 2 で追加）
        _LOGGER.warning(
            "kill_switch_ssm_read_failed",
            extra={
                "env_name": env_name,
                "parameter_name": parameter_name,
                "error": str(exc),
                "fallback": "disabled",
            },
        )
        return False
