"""Unit-3 Debate SSM Configuration Loader のテスト（Phase 1 Step 2.1 Red）。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 2
参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md §5
"""

from __future__ import annotations

from unittest.mock import patch

import boto3
import pytest
from botocore.stub import Stubber

from backend.src.debate import ssm


@pytest.fixture
def ssm_client_stub() -> tuple[object, Stubber]:
    """boto3 SSM クライアントを Stubber でモックする。"""
    client = boto3.client("ssm", region_name="ap-northeast-1")
    stub = Stubber(client)
    stub.activate()
    return client, stub


def test_get_model_id_returns_value_from_ssm(
    ssm_client_stub: tuple[object, Stubber],
) -> None:
    """SSM `/yudane/dev/debate/model-id` の値を返す。"""
    client, stub = ssm_client_stub
    stub.add_response(
        "get_parameter",
        {
            "Parameter": {
                "Name": "/yudane/dev/debate/model-id",
                "Type": "String",
                "Value": "anthropic.claude-haiku-4-5",
            }
        },
        expected_params={"Name": "/yudane/dev/debate/model-id"},
    )

    with patch.object(ssm, "_ssm_client", return_value=client):
        result = ssm.get_model_id("dev")

    assert result == "anthropic.claude-haiku-4-5"
    stub.assert_no_pending_responses()


def test_is_kill_switch_enabled_returns_true_for_enabled(
    ssm_client_stub: tuple[object, Stubber],
) -> None:
    """SSM `/yudane/dev/debate/kill-switch` 値 'enabled' で True を返す。"""
    client, stub = ssm_client_stub
    stub.add_response(
        "get_parameter",
        {
            "Parameter": {
                "Name": "/yudane/dev/debate/kill-switch",
                "Type": "String",
                "Value": "enabled",
            }
        },
        expected_params={"Name": "/yudane/dev/debate/kill-switch"},
    )

    with patch.object(ssm, "_ssm_client", return_value=client):
        result = ssm.is_kill_switch_enabled("dev")

    assert result is True
    stub.assert_no_pending_responses()


def test_is_kill_switch_enabled_returns_false_for_disabled(
    ssm_client_stub: tuple[object, Stubber],
) -> None:
    """値 'disabled' で False を返す。"""
    client, stub = ssm_client_stub
    stub.add_response(
        "get_parameter",
        {
            "Parameter": {
                "Name": "/yudane/dev/debate/kill-switch",
                "Type": "String",
                "Value": "disabled",
            }
        },
        expected_params={"Name": "/yudane/dev/debate/kill-switch"},
    )

    with patch.object(ssm, "_ssm_client", return_value=client):
        result = ssm.is_kill_switch_enabled("dev")

    assert result is False
    stub.assert_no_pending_responses()


def test_is_kill_switch_enabled_returns_false_on_ssm_exception(
    ssm_client_stub: tuple[object, Stubber],
) -> None:
    """SSM 例外時に fail-safe で False を返す（kill-switch 未設定 = 'disabled' 既定動作）。"""
    client, stub = ssm_client_stub
    stub.add_client_error(
        "get_parameter",
        service_error_code="ParameterNotFound",
        service_message="Parameter not found",
        expected_params={"Name": "/yudane/dev/debate/kill-switch"},
    )

    with patch.object(ssm, "_ssm_client", return_value=client):
        result = ssm.is_kill_switch_enabled("dev")

    assert result is False
    stub.assert_no_pending_responses()


def test_get_model_id_uses_env_specific_path(
    ssm_client_stub: tuple[object, Stubber],
) -> None:
    """env 名で SSM パスが切り替わる（dev / staging / prd）。"""
    client, stub = ssm_client_stub
    stub.add_response(
        "get_parameter",
        {
            "Parameter": {
                "Name": "/yudane/prd/debate/model-id",
                "Type": "String",
                "Value": "anthropic.claude-sonnet-4-6",
            }
        },
        expected_params={"Name": "/yudane/prd/debate/model-id"},
    )

    with patch.object(ssm, "_ssm_client", return_value=client):
        result = ssm.get_model_id("prd")

    assert result == "anthropic.claude-sonnet-4-6"
    stub.assert_no_pending_responses()


# ---------------------------------------------------------------------------
# Phase A1 拡張: ローカルモード（DEBATE_LOCAL_MODE=true）で SSM をバイパスする
# ---------------------------------------------------------------------------


def test_get_model_id_returns_local_model_in_local_mode(monkeypatch) -> None:
    """ローカルモード時は SSM をバイパスし環境変数 DEBATE_LOCAL_MODEL_ID を返す。"""
    monkeypatch.setenv("DEBATE_LOCAL_MODE", "true")
    monkeypatch.setenv(
        "DEBATE_LOCAL_MODEL_ID", "jp.anthropic.claude-haiku-4-5-20251001-v1:0"
    )

    result = ssm.get_model_id("dev")
    assert result == "jp.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_get_model_id_uses_default_when_env_unset(monkeypatch) -> None:
    """ローカルモードで DEBATE_LOCAL_MODEL_ID 未設定時は jp CRIS profile 既定値を返す。"""
    monkeypatch.setenv("DEBATE_LOCAL_MODE", "true")
    monkeypatch.delenv("DEBATE_LOCAL_MODEL_ID", raising=False)

    result = ssm.get_model_id("dev")
    assert result == "jp.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_is_kill_switch_returns_false_in_local_mode(monkeypatch) -> None:
    """ローカルモードでは kill-switch 判定をバイパスし常に False を返す（SSM 呼ばない）。"""
    monkeypatch.setenv("DEBATE_LOCAL_MODE", "true")

    result = ssm.is_kill_switch_enabled("dev")
    assert result is False
