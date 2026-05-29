"""ALG-TRANSITION の単体テスト + PBT-04（冪等性 / 上限超過なし / fail-closed）。"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.common.exceptions import DomainError, ErrorCategory
from backend.src.reel.models import AmazonTransitionRequest, ExpAward
from backend.src.reel.transition import record_transition

from safeguard_policy import SafeguardDecision

_MONTH = "2026-05"


class _FakeGate:
    """テスト用 Safeguard ゲート。"""

    def __init__(self, decision: str, reason: str = "allowed", *, raise_exc: bool = False) -> None:
        self._decision = decision
        self._reason = reason
        self._raise = raise_exc

    def evaluate(self, user_id: str) -> SafeguardDecision:
        if self._raise:
            raise RuntimeError("safeguard store down")
        return SafeguardDecision(
            decision=self._decision,  # type: ignore[arg-type]
            reason_code=self._reason,  # type: ignore[arg-type]
            effective_limit_yen=100_000,
            remaining_yen=50_000,
        )


class _FakeRepo:
    """テスト用の冪等永続層（メモリ）。"""

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.month_count = 0
        self.exp = 40

    def record_if_absent(self, req: AmazonTransitionRequest, month_bucket: str) -> bool:
        if req.client_transition_id in self.seen:
            return False
        self.seen.add(req.client_transition_id)
        self.month_count += 1
        return True

    def increment_exp(self, user_id: str, amount: int) -> int:
        self.exp += amount
        return self.exp

    def current_exp(self, user_id: str) -> int:
        return self.exp


def _req(cid: str = "c1") -> AmazonTransitionRequest:
    return AmazonTransitionRequest(
        user_id="u1", card_id="card-1", asin="B0EXAMPLE1", context="reel", client_transition_id=cid
    )


def test_allow_records_and_awards_exp() -> None:
    """allow で記録 + EXP +1。"""
    repo = _FakeRepo()
    result = record_transition(_req(), gate=_FakeGate("allow"), repo=repo, month_bucket=_MONTH)
    assert result == ExpAward(awarded=1, total_exp=41, duplicate=False)
    assert repo.month_count == 1


def test_warn_does_not_block() -> None:
    """warn は遷移を止めない（REEL-TR-04）。"""
    repo = _FakeRepo()
    result = record_transition(_req(), gate=_FakeGate("warn", "safeguard.near-limit"), repo=repo, month_bucket=_MONTH)
    assert result.awarded == 1


def test_block_raises_409_and_no_record() -> None:
    """block は記録せず 409（REEL-TR-03）。"""
    repo = _FakeRepo()
    with pytest.raises(DomainError) as exc:
        record_transition(_req(), gate=_FakeGate("block", "safeguard.monthly-limit-exceeded"), repo=repo, month_bucket=_MONTH)
    assert exc.value.status == 409
    assert exc.value.category is ErrorCategory.SAFEGUARD
    assert repo.month_count == 0


def test_gate_failure_fail_closed() -> None:
    """Safeguard 取得失敗は fail-closed（409、記録しない、NFR-AVAIL-05）。"""
    repo = _FakeRepo()
    with pytest.raises(DomainError) as exc:
        record_transition(_req(), gate=_FakeGate("allow", raise_exc=True), repo=repo, month_bucket=_MONTH)
    assert exc.value.status == 409
    assert repo.month_count == 0


def test_idempotent_duplicate_no_double_count() -> None:
    """同一 clientTransitionId の再送は EXP/カウント二重計上なし（REEL-TR-01 / PBT-04）。"""
    repo = _FakeRepo()
    first = record_transition(_req("dup"), gate=_FakeGate("allow"), repo=repo, month_bucket=_MONTH)
    second = record_transition(_req("dup"), gate=_FakeGate("allow"), repo=repo, month_bucket=_MONTH)
    assert first == ExpAward(awarded=1, total_exp=41, duplicate=False)
    assert second == ExpAward(awarded=0, total_exp=41, duplicate=True)
    assert repo.month_count == 1


# --- PBT-04 ---

@given(n=st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_repeated_same_key_awards_once(n: int) -> None:
    """PBT: 同一 clientTransitionId を N 回送っても EXP 加算は高々 1（PBT-04）。"""
    repo = _FakeRepo()
    results = [
        record_transition(_req("same"), gate=_FakeGate("allow"), repo=repo, month_bucket=_MONTH)
        for _ in range(n)
    ]
    awarded_total = sum(r.awarded for r in results)
    assert awarded_total == 1
    assert repo.month_count == 1


@given(ids=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=20, unique=True))
@settings(max_examples=100)
def test_month_count_equals_unique_ids(ids: list[str]) -> None:
    """PBT: 月間カウントはユニークな冪等キー数に一致（二重計上なし）。"""
    repo = _FakeRepo()
    for cid in ids:
        record_transition(_req(cid), gate=_FakeGate("allow"), repo=repo, month_bucket=_MONTH)
    assert repo.month_count == len(set(ids))
