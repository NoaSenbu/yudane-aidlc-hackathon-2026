"""B-05 cart_attack_scheduler_retry — rate(15min) で起動するリトライバッチ（NFR Q4=A'）。

部分失敗で attackSchedule が空の watching アイテムを GSI1 で抽出 → schedule_attacks 再実行 →
3 回連続失敗で watching_orphaned 遷移 + Alarm 5 累積。

設計:
- aidlc-docs/construction/unit-5-cart-intercept/functional-design/sequence-diagrams.md §7
- aidlc-docs/construction/unit-5-cart-intercept/nfr-design/nfr-design-patterns.md §1.2

TDD: クラシック TDD

2026-05-29 Issue Z2/Z3 修正: CartWatchItem に user_id 属性を追加、from_dynamodb で
PK = USER#{userId} から復元するように変更。本 Lambda は item.user_id を直接使う形に変更。

TODO(unit-1-packaging-001 / B-505): 本 Lambda の `from backend.src.cart.repository import ...`
は CDK packaging 構成では runtime ImportError になる。Member A の Unit-1 packaging 方針確立後に修正。
詳細は doc/backlog.md B-505 参照。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.src.cart.repository import CartWatchItemsRepo
from backend.src.cart.scheduler import schedule_attacks
from backend.src.common.logging import AuditLogger

MAX_RETRY_ATTEMPTS = 3  # 3 回連続失敗で watching_orphaned 遷移


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """rate(15 minutes) で EventBridge Schedule から起動される B-05 retry batch。

    フロー:
    1. GSI1-status-createdAt で status=watching かつ attackSchedule 不完全なアイテムを最大 100 件取得
    2. 各アイテムについて schedule_attacks 再実行
       - 成功: attackSchedule 更新 + retry_count=0 リセット + cart.scheduler.retry_succeeded
       - 失敗 + retry_count < 3: retry_count++ + cart.scheduler.retry_failed
       - 失敗 + retry_count >= 3: status=watching_orphaned 遷移 + Alarm 5 累積

    Returns:
        処理結果サマリ（succeeded / failed / orphaned のカウント）。
    """
    audit = AuditLogger(service="cart-attack-scheduler-retry")
    repo = CartWatchItemsRepo()

    # GSI1 で attackSchedule 不完全な watching アイテムを抽出（最大 100 件）
    candidates = repo.query_orphan_candidates(limit=100)

    succeeded = 0
    failed = 0
    orphaned = 0

    for item in candidates:
        if not item.user_id:
            # PK が USER# 形式でない異常データ（防御的）
            audit.log(
                "warn",
                "Skip orphan candidate without user_id",
                {"asin": item.asin, "itemId": item.item_id},
            )
            continue

        # 既に 3 回失敗済（前サイクルで処理漏れ）→ orphaned 遷移
        if item.retry_count >= MAX_RETRY_ATTEMPTS:
            transitioned = repo.transition_status(
                user_id=item.user_id,
                asin=item.asin,
                to_status="watching_orphaned",
            )
            if transitioned:
                orphaned += 1
                audit.metric(
                    "cart.scheduler.retry_failed", 1, "Count", {"reason": "max-retries"}
                )
            continue

        try:
            # schedule_attacks 再実行（base_time は createdAt）
            base_time = datetime.fromisoformat(item.created_at)
            attack_schedule = schedule_attacks(
                user_id=item.user_id,
                item_id=item.item_id,
                asin=item.asin,
                base_time=base_time,
            )
            repo.update_attack_schedule(item.user_id, item.asin, attack_schedule)
            succeeded += 1
            audit.metric("cart.scheduler.retry_succeeded", 1, "Count", {})
        except Exception as e:
            # 失敗時は retry_count++
            new_count = repo.increment_retry_count(item.user_id, item.asin)
            failed += 1
            audit.log(
                "warn",
                "Schedule retry failed",
                {
                    "userId": item.user_id,
                    "asin": item.asin,
                    "retryCount": new_count,
                    "error": str(e),
                },
            )
            audit.metric("cart.scheduler.retry_failed", 1, "Count", {"reason": "create-failed"})

            # 3 回失敗時は watching_orphaned に遷移
            if new_count >= MAX_RETRY_ATTEMPTS:
                transitioned = repo.transition_status(
                    user_id=item.user_id,
                    asin=item.asin,
                    to_status="watching_orphaned",
                )
                if transitioned:
                    orphaned += 1
                    audit.log(
                        "warn",
                        "Watching item transitioned to watching_orphaned",
                        {"asin": item.asin, "retryCount": new_count},
                    )

    audit.log(
        "info",
        "Retry batch completed",
        {
            "candidates": len(candidates),
            "succeeded": succeeded,
            "failed": failed,
            "orphaned": orphaned,
        },
    )
    return {
        "statusCode": 200,
        "body": {
            "candidates": len(candidates),
            "succeeded": succeeded,
            "failed": failed,
            "orphaned": orphaned,
        },
    }
