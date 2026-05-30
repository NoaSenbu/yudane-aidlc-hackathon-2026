"""DebateInvocationPayload / ClientSignals の PBT-02 Round-trip プロパティ（Step 3.5 PBT 補強）。

PBT-02: 任意の有効な payload を model_dump → model_validate で再構築すると同一値が得られる。

参照: aidlc-docs/construction/unit-3-debate/nfr-requirements/nfr-requirements.md NFR-PBT-DEBATE-02
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from backend.src.debate.domain.payloads import (
    DebateInvocationPayload,
)


# ASIN は 10 桁英数字大文字
asin_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=10,
    max_size=10,
)

trigger_strategy = st.sampled_from(["reel_skip", "cart_intercept", "product_dwell"])

action_strategy = st.sampled_from(["start_session", "request_affirmation"])

# user_input は 1〜2000 文字の任意テキスト（制御文字以外）
user_input_strategy = st.text(min_size=1, max_size=2000).filter(
    lambda s: all(ord(c) >= 0x20 or c in "\n\t" for c in s)
)


@given(
    user_input=user_input_strategy,
    asin=asin_strategy,
    trigger=trigger_strategy,
    action=action_strategy,
)
def test_payload_round_trip_preserves_values(
    user_input: str,
    asin: str,
    trigger: str,
    action: str,
) -> None:
    """PBT-02: model_dump → model_validate のラウンドトリップで同一値が得られる。"""
    original_data: dict[str, object] = {
        "action": action,
        "user_input": user_input,
        "asin": asin,
        "trigger": trigger,
    }
    if action == "request_affirmation":
        original_data["outcome"] = "agreed"

    payload_a = DebateInvocationPayload.model_validate(original_data)
    dumped = payload_a.model_dump()
    payload_b = DebateInvocationPayload.model_validate(dumped)

    assert payload_a == payload_b
    assert payload_a.user_input == payload_b.user_input
    assert payload_a.asin == payload_b.asin
    assert payload_a.trigger == payload_b.trigger
    assert payload_a.action == payload_b.action


@given(
    cart_intercepts=st.integers(min_value=0, max_value=100),
    debate_refuses=st.integers(min_value=0, max_value=100),
    late_night=st.booleans(),
    hour_jst=st.integers(min_value=0, max_value=23),
)
def test_client_signals_round_trip(
    cart_intercepts: int,
    debate_refuses: int,
    late_night: bool,
    hour_jst: int,
) -> None:
    """PBT-02: ClientSignals のラウンドトリップで同一値が得られる。"""
    from backend.src.debate.domain.payloads import ClientSignals

    original = ClientSignals(
        recent_cart_intercepts=cart_intercepts,
        recent_debate_refuses=debate_refuses,
        last_signin_at_late_night=late_night,
        current_hour_jst=hour_jst,
    )
    dumped = original.model_dump()
    restored = ClientSignals.model_validate(dumped)
    assert original == restored
