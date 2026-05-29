"""負債セーフガード調整ロジックの単体テスト（US-AUTH-03 / DEBT-01〜05）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.src.auth.debt_safeguard import (
    declare_debt,
    evaluate_debt_release,
    request_debt_release,
)
from backend.src.auth.models import SafeguardStateEntity


def _state() -> SafeguardStateEntity:
    return SafeguardStateEntity(user_id="u1", monthly_limit_yen=100_000)


def test_declare_debt_sets_flags() -> None:
    """負債申告で has_debt と冷却が ON（DEBT-01）。"""
    s = declare_debt(_state())
    assert s.flags.has_debt
    assert s.flags.cooldown_on


def test_release_before_cooldown_is_noop() -> None:
    """72h 未満の解除は no-op（DEBT-05）。"""
    now = datetime.fromisoformat("2026-05-30T00:00:00")
    s = declare_debt(_state())
    s = request_debt_release(s, now)
    evaluated = evaluate_debt_release(s, now + timedelta(hours=71))
    assert evaluated.flags.has_debt  # まだ解除されない


def test_release_after_cooldown() -> None:
    """72h 経過後に解除される（DEBT-05）。"""
    now = datetime.fromisoformat("2026-05-30T00:00:00")
    s = declare_debt(_state())
    s = request_debt_release(s, now)
    evaluated = evaluate_debt_release(s, now + timedelta(hours=72))
    assert not evaluated.flags.has_debt
    assert not evaluated.flags.cooldown_on
    assert evaluated.debt_release_requested_at is None


def test_no_request_no_release() -> None:
    """解除リクエストがなければ評価しても変化なし。"""
    now = datetime.fromisoformat("2026-05-30T00:00:00")
    s = declare_debt(_state())
    evaluated = evaluate_debt_release(s, now + timedelta(days=10))
    assert evaluated.flags.has_debt  # リクエストなしなので維持
