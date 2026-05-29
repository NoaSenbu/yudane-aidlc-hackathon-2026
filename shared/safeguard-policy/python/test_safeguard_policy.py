"""S-03 SafeguardPolicy の単体テスト + PBT（NFR-PBT-02 / NFR-COV-02）。"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from safeguard_policy import (
    WARN_THRESHOLD_RATIO,
    SafeguardFlags,
    SafeguardInput,
    decide_allow,
)

_NO_FLAGS = SafeguardFlags(cooldown_on=False, quiet_week=False, has_debt=False)


def _make(
    *,
    monthly_limit_yen: int,
    current_budget_used_yen: int,
    flags: SafeguardFlags = _NO_FLAGS,
    transition_count_month: int = 0,
) -> SafeguardInput:
    return SafeguardInput(
        transition_count_month=transition_count_month,
        monthly_limit_yen=monthly_limit_yen,
        current_budget_used_yen=current_budget_used_yen,
        flags=flags,
    )


def test_cooldown_blocks_first() -> None:
    """cooldown は最優先で block。"""
    r = decide_allow(
        _make(
            monthly_limit_yen=100_000,
            current_budget_used_yen=0,
            flags=SafeguardFlags(cooldown_on=True, quiet_week=False, has_debt=False),
        )
    )
    assert r.decision == "block"
    assert r.reason_code == "safeguard.cooldown"


def test_debt_halves_effective_limit() -> None:
    """負債者は実効上限が半減し debt-restricted。"""
    r = decide_allow(
        _make(
            monthly_limit_yen=100_000,
            current_budget_used_yen=60_000,
            flags=SafeguardFlags(cooldown_on=False, quiet_week=False, has_debt=True),
        )
    )
    assert r.effective_limit_yen == 50_000
    assert r.decision == "block"
    assert r.reason_code == "safeguard.debt-restricted"


def test_warn_near_limit() -> None:
    """80% 超で warn。"""
    r = decide_allow(_make(monthly_limit_yen=100_000, current_budget_used_yen=85_000))
    assert r.decision == "warn"
    assert r.reason_code == "safeguard.near-limit"


def test_allow_when_room() -> None:
    """余裕があれば allow。"""
    r = decide_allow(_make(monthly_limit_yen=100_000, current_budget_used_yen=10_000))
    assert r.decision == "allow"


_input_strategy = st.builds(
    SafeguardInput,
    transition_count_month=st.integers(min_value=0, max_value=100),
    monthly_limit_yen=st.integers(min_value=1_000, max_value=1_000_000),
    current_budget_used_yen=st.integers(min_value=0, max_value=2_000_000),
    flags=st.builds(
        SafeguardFlags,
        cooldown_on=st.booleans(),
        quiet_week=st.booleans(),
        has_debt=st.booleans(),
    ),
)


@given(data=_input_strategy)
@settings(max_examples=300)
def test_remaining_non_negative(data: SafeguardInput) -> None:
    """PBT-03: remaining_yen は常に 0 以上。"""
    assert decide_allow(data).remaining_yen >= 0


@given(data=_input_strategy)
@settings(max_examples=300)
def test_effective_limit_not_above_monthly(data: SafeguardInput) -> None:
    """PBT-03: 実効上限は月間上限を超えない。"""
    assert decide_allow(data).effective_limit_yen <= data.monthly_limit_yen


@given(data=_input_strategy)
@settings(max_examples=300)
def test_flag_blocks(data: SafeguardInput) -> None:
    """cooldown/quiet_week が立っていれば必ず block。"""
    if data.flags.cooldown_on or data.flags.quiet_week:
        assert decide_allow(data).decision == "block"


@given(data=_input_strategy)
@settings(max_examples=300)
def test_idempotency(data: SafeguardInput) -> None:
    """PBT-04: 同一入力は同一結果（純関数）。"""
    assert decide_allow(data) == decide_allow(data)


@given(data=_input_strategy)
@settings(max_examples=300)
def test_allow_when_below_warn(data: SafeguardInput) -> None:
    """フラグなしで 80% 未満なら allow。"""
    no_flag = SafeguardInput(
        transition_count_month=data.transition_count_month,
        monthly_limit_yen=data.monthly_limit_yen,
        current_budget_used_yen=data.current_budget_used_yen,
        flags=_NO_FLAGS,
    )
    result = decide_allow(no_flag)
    if no_flag.current_budget_used_yen < no_flag.monthly_limit_yen * WARN_THRESHOLD_RATIO:
        assert result.decision == "allow"
