"""Unit-3 Debate 入力 DTO（Phase 1 Step 3.2 Green）。

`DebateInvocationPayload` は AgentCore Runtime `InvokeAgentRuntimeCommand.payload` で受け取る
JSON（Mobile から送信）。1 つの entrypoint で論破ストリーミングと肯定フィードバック生成の両方を扱うため、
`action` フィールドで分岐する。

参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §2
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md DEBATE / SECURITY-08

不変条件:
    - asin は 10 桁英数字大文字（business-rules ASIN-01）
    - user_input は 2000 文字以下（プロンプト爆発防止）
    - actor_id は payload に含めない（JWT.sub から取得、SECURITY-08）
    - action='request_affirmation' のときのみ outcome='agreed' が必須
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: 論破セッションのトリガー（Reel スキップ / カート介入 / 商品ページ滞在）
DebateTrigger = Literal["reel_skip", "cart_intercept", "product_dwell"]

#: AgentCore entrypoint アクション分岐
DebateAction = Literal["start_session", "request_affirmation"]


class ClientSignals(BaseModel):
    """Mobile が送信するストレス推定用の信号（PII 含まない）。

    Attributes:
        recent_cart_intercepts: 直近 7 日間のカート介入回数。
        recent_debate_refuses: 直近 7 日間の論破拒否回数。
        last_signin_at_late_night: 直近 24h 以内に深夜帯（22-02 JST）サインインしたか。
        current_hour_jst: 現在の JST 時（0-23）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    recent_cart_intercepts: int = Field(default=0, ge=0, le=100)
    recent_debate_refuses: int = Field(default=0, ge=0, le=100)
    last_signin_at_late_night: bool = False
    current_hour_jst: int = Field(..., ge=0, le=23)


class DebateInvocationPayload(BaseModel):
    """論破セッションを起動する Mobile → AgentCore の入力 DTO。

    Attributes:
        action: AgentCore entrypoint の分岐（start_session 既定 / request_affirmation 肯定 FB）。
        user_input: ユーザーの自然文入力（最大 2000 文字、プロンプト爆発防止）。
        asin: Amazon ASIN（10 桁英数字大文字、business-rules ASIN-01）。
        trigger: 論破起動経路（reel_skip / cart_intercept / product_dwell）。
        client_session_id: Mobile 側で生成する ULID（None なら Backend で発番）。
        client_signals: ストレス推定用の信号（任意、PII を含まない）。
        outcome: action='request_affirmation' 時のみ意味を持つ翻意結果（'agreed' のみ）。

    Note:
        `actor_id` は payload に含めない（SECURITY-08）。AgentCore Runtime context.user.sub から
        取得するのが正。攻撃者が actor_id を偽装しても、Pydantic 既定の `extra='ignore'` で破棄される
        （test_actor_id_in_payload_is_ignored で検証）。
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    action: DebateAction = "start_session"
    user_input: str = Field(..., min_length=1, max_length=2000)
    asin: str = Field(..., pattern=r"^[A-Z0-9]{10}$")
    trigger: DebateTrigger
    client_session_id: str | None = Field(default=None, min_length=26, max_length=128)
    client_signals: ClientSignals | None = None
    outcome: Literal["agreed"] | None = None
