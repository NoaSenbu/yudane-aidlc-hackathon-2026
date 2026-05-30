"""ALG-CATALOG: 商品カタログ取得（B-11、Q7=A / CL-1=A）。

ポート/アダプタ抽象 + キャッシュデコレータ。MVP は DummyCatalogAdapter（プロセス内・
外部ネットワークに出ない）。決勝は CreatorsApiAdapter（VPC 内、stale-on-error）。
設計: nfr-design R-PAT-CAT-01/02・logical-components RLC-06 / business-rules REEL-CAT-01〜06。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from backend.src.reel.models import CatalogQuery, ProductMeta


class ProductCatalogPort(Protocol):
    """カタログアクセスの抽象（REEL-CAT-01、直接 SDK 呼出禁止）。"""

    def get_item_by_asin(self, asin: str) -> ProductMeta | None:
        """ASIN 単一取得。"""
        ...

    def search_items(self, query: CatalogQuery) -> list[ProductMeta]:
        """クエリ検索（カテゴリ/ブランド/共購買起点）。"""
        ...


_DUMMY_CATALOG_PATH = Path(__file__).with_name("dummy_catalog.json")


class DummyCatalogAdapter:
    """ハッカソン書類審査・予選用の固定カタログ（§8 A-10 / FR-REEL-04 / REEL-CAT-02）。

    外部ネットワークに出ず、同梱 JSON から決定論的に返す（REEL-CAT-06）。
    """

    def __init__(self, items: list[ProductMeta] | None = None) -> None:
        """カタログを読み込む（引数優先、無ければ同梱 JSON）。

        Args:
            items: テスト用に注入する商品リスト。None なら dummy_catalog.json を読む。
        """
        self._items = items if items is not None else self._load_bundled()

    @staticmethod
    def _load_bundled() -> list[ProductMeta]:
        """同梱 JSON を読み込む。存在しなければ空リスト。"""
        if not _DUMMY_CATALOG_PATH.exists():
            return []
        raw = json.loads(_DUMMY_CATALOG_PATH.read_text(encoding="utf-8"))
        return [ProductMeta(**item) for item in raw]

    def get_item_by_asin(self, asin: str) -> ProductMeta | None:
        """ASIN 単一取得。"""
        return next((item for item in self._items if item.asin == asin), None)

    def search_items(self, query: CatalogQuery) -> list[ProductMeta]:
        """カテゴリ/ブランド一致 + NG カテゴリ除外で検索（CL-1）。

        いずれの条件も空なら全件（cold start の人気リスト用途）。
        """
        results: list[ProductMeta] = []
        for item in self._items:
            if item.category in query.exclude_ng_categories:
                continue
            if self._matches(item, query):
                results.append(item)
        return results[: query.max_results]

    @staticmethod
    def _matches(item: ProductMeta, query: CatalogQuery) -> bool:
        """カテゴリ/ブランド一致判定。両条件が空なら全件一致扱い。"""
        if not query.by_category and not query.by_brand:
            return True
        return item.category in query.by_category or item.brand in query.by_brand


class CachedCatalog:
    """キャッシュデコレータ層（両アダプタ共通、TTL は決勝の Redis で実体化、REEL-CAT-04）。

    MVP はプロセス内 dict キャッシュ。決勝で ElastiCache Redis に差し替える前提。
    決勝の外部 API 失敗時 stale 返却（R-PAT-CAT-01）も本層の責務。
    """

    def __init__(
        self,
        adapter: ProductCatalogPort,
        *,
        now: Callable[[], float] | None = None,
        ttl_seconds: int = 21_600,
    ) -> None:
        """キャッシュラッパを構築する。

        Args:
            adapter: 実体アダプタ（Dummy / CreatorsApi）。
            now: 現在時刻取得関数（テスト注入用）。
            ttl_seconds: キャッシュ TTL（既定 6h、Unit-1 設定値と整合）。
        """
        self._adapter = adapter
        self._ttl = ttl_seconds
        self._now = now or _monotonic
        self._store: dict[str, tuple[float, ProductMeta]] = {}

    def get_item_by_asin(self, asin: str) -> ProductMeta | None:
        """キャッシュ参照 → ミスでアダプタ → put（cache-aside）。"""
        cached = self._store.get(asin)
        if cached is not None and (self._now() - cached[0]) < self._ttl:
            return cached[1]
        item = self._adapter.get_item_by_asin(asin)
        if item is not None:
            self._store[asin] = (self._now(), item)
        return item

    def search_items(self, query: CatalogQuery) -> list[ProductMeta]:
        """検索はアダプタへ委譲（候補リストの短 TTL キャッシュは決勝で追加）。"""
        return self._adapter.search_items(query)


def _monotonic() -> float:
    """単調増加時刻（既定の now）。"""
    import time

    return time.monotonic()
