"""Unit-3 Debate ドメインモデル DebateInvocationPayload / ClientSignals のテスト（Step 3.1 Red）。

参照: domain-entities.md §2.1 / §2.2
参照: business-rules.md DEBATE / SECURITY-08 (actor_id を payload に含めない)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.src.debate.domain.payloads import ClientSignals, DebateInvocationPayload


class TestDebateInvocationPayload:
    """DebateInvocationPayload の妥当性検証。"""

    def test_valid_start_session_payload(self) -> None:
        """action='start_session' で正しく検証される。"""
        payload = DebateInvocationPayload.model_validate(
            {
                "action": "start_session",
                "user_input": "でも欲しい",
                "asin": "B01ABC1234",
                "trigger": "reel_skip",
            }
        )
        assert payload.action == "start_session"
        assert payload.user_input == "でも欲しい"
        assert payload.asin == "B01ABC1234"
        assert payload.trigger == "reel_skip"
        assert payload.client_session_id is None
        assert payload.client_signals is None
        assert payload.outcome is None

    def test_default_action_is_start_session(self) -> None:
        """action 省略時は 'start_session' が既定値。"""
        payload = DebateInvocationPayload.model_validate(
            {
                "user_input": "迷う",
                "asin": "B01ABC1234",
                "trigger": "cart_intercept",
            }
        )
        assert payload.action == "start_session"

    def test_request_affirmation_with_outcome(self) -> None:
        """action='request_affirmation' で outcome='agreed' を受け付ける。"""
        payload = DebateInvocationPayload.model_validate(
            {
                "action": "request_affirmation",
                "user_input": "買うことにした",
                "asin": "B01ABC1234",
                "trigger": "reel_skip",
                "outcome": "agreed",
            }
        )
        assert payload.action == "request_affirmation"
        assert payload.outcome == "agreed"

    def test_actor_id_in_payload_is_ignored(self) -> None:
        """payload に actor_id を入れても無視される（SECURITY-08）。

        Pydantic v2 の既定では未定義フィールドは ignore される（extra='ignore'）。
        actor_id は JWT.sub から取得するのが正で、payload 経由は不可。
        """
        payload = DebateInvocationPayload.model_validate(
            {
                "actor_id": "attacker_user_id",  # 攻撃者が偽装した actor_id
                "user_input": "なりすまし",
                "asin": "B01ABC1234",
                "trigger": "reel_skip",
            }
        )
        # actor_id 属性自体が存在しない（payload 経由では取得不可）
        assert not hasattr(payload, "actor_id")

    @pytest.mark.parametrize(
        "invalid_asin",
        [
            "b01abc1234",  # 小文字含む
            "B01ABC123",  # 9 桁
            "B01ABC12345",  # 11 桁
            "B01ABC-234",  # ハイフン含む
            "",  # 空文字
        ],
    )
    def test_invalid_asin_raises(self, invalid_asin: str) -> None:
        """asin が 10 桁英数字大文字以外で ValidationError。"""
        with pytest.raises(ValidationError):
            DebateInvocationPayload.model_validate(
                {
                    "user_input": "テスト",
                    "asin": invalid_asin,
                    "trigger": "reel_skip",
                }
            )

    def test_user_input_over_2000_chars_raises(self) -> None:
        """user_input が 2000 文字超で ValidationError（プロンプト爆発防止）。"""
        with pytest.raises(ValidationError):
            DebateInvocationPayload.model_validate(
                {
                    "user_input": "あ" * 2001,
                    "asin": "B01ABC1234",
                    "trigger": "reel_skip",
                }
            )

    def test_empty_user_input_raises(self) -> None:
        """user_input が空文字で ValidationError。"""
        with pytest.raises(ValidationError):
            DebateInvocationPayload.model_validate(
                {
                    "user_input": "",
                    "asin": "B01ABC1234",
                    "trigger": "reel_skip",
                }
            )

    @pytest.mark.parametrize(
        "invalid_trigger",
        ["unknown_trigger", "REEL_SKIP", "share_extension", ""],
    )
    def test_invalid_trigger_raises(self, invalid_trigger: str) -> None:
        """trigger が許可されたリテラル以外で ValidationError。"""
        with pytest.raises(ValidationError):
            DebateInvocationPayload.model_validate(
                {
                    "user_input": "テスト",
                    "asin": "B01ABC1234",
                    "trigger": invalid_trigger,
                }
            )

    def test_with_client_signals(self) -> None:
        """client_signals を含むペイロードを正しく検証する。"""
        payload = DebateInvocationPayload.model_validate(
            {
                "user_input": "迷う",
                "asin": "B01ABC1234",
                "trigger": "reel_skip",
                "client_signals": {
                    "recent_cart_intercepts": 3,
                    "recent_debate_refuses": 1,
                    "last_signin_at_late_night": True,
                    "current_hour_jst": 23,
                },
            }
        )
        assert payload.client_signals is not None
        assert payload.client_signals.recent_cart_intercepts == 3
        assert payload.client_signals.current_hour_jst == 23


class TestClientSignals:
    """ClientSignals の妥当性検証。"""

    def test_valid_signals(self) -> None:
        """正常な信号は受理される。"""
        signals = ClientSignals.model_validate(
            {
                "recent_cart_intercepts": 5,
                "recent_debate_refuses": 2,
                "last_signin_at_late_night": False,
                "current_hour_jst": 12,
            }
        )
        assert signals.recent_cart_intercepts == 5
        assert signals.current_hour_jst == 12

    @pytest.mark.parametrize("hour", [-1, 24, 100])
    def test_invalid_hour_raises(self, hour: int) -> None:
        """current_hour_jst の範囲外で ValidationError。"""
        with pytest.raises(ValidationError):
            ClientSignals.model_validate(
                {
                    "recent_cart_intercepts": 0,
                    "recent_debate_refuses": 0,
                    "last_signin_at_late_night": False,
                    "current_hour_jst": hour,
                }
            )

    @pytest.mark.parametrize("count", [-1, 101])
    def test_count_out_of_range_raises(self, count: int) -> None:
        """recent_cart_intercepts / recent_debate_refuses の範囲外で ValidationError。"""
        with pytest.raises(ValidationError):
            ClientSignals.model_validate(
                {
                    "recent_cart_intercepts": count,
                    "recent_debate_refuses": 0,
                    "last_signin_at_late_night": False,
                    "current_hour_jst": 12,
                }
            )
