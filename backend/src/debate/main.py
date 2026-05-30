"""Unit-3 Debate AgentCore Runtime entrypoint（Phase 2 Step 3.2 Green、Strands Agent 統合）。

AgentCore Runtime にデプロイされる Strands Agent のエントリポイント。Phase 2 では:
  1. parse_jwt_actor_id でCognito JWT.sub を取得（PAT-D-SEC-01）
  2. SSM kill-switch チェック（PAT-D-COST-04）
  3. payload 検証（DebateInvocationPayload、SECURITY-08 で actor_id 偽装破棄）
  4. action='refuse' は increment_refuse_count を呼んで終了
  5. クールダウン判定（cost-protective、PAT-D-COST-01）
  6. ストレスレベル推定 → プロンプト合成 → Strands Agent.stream_async() で論破ストリーミング

Strands SDK / bedrock-agentcore SDK は **lazy import + DI** でテスト容易性を確保。
本番では `_get_strands_agent()` が SDK 経由で実 Agent を返すが、テストでは
`patch.object(main, "_get_strands_agent")` でモック差し替え可能。

参照: aidlc-docs/construction/unit-3-debate/functional-design/strands-agent-design.md §1
参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 3
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from backend.src.debate.cooldown import check_cooldown, increment_refuse_count
from backend.src.debate.domain.memory_context import (
    MemoryContext,
    empty_memory_context,
)
from backend.src.debate.domain.payloads import DebateInvocationPayload
from backend.src.debate.domain.results import CooldownDecision, CooldownState
from backend.src.debate.graceful_shutdown import (
    DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS,
    check_graceful_shutdown_status,
)
from backend.src.debate.local_mode import (
    get_local_cooldown_store,
    get_local_memory_store,
    is_local_mode,
    local_parse_jwt_actor_id,
)
from backend.src.debate.moderation import check_text_for_ng_patterns
from backend.src.debate.prompts.compose import compose_debate_prompt
from backend.src.debate.ssm import get_model_id, is_kill_switch_enabled
from backend.src.debate.stress import estimate_stress_level

_LOGGER = logging.getLogger(__name__)

# 起動時 1 回だけ SSM から model_id 取得（Q4=A+SSM、Phase 2 で agent.stream_async に渡す）。
# テスト時は ENV_NAME 未設定のため lazy 評価。
_MODEL_ID: str | None = None
_COOLDOWNS_TABLE_NAME: str | None = None
_STRANDS_AGENT: Any = None  # Strands Agent インスタンス（lazy init）


def _get_env_name() -> str:
    """環境名を取得。ENV_NAME 未設定時は dev を既定値に。"""
    return os.environ.get("ENV_NAME", "dev")


def _get_cooldowns_table_name() -> str:
    """Cooldowns DDB テーブル名（環境変数または既定値）。"""
    global _COOLDOWNS_TABLE_NAME
    if _COOLDOWNS_TABLE_NAME is None:
        _COOLDOWNS_TABLE_NAME = os.environ.get(
            "COOLDOWNS_TABLE_NAME",
            f"yudane-debate-{_get_env_name()}-cooldowns",
        )
    return _COOLDOWNS_TABLE_NAME


def _get_model_id_lazy() -> str:
    """Bedrock モデル ID の遅延取得（起動時のみ SSM 呼び出し）。"""
    global _MODEL_ID
    if _MODEL_ID is None:
        _MODEL_ID = get_model_id(env_name=_get_env_name())
    return _MODEL_ID


def _get_strands_agent() -> Any:
    """Strands Agent インスタンスを lazy 取得する（DI ポイント、テストでモック差し替え可能）。

    Phase 2 では Strands SDK を実 import し、`Agent(model=MODEL_ID, callback_handler=None)` を
    1 回だけ生成して再利用する。Phase 3 で MemoryHook + Bedrock Guardrails を追加する。

    Returns:
        Strands Agent インスタンス（実 SDK が未 install の場合は ImportError を伝播）。

    Note:
        テストでは `patch.object(main, "_get_strands_agent")` で MagicMock を返すように差し替え、
        実 SDK / 実 Bedrock 呼び出しを回避する。
    """
    global _STRANDS_AGENT
    if _STRANDS_AGENT is not None:
        return _STRANDS_AGENT

    # 実 SDK の lazy import（pip install strands-agents が必要、Phase 2 Step 4 のローカルモードで対応）
    from strands import Agent  # type: ignore[import-not-found]

    _STRANDS_AGENT = Agent(
        model=_get_model_id_lazy(),
        callback_handler=None,
        # Phase 3 で hooks=[DebateMemoryHook()] / bedrock_kwargs={"guardrailIdentifier": ...} を追加
    )
    return _STRANDS_AGENT


def parse_jwt_actor_id(context: Any) -> str | None:
    """AgentCore Runtime context から actor_id (JWT.sub) を取得する（PAT-D-SEC-01）。

    Cognito Authorizer が発行した context.user.sub のみを正とする。
    payload に含まれる actor_id は Pydantic の `extra='ignore'` で破棄される（SECURITY-08）。

    **ローカルモード**（`DEBATE_LOCAL_MODE=true`）の場合、JWT 認証をバイパスして
    dummy `'local-user'` を返す（L2 MVP 動作確認のため）。

    Args:
        context: AgentCore Runtime の context オブジェクト。

    Returns:
        Cognito JWT.sub（actor_id）、または取得不能なら None（auth.unauthenticated）。
    """
    # ローカルモードでは JWT バイパス
    if is_local_mode():
        return local_parse_jwt_actor_id()

    user = getattr(context, "user", None)
    if user is None:
        return None
    sub = getattr(user, "sub", None)
    if not isinstance(sub, str) or not sub:
        return None
    return sub


def _check_cooldown_dispatcher(actor_id: str, now: datetime) -> CooldownDecision:
    """ローカルモード / 本番モードに応じて Cooldown 判定をディスパッチする。"""
    if is_local_mode():
        return get_local_cooldown_store().check_cooldown(actor_id, now)
    return check_cooldown(
        actor_id=actor_id,
        now=now,
        table_name=_get_cooldowns_table_name(),
    )


def _increment_refuse_count_dispatcher(
    actor_id: str,
    now: datetime,
    *,
    after_natural_release: bool = False,
) -> CooldownState:
    """ローカルモード / 本番モードに応じて拒否カウント加算をディスパッチする。"""
    if is_local_mode():
        return get_local_cooldown_store().increment_refuse_count(
            actor_id, now, after_natural_release=after_natural_release
        )
    return increment_refuse_count(
        actor_id=actor_id,
        now=now,
        table_name=_get_cooldowns_table_name(),
        after_natural_release=after_natural_release,
    )


async def _build_memory_context(actor_id: str) -> MemoryContext:
    """MemoryHook 経由で MemoryContext を構築する。

    ローカルモード時は LocalMemoryStore（empty MemoryContext）を返す。
    本番モードでは Phase 2 では empty を返す（fail-safe、Memory retrieve は Phase 3 で結線）。

    Args:
        actor_id: Cognito JWT.sub。namespace 構築に使用。

    Returns:
        MemoryContext（Phase 2 では empty、Phase 3 で実 Memory retrieve に置換）。
    """
    if is_local_mode():
        return await get_local_memory_store().build_memory_context(actor_id)

    # Phase 2 本番モードでも empty を返す（fail-safe）。
    # Phase 3 で MemoryHook 経由で `retrieve_memories(namespace=f'/user/debate/{actor_id}/')` 等を呼ぶ。
    _ = actor_id  # 未使用警告抑制（Phase 3 で実装時に削除）
    return empty_memory_context()


async def _run_streaming_agent(
    actor_id: str,
    invocation: DebateInvocationPayload,
    now: datetime,
) -> AsyncIterator[dict[str, Any]]:
    """Strands Agent 経由で Bedrock Haiku 4.5 streaming を実行する（Phase 2 Step 3.2 / Phase 3 Step 3-1.2）。

    フロー:
        1. ストレスレベル推定（client_signals + Memory）
        2. MemoryContext 構築（Phase 2 では empty）
        3. プロンプト合成（M-1 + M-2 併走、PBT-03 不変条件）
        4. Strands Agent.stream_async() で Bedrock Haiku 4.5 streaming
        5. 各 chunk yield 後に経過時間をチェックし、80 秒で graceful shutdown 発火、90 秒で hard cutoff
        6. Strands native event を Mobile 互換 StrandsStreamEvent dict に変換して yield
    """
    # 1. ストレスレベル推定
    stress_result = estimate_stress_level(
        actor_id=actor_id,
        now=now,
        client_signals=invocation.client_signals,
        memory_signals=None,  # Phase 2 では empty、Phase 3 で Memory retrieve 経由
    )
    _LOGGER.info(
        "stress_estimated",
        extra={
            "actor_id": actor_id,
            "level": stress_result.level,
            "score": stress_result.score,
        },
    )

    # 2. MemoryContext 構築（Phase 2 では empty）
    memory_context = await _build_memory_context(actor_id)

    # 3. プロンプト合成
    composed = compose_debate_prompt(
        user_input=invocation.user_input,
        asin=invocation.asin,
        stress_level=stress_result.level,
        memory_context=memory_context,
    )
    _LOGGER.info(
        "prompt_composed",
        extra={
            "actor_id": actor_id,
            "axes": composed.axes,
            "text_length": len(composed.text),
        },
    )

    # 4. Strands Agent streaming + graceful shutdown 80s（Phase 3 Step 3-1.2）
    agent = _get_strands_agent()
    started_at = now
    graceful_shutdown_yielded = False
    completion_reason = "agent_completed"

    async for native_event in agent.stream_async(composed.text):
        # 経過時間チェック（_now_for_session で時刻を取得、テスト容易性のため関数化）
        current = _now_for_session()
        status = check_graceful_shutdown_status(started_at, current)

        if status == "hard_cutoff":
            # 90 秒以上経過 → hard cutoff、現在の chunk は捨てて終了
            completion_reason = "hard_timeout"
            break

        if status == "graceful_shutdown" and not graceful_shutdown_yielded:
            # 80 秒経過 → graceful shutdown 発火（1 回のみ）
            graceful_shutdown_yielded = True
            elapsed = (current - started_at).total_seconds()
            yield {
                "type": "graceful_shutdown_initiated",
                "metadata": {"elapsed_seconds": int(elapsed)},
            }
            # サマリ生成（agent.invoke_async で 1〜2 文）
            try:
                summary = await asyncio.wait_for(
                    agent.invoke_async(
                        "ここまでの論破サマリを 1〜2 文で生成。"
                        "トーンは論理優位ディベート系（敬語、〜じゃないですか? / "
                        "結局 / 論理的に / データあるんですか?）、"
                        "未確定の論破軸を含めない",
                    ),
                    timeout=DEBATE_GRACEFUL_SUMMARY_TIMEOUT_SECONDS,
                )
                if isinstance(summary, str) and summary:
                    yield {
                        "type": "summary",
                        "delta_text": summary,
                    }
            except (TimeoutError, Exception) as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "graceful_summary_failed",
                    extra={"error": str(exc)},
                )
            completion_reason = "graceful_timeout"
            break

        # 通常 chunk を変換して yield
        converted = _convert_strands_event(native_event)
        if converted is not None:
            yield converted

    # 5. session_complete を最後に yield
    yield {
        "type": "session_complete",
        "metadata": {"reason": completion_reason},
    }


def _now_for_session() -> datetime:
    """セッション中の現在時刻（テスト容易性のため関数化、本番は datetime.now(UTC)）。"""
    return datetime.now(UTC)


def _convert_strands_event(native_event: dict[str, Any]) -> dict[str, Any] | None:
    """Strands native event を Mobile 互換 StrandsStreamEvent dict に変換する純関数。

    Strands native event 形式（公式 docs:
    https://strandsagents.com/docs/user-guide/concepts/streaming/async-iterators/）:
        - `{"data": "...text chunk..."}`        → text streaming chunk
        - `{"event": ...}` / `{"current_tool_use": ...}` 等 → 内部イベント（無視）

    Mobile 互換 StrandsStreamEvent:
        - `{"type": "token", "delta_text": "..."}`
        - `{"type": "moderation_blocked", "metadata": {"pattern_id": ..., "pattern_name": ...}}`

    Phase 3 Step 3-2.3: text chunk に対して第 3 層モデレーション（NG-3 / NG-6 系正規表現）を
    実行し、検出時は `moderation_blocked` event を返す（token への変換は行わない、
    NG 文言を Mobile 側に流出させない）。SECURITY-08 / business-rules MOD-01〜03 と整合。

    Args:
        native_event: Strands Agent.stream_async() が yield する dict。

    Returns:
        Mobile 互換 dict、無視すべき内部 event は None。
    """
    if not isinstance(native_event, dict):
        return None

    # text chunk: {"data": "..."}
    if "data" in native_event:
        delta = native_event["data"]
        if isinstance(delta, str) and delta:
            # Phase 3 Step 3-2.3: 第 3 層モデレーション
            ng = check_text_for_ng_patterns(delta)
            if ng is not None:
                # NG パターン検出 → moderation_blocked event。
                # 注: matched_text は NgDetection 内には残るが、Mobile に返す
                # metadata には含めない（PII / NG 文言の Telemetry 流出防止、SECURITY-08）
                return {
                    "type": "moderation_blocked",
                    "metadata": {
                        "pattern_id": ng.pattern_id,
                        "pattern_name": ng.pattern_name,
                    },
                }
            return {
                "type": "token",
                "delta_text": delta,
            }

    # 他の内部 event（current_tool_use / event etc.）は Phase 2 では無視。
    # Phase 3 で `tool_use` 等の拡張 EventType に変換する。
    return None


async def debate_handler(
    payload: dict[str, Any],
    context: Any,
    *,
    now: datetime | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """論破セッションのメインハンドラ（Phase 2 Strands Agent 統合）。

    実装フロー:
        1. SSM kill-switch チェック（fail-fast、PAT-D-COST-04）
        2. JWT actor_id 解決（auth.unauthenticated は早期 return）
        3. DebateInvocationPayload 検証（payload.invalid は早期 return）
        4. action='refuse' は increment_refuse_count を呼んで debate.refused yield
        5. action='request_affirmation' は Phase 4 で実装（Phase 2 では未対応）
        6. クールダウン判定（active なら debate.cooldown_triggered + Strands 呼ばない）
        7. Strands Agent streaming（M-1 + M-2 併走プロンプト経由）

    Args:
        payload: AgentCore Runtime InvokeAgentRuntimeCommand.payload（JSON）。
        context: AgentCore Runtime context（user.sub から actor_id 取得）。
        now: 現在時刻（テスト容易性のため引数化、本番は None で utcnow を使用）。

    Yields:
        StrandsStreamEvent 互換の dict（type / delta_text / metadata）。
    """
    if now is None:
        now = datetime.now(UTC)

    env_name = _get_env_name()

    # 1. kill-switch チェック（fail-fast、Strands 呼ばない、PAT-D-COST-04）
    if is_kill_switch_enabled(env_name):
        yield {"type": "error", "metadata": {"reason": "kill_switch.enabled"}}
        return

    # 2. JWT actor_id 解決（PAT-D-SEC-01）
    actor_id = parse_jwt_actor_id(context)
    if actor_id is None:
        yield {"type": "error", "metadata": {"reason": "auth.unauthenticated"}}
        return

    # 3. payload 検証（SECURITY-08: actor_id を payload に入れても extra='ignore' で破棄）
    # 注: action='refuse' は DebateInvocationPayload のスキーマにない（Phase 2 拡張）ため、
    #     payload.get('action') を検証より前に確認する。
    raw_action = payload.get("action")

    # 4. action='refuse' は increment_refuse_count を呼んで終了
    if raw_action == "refuse":
        async for evt in _handle_refuse(actor_id, now):
            yield evt
        return

    try:
        invocation = DebateInvocationPayload.model_validate(payload)
    except ValidationError as exc:
        _LOGGER.warning(
            "payload_validation_failed",
            extra={"actor_id": actor_id, "errors": exc.errors()},
        )
        yield {"type": "error", "metadata": {"reason": "payload.invalid"}}
        return

    # 5. action='request_affirmation' は Phase 4 で実装
    if invocation.action == "request_affirmation":
        yield {
            "type": "error",
            "metadata": {"reason": "affirmation.not_implemented_in_phase2"},
        }
        return

    # 6. クールダウン判定（Strands 呼ぶ前に必ず確認、PAT-D-COST-01）
    decision: CooldownDecision = _check_cooldown_dispatcher(actor_id, now)
    if decision.active and decision.cooldown_until is not None:
        yield {
            "type": "debate.cooldown_triggered",
            "metadata": {
                "cooldown_until": decision.cooldown_until.isoformat(),
            },
        }
        return

    # 7. Strands Agent streaming（M-1 + M-2 併走プロンプト経由）
    async for event in _run_streaming_agent(actor_id, invocation, now):
        yield event


async def _handle_refuse(actor_id: str, now: datetime) -> AsyncIterator[dict[str, Any]]:
    """action='refuse' 時のハンドラ。increment_refuse_count を呼んで debate.refused を yield。

    PBT-04 idempotency 関連: 同一 client_session_id で 2 回 'refuse' が来ても、
    DDB ConditionExpression で重複加算を防ぐ（cooldown.py の実装に委譲）。

    Args:
        actor_id: Cognito JWT.sub。
        now: 現在時刻。

    Yields:
        debate.refused event（cooldownTriggered=true / consecutiveRefuses を含む）。
    """
    state = _increment_refuse_count_dispatcher(
        actor_id=actor_id,
        now=now,
        after_natural_release=False,
    )
    metadata: dict[str, Any] = {
        "consecutive_refuses": state.consecutive_refuses,
    }
    if state.cooldown_until is not None:
        metadata["cooldown_until"] = state.cooldown_until.isoformat()
        metadata["cooldown_triggered"] = True
    else:
        metadata["cooldown_triggered"] = False

    yield {
        "type": "debate.refused",
        "metadata": metadata,
    }


__all__ = [
    "debate_handler",
    "increment_refuse_count",  # 再エクスポート（Phase 2 Step 3 結線済）
    "parse_jwt_actor_id",
]
