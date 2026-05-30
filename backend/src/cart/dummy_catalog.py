"""ダミーカタログ — Amazon Approved Mobile Application 申請承認前の B-11 fallback。

backlog B-503 で削除候補。USE_DUMMY_CATALOG=true の場合、Creators API の代わりに本辞書を返す。
"""

from __future__ import annotations

from typing import Optional

from backend.src.cart.repository import ProductMeta

# 10 商品の固定データ（mockup と整合させた最小ダミー）
_DUMMY_PRODUCTS: dict[str, ProductMeta] = {
    "B0CXXXXXXX": ProductMeta(
        title="ワイヤレスイヤホン NoiseCancel Pro",
        price_yen=12_800,
        image_url="https://placeholder.example.com/earbuds.svg",
        review_summary="ノイキャン性能が良いという声が多い",
        brand="サンプルブランド",
        category="electronics",
    ),
    "B0CYYYYYYY": ProductMeta(
        title="人を動かす（新装版）",
        price_yen=1_650,
        image_url="https://placeholder.example.com/book.svg",
        review_summary="自己啓発の古典として高評価",
        brand="サンプルブランド",
        category="books",
    ),
    "B0CZZZZZZZ": ProductMeta(
        title="シングルモルトウイスキー 12 年",
        price_yen=8_900,
        image_url="https://placeholder.example.com/whisky.svg",
        review_summary="深いコクで高評価",
        brand="サンプルブランド",
        category="grocery",
    ),
    "B0CAAAAAAA": ProductMeta(
        title="LED デスクライト 調光調色",
        price_yen=4_500,
        image_url="https://placeholder.example.com/desk-lamp.svg",
        review_summary="目に優しいと評判",
        brand="サンプルブランド",
        category="home",
    ),
}


def get_dummy_product(asin: str) -> Optional[ProductMeta]:
    """ダミーカタログから商品メタを取得する（未登録の ASIN は None）。

    backlog B-503 で削除予定。本実装は Approved Mobile Application 申請承認後に
    B-11 CreatorsApiClient（Unit-4 owner）に切り替える。
    """
    return _DUMMY_PRODUCTS.get(asin)
