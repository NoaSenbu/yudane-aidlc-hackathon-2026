"""Unit-3 Debate ローカル開発モード（Phase 2 Step 4.2 Green、L2 MVP のため）。

`agentcore dev --port 8080` 起動時に DDB Cooldowns / AgentCore Memory を **in-memory dict** で
代替する切替フラグ。実 Bedrock は呼び出す（L2 構成）。`moto` は使わず軽量な Protocol-based DI。

環境変数:
    DEBATE_LOCAL_MODE=true|false     # 既定 false、true でローカルモード有効化
    LOCAL_USER_ID                    # 既定 'local-user'、JWT 認証バイパス時の actor_id

参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase2-plan.md §1 Step 4
参照: aidlc-docs/construction/unit-3-debate/code/local-dev-guide.md
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from backend.src.debate.domain.memory_context import (
    MemoryContext,
    empty_memory_context,
)
from backend.src.debate.domain.results import CooldownDecision, CooldownState

_LOGGER = logging.getLogger(__name__)

#: 環境変数フラグ
_LOCAL_MODE_ENV: str = "DEBATE_LOCAL_MODE"
_LOCAL_USER_ID_ENV: str = "LOCAL_USER_ID"

#: ローカルモードのデフォルト actor_id
_LOCAL_USER_ID_DEFAULT: str = "local-user"


def is_local_mode() -> bool:
    """ローカル開発モードか判定する。

    環境変数 `DEBATE_LOCAL_MODE` が `'true'` / `'1'` / `'yes'` のいずれかなら True。
    既定（未設定 / 空文字 / `'false'`）は False。
    """
    value = os.environ.get(_LOCAL_MODE_ENV, "").strip().lower()
    return value in ("true", "1", "yes")


def local_parse_jwt_actor_id() -> str:
    """ローカルモード時に JWT 認証をバイパスして dummy actor_id を返す。"""
    return os.environ.get(_LOCAL_USER_ID_ENV, _LOCAL_USER_ID_DEFAULT)


class LocalCooldownStore:
    """in-memory dict で Cooldowns を代替するローカル実装。

    本番の `cooldown.check_cooldown` / `cooldown.increment_refuse_count` と同じシグネチャを
    `CooldownStoreProtocol` で満たす。プロセス再起動でリセットされる。
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def check_cooldown(
        self,
        actor_id: str,
        now: datetime,
    ) -> CooldownDecision:
        """in-memory dict から Cooldown 状態を判定する。"""
        record = self._records.get(actor_id)
        if record is None:
            return CooldownDecision(
                active=False, cooldown_until=None, consecutive_refuses=0
            )

        cooldown_until = record.get("cooldown_until")
        consecutive_refuses = record.get("consecutive_refuses", 0)

        if cooldown_until is None:
            return CooldownDecision(
                active=False,
                cooldown_until=None,
                consecutive_refuses=consecutive_refuses,
            )

        if cooldown_until <= now:
            # 自然解除済み（COOLDOWN-04 と同じ動作）
            return CooldownDecision(
                active=False, cooldown_until=None, consecutive_refuses=0
            )

        return CooldownDecision(
            active=True,
            cooldown_until=cooldown_until,
            consecutive_refuses=consecutive_refuses,
        )

    def increment_refuse_count(
        self,
        actor_id: str,
        now: datetime,
        *,
        after_natural_release: bool = False,
    ) -> CooldownState:
        """in-memory dict で連続拒否カウントを更新する。

        本番 cooldown.py の COOLDOWN-02 / COOLDOWN-04 と同じ不変条件を保証。
        """
        ttl_value = int((now + timedelta(days=30)).timestamp())

        if after_natural_release:
            # COOLDOWN-04: 自然解除後 → consecutive_refuses=1, cooldown_until=None
            self._records[actor_id] = {
                "consecutive_refuses": 1,
                "last_refuse_at": now,
                "cooldown_until": None,
            }
            return CooldownState(
                PK=f"USER#{actor_id}",
                SK="COOLDOWN#current",
                consecutiveRefuses=1,
                lastRefuseAt=now.isoformat(),
                cooldownUntil=None,
                ttl=ttl_value,
            )

        # 通常パス
        record = self._records.get(actor_id, {"consecutive_refuses": 0})
        new_count = record["consecutive_refuses"] + 1

        if new_count >= 3:
            # COOLDOWN-02: 3 回到達でクールダウン発火（PBT-03 不変条件）
            cooldown_until = now + timedelta(hours=3)
            self._records[actor_id] = {
                "consecutive_refuses": 3,
                "last_refuse_at": now,
                "cooldown_until": cooldown_until,
            }
            return CooldownState(
                PK=f"USER#{actor_id}",
                SK="COOLDOWN#current",
                consecutiveRefuses=3,
                lastRefuseAt=now.isoformat(),
                cooldownUntil=cooldown_until.isoformat(),
                ttl=ttl_value,
            )

        self._records[actor_id] = {
            "consecutive_refuses": new_count,
            "last_refuse_at": now,
            "cooldown_until": None,
        }
        return CooldownState(
            PK=f"USER#{actor_id}",
            SK="COOLDOWN#current",
            consecutiveRefuses=new_count,
            lastRefuseAt=now.isoformat(),
            cooldownUntil=None,
            ttl=ttl_value,
        )


class LocalMemoryStore:
    """in-memory で Memory を代替するローカル実装。

    Phase 2 では empty MemoryContext を返すだけ（fail-safe で動作可能、
    PROMPT-CONFIG 既定値 preferred_axis='fact'）。
    """

    async def build_memory_context(self, actor_id: str) -> MemoryContext:
        """常に empty MemoryContext を返す（PROMPT-CONFIG 既定値で動作）。"""
        _ = actor_id  # 未使用警告抑制
        return empty_memory_context()

    async def record_event(
        self,
        actor_id: str,
        session_id: str,
        axis: str,
        outcome: str,
        turn: int,
    ) -> None:
        """ローカルでは Memory への書き込みを実施せず、ログのみ。"""
        _LOGGER.info(
            "local_memory_record_event",
            extra={
                "actor_id": actor_id,
                "session_id": session_id,
                "axis": axis,
                "outcome": outcome,
                "turn": turn,
            },
        )


# シングルトン（agentcore dev で 1 プロセス内で再利用）
_LOCAL_COOLDOWN_STORE: LocalCooldownStore | None = None
_LOCAL_MEMORY_STORE: LocalMemoryStore | None = None


def get_local_cooldown_store() -> LocalCooldownStore:
    """シングルトンの LocalCooldownStore を返す。"""
    global _LOCAL_COOLDOWN_STORE
    if _LOCAL_COOLDOWN_STORE is None:
        _LOCAL_COOLDOWN_STORE = LocalCooldownStore()
    return _LOCAL_COOLDOWN_STORE


def get_local_memory_store() -> LocalMemoryStore:
    """シングルトンの LocalMemoryStore を返す。"""
    global _LOCAL_MEMORY_STORE
    if _LOCAL_MEMORY_STORE is None:
        _LOCAL_MEMORY_STORE = LocalMemoryStore()
    return _LOCAL_MEMORY_STORE


def reset_local_stores_for_testing() -> None:
    """テスト用にシングルトンをリセットする。"""
    global _LOCAL_COOLDOWN_STORE, _LOCAL_MEMORY_STORE
    _LOCAL_COOLDOWN_STORE = None
    _LOCAL_MEMORY_STORE = None
