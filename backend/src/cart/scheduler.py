"""B-05 CartAttackScheduler — EventBridge Scheduler ジョブ管理ライブラリ。

CartWatchItem 登録時刻 createdAt を起点に 30m / 6h / 24h の 3 ジョブを One-time Schedule で作成。
失敗時は部分失敗許容（NFR Design Q4=A'、3 件中 1 件失敗でも CartWatchItem は status=watching で残す）。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §2.2 / Q4=A
TDD: クラシック TDD
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import boto3

from backend.src.cart.repository import AttackSchedule

# 追撃ステップの遅延秒数（business-rules.md SG 定数表）
ATTACK_STEPS: dict[Literal["30m", "6h", "24h"], int] = {
    "30m": 1_800,
    "6h": 21_600,
    "24h": 86_400,
}


def _user_hash(user_id: str) -> str:
    """Cognito sub の最初 8 文字を SHA-256 ハッシュで短縮する（Schedule 名 64 文字制限対応）。"""
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]


def _build_schedule_name(
    user_id: str, asin: str, base_time: datetime, step: Literal["30m", "6h", "24h"]
) -> str:
    """Schedule 名を生成する。

    形式: cart-attack-{user_hash}-{asin}-{base_ms}-{step}
    例: cart-attack-XXXXXXXX-B0CXXXXXXX-1717000000000-30m

    制約: 64 文字以内、[0-9a-zA-Z-_.] のみ（infrastructure-design.md §1.2）。
    DEV_INITIAL（個人 sandbox 識別子）が環境変数で指定されている場合は prefix に挿入。
    """
    base_ms = int(base_time.timestamp() * 1000)
    dev_initial = os.environ.get("DEV_INITIAL", "")
    init_prefix = f"{dev_initial}-" if dev_initial else ""
    return f"cart-attack-{init_prefix}{_user_hash(user_id)}-{asin}-{base_ms}-{step}"


def schedule_attacks(
    user_id: str,
    item_id: str,
    asin: str,
    base_time: datetime,
    scheduler_client: Optional[object] = None,
) -> AttackSchedule:
    """30m / 6h / 24h の 3 ジョブを EventBridge Scheduler に登録する。

    部分失敗許容: 1 件失敗しても他 2 件は登録試行する。すべて失敗した場合は
    例外を呼出側に伝播し、呼出側（B-04）で CartWatchItem は status=watching を維持。

    Args:
        user_id: Cognito sub。
        item_id: CartWatchItems の itemId（ULID）。
        asin: Amazon ASIN（10 文字）。
        base_time: 起算点（CartWatchItem の createdAt）。
        scheduler_client: EventBridge Scheduler クライアント（テスト注入用）。

    Returns:
        AttackSchedule（3 ステップの Schedule 名）。

    Raises:
        Exception: 全 3 件作成失敗時のみ伝播。部分失敗は warn ログのみ。
    """
    sched = scheduler_client or boto3.client("scheduler")
    notification_dispatcher_arn = os.environ["NOTIFICATION_DISPATCHER_ARN"]
    scheduler_role_arn = os.environ["SCHEDULER_ROLE_ARN"]

    schedule_names: dict[str, str] = {}
    failures: list[tuple[str, Exception]] = []

    for step, delay_sec in ATTACK_STEPS.items():
        fire_at = base_time + timedelta(seconds=delay_sec)
        schedule_name = _build_schedule_name(user_id, asin, base_time, step)
        try:
            sched.create_schedule(  # type: ignore[attr-defined]
                Name=schedule_name,
                GroupName="default",
                ScheduleExpression=f"at({fire_at.strftime('%Y-%m-%dT%H:%M:%S')})",
                ScheduleExpressionTimezone="Etc/UTC",
                FlexibleTimeWindow={"Mode": "OFF"},
                State="ENABLED",
                ActionAfterCompletion="DELETE",  # Q4=A: 完了後自動削除
                Target={
                    "Arn": notification_dispatcher_arn,
                    "RoleArn": scheduler_role_arn,
                    "Input": _build_input(user_id, item_id, asin, step),
                    "RetryPolicy": {
                        "MaximumEventAgeInSeconds": 600,
                        "MaximumRetryAttempts": 2,
                    },
                },
            )
            schedule_names[f"schedule_{step}"] = schedule_name
        except Exception as exc:
            failures.append((step, exc))
            schedule_names[f"schedule_{step}"] = ""  # 空値で「未登録」を表現

    if len(failures) == 3:
        # 全件失敗時のみ呼出側に伝播
        raise RuntimeError(
            f"All 3 attacks failed for itemId={item_id}: {[str(e) for _, e in failures]}"
        )

    return AttackSchedule(
        schedule_30m=schedule_names.get("schedule_30m", ""),
        schedule_6h=schedule_names.get("schedule_6h", ""),
        schedule_24h=schedule_names.get("schedule_24h", ""),
    )


def cancel_attacks(
    schedule: AttackSchedule,
    scheduler_client: Optional[object] = None,
) -> None:
    """3 ジョブをキャンセルする。

    既に発火済 / 削除済（ResourceNotFoundException）は無視する。
    """
    sched = scheduler_client or boto3.client("scheduler")
    for name in [schedule.schedule_30m, schedule.schedule_6h, schedule.schedule_24h]:
        if not name:
            continue
        try:
            sched.delete_schedule(Name=name, GroupName="default")  # type: ignore[attr-defined]
        except sched.exceptions.ResourceNotFoundException:  # type: ignore[attr-defined]
            # 既に発火 / 削除済として無視
            continue
        except Exception:
            # その他のエラーは呼出側でハンドリング
            raise


def _build_input(
    user_id: str, item_id: str, asin: str, step: Literal["30m", "6h", "24h"]
) -> str:
    """Scheduler の Input を JSON 文字列で生成する（B-06 NotificationDispatcher が受領）。"""
    import json

    return json.dumps({"userId": user_id, "itemId": item_id, "asin": asin, "step": step})
