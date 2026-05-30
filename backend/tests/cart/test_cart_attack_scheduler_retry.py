"""B-05 cart_attack_scheduler_retry 単体テスト。

3 連続失敗で watching_orphaned 遷移 + 成功時 retry_count=0 リセット + 100 件超過時の逐次処理。

2026-05-29 Issue Z2/Z3 修正: CartWatchItem.user_id 追加で retry batch が正しく user_id を扱う
ことを確認するテストを追加。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.src.cart.repository import (
    CartWatchItem,
    CartWatchItemsRepo,
    ProductMeta,
)


class TestRetryBatchSkeleton:
    """retry batch スケルトンテスト。

    本格的な moto 統合テストは IT-08（Integration Test）で実施。
    本 Step では機能仕様 + Z2/Z3 修正の確認のみ。
    """

    def test_max_retry_attempts_constant(self) -> None:
        from backend.src.cart.handlers.cart_attack_scheduler_retry import MAX_RETRY_ATTEMPTS

        assert MAX_RETRY_ATTEMPTS == 3  # NFR Design Q4=A' 確定値

    def test_handler_imports_successfully(self) -> None:
        """handler module が import できることを確認。"""
        from backend.src.cart.handlers.cart_attack_scheduler_retry import lambda_handler

        assert callable(lambda_handler)


class TestUserIdRecovery:
    """Issue Z2/Z3 修正の確認: CartWatchItem.user_id が PK から復元される。"""

    def test_user_id_recovered_from_pk(self) -> None:
        item = CartWatchItem.from_dynamodb(
            {
                "PK": "USER#user-abc-123",
                "SK": "CART#B0CXXXXXXX",
                "itemId": "01HG000000000000000000",
                "asin": "B0CXXXXXXX",
                "status": "watching",
                "productMeta": {"title": "test", "priceYen": 100},
                "createdAt": "2026-05-29T10:00:00+00:00",
                "updatedAt": "2026-05-29T10:00:00+00:00",
            }
        )
        assert item.user_id == "user-abc-123"

    def test_user_id_empty_when_pk_missing(self) -> None:
        item = CartWatchItem.from_dynamodb(
            {
                "itemId": "01HG",
                "asin": "B0CXXXXXXX",
                "status": "watching",
                "productMeta": {"title": "test", "priceYen": 100},
                "createdAt": "2026-05-29T10:00:00+00:00",
                "updatedAt": "2026-05-29T10:00:00+00:00",
            }
        )
        assert item.user_id == ""

    def test_query_orphan_candidates_returns_items_with_user_id(
        self, cart_watch_items_table  # type: ignore[no-untyped-def]
    ) -> None:
        """GSI1 Query 結果も PK 経由で user_id が復元される（Z2 修正の統合確認）。"""
        repo = CartWatchItemsRepo(table=cart_watch_items_table)
        now = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
        repo.create(
            "user-1", "B0CXXXXXXX", "01HG",
            ProductMeta("title", 100), "watching", now,
        )
        candidates = repo.query_orphan_candidates(limit=10)
        # attackSchedule 未設定の watching アイテムが取れるはず
        assert len(candidates) >= 1
        # Issue Z2 修正: user_id が PK から復元される
        for candidate in candidates:
            assert candidate.user_id == "user-1"
