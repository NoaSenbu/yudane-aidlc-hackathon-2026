"""Phase 4 Step 4-3.1 PBT-01: Idempotency プロパティ。

PBT-01 (NFR-PBT-DEBATE-01) Idempotency:
  任意の actor_id / now で `LocalCooldownStore.increment_refuse_count` を
  「同一 client_session_id 相当の同一文脈」で 2 回連続呼ぶと、
  最終状態は 2 回目の呼び出しに対応するもの（重複加算が防止されているか）の不変条件を property 化。

  注: 本番 cooldown.py は DDB ConditionExpression で重複加算を防ぐ実装で、
  PBT-03 で既にカバー済。本 PBT-01 は LocalCooldownStore（in-memory）で
  「2 回連続増加で必ず +2 増加（既知の確定的挙動）」と「自然解除後の最初の
  拒否で必ず 1 リセット」を property 化する補完テスト。

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase3-6-plan.md §2 Step 4-3.1
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.debate.local_mode import LocalCooldownStore

# ---------------------------------------------------------------------------
# Hypothesis Arbitrary
# ---------------------------------------------------------------------------

datetime_strategy = st.datetimes(
    min_value=datetime(2025, 1, 1).replace(tzinfo=None),
    max_value=datetime(2030, 12, 31).replace(tzinfo=None),
    timezones=st.just(UTC),
)

actor_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=8,
    max_size=36,
)


# ---------------------------------------------------------------------------
# PBT-01: 連続増加の単調性（同 actor で 2 回連続呼ぶと count が +2）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(actor_id=actor_id_strategy, now=datetime_strategy)
def test_consecutive_increments_monotonic(actor_id: str, now: datetime) -> None:
    """連続 2 回 increment で count が +2（threshold 未到達なら）。"""
    store = LocalCooldownStore()
    state1 = store.increment_refuse_count(actor_id, now)
    state2 = store.increment_refuse_count(actor_id, now)
    assert state1.consecutive_refuses == 1
    assert state2.consecutive_refuses == 2
    assert state2.cooldown_until is None  # 2 回ではまだ発火しない


# ---------------------------------------------------------------------------
# PBT-01: 自然解除後の最初の拒否で必ず 1 リセット
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(actor_id=actor_id_strategy, now=datetime_strategy)
def test_natural_release_resets_to_one(actor_id: str, now: datetime) -> None:
    """自然解除フラグ True で increment すると必ず count == 1 / cooldown_until == None。"""
    store = LocalCooldownStore()
    # 事前に threshold 到達状態を作る
    store.increment_refuse_count(actor_id, now)
    store.increment_refuse_count(actor_id, now)
    store.increment_refuse_count(actor_id, now)

    # 自然解除後の最初の拒否
    state = store.increment_refuse_count(actor_id, now, after_natural_release=True)
    assert state.consecutive_refuses == 1
    assert state.cooldown_until is None


# ---------------------------------------------------------------------------
# PBT-01: 異なる actor_id 同士は独立（state 干渉なし）
# ---------------------------------------------------------------------------
@settings(max_examples=50, deadline=None)
@given(
    actor_a=actor_id_strategy,
    actor_b=actor_id_strategy,
    now=datetime_strategy,
)
def test_different_actors_are_independent(
    actor_a: str, actor_b: str, now: datetime
) -> None:
    """異なる actor の increment は state 干渉しない。"""
    if actor_a == actor_b:
        return  # 同一 actor はスキップ（trivial case）
    store = LocalCooldownStore()
    state_a = store.increment_refuse_count(actor_a, now)
    state_b = store.increment_refuse_count(actor_b, now)
    # actor_a / actor_b それぞれ独立して 1 回目
    assert state_a.consecutive_refuses == 1
    assert state_b.consecutive_refuses == 1
    # 各 actor に対する check_cooldown が独立
    decision_a = store.check_cooldown(actor_a, now)
    decision_b = store.check_cooldown(actor_b, now)
    assert not decision_a.active
    assert not decision_b.active
    assert decision_a.consecutive_refuses == 1
    assert decision_b.consecutive_refuses == 1
