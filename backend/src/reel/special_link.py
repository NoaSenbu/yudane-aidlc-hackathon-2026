"""ALG-LINK: Amazon Associates Special Link 生成（B-10、Q8=A / NG-8）。

タグ付き正規 URL を純関数で生成（同一入力→同一 URL）。短縮 URL を使わず（NG-8）、
環境ガード（dev=仮リンク / prd 未承認=ブロック）を適用。専用 Lambda にせず
feed/transition Lambda が import する共有モジュール（R-PAT-LINK-01）。
"""

from __future__ import annotations

from typing import Literal

from backend.src.reel.models import SpecialLink

Env = Literal["dev", "prd"]

_AMAZON_BASE = "https://www.amazon.co.jp/dp/"


def generate_special_link(
    asin: str,
    user_id: str,
    *,
    env: Env,
    associates_tag: str,
    creators_approved: bool,
) -> SpecialLink:
    """Special Link を生成する（純関数、PBT-02 round-trip）。

    生成 URL は S-01 extractAsin で元 ASIN に逆抽出できる（短縮しない、REEL-LINK-02/03）。
    Associates タグは SSM 由来の非機密値（URL に公開される）。

    Args:
        asin: 正規化済み ASIN。
        user_id: commission 計測用サブタグの材料。
        env: 実行環境。
        associates_tag: Associates トラッキングタグ（SSM）。
        creators_approved: Approved Mobile Application 承認フラグ（§8 A-10）。

    Returns:
        SpecialLink（prd 未承認は blocked=true、dev は仮リンク）。
    """
    tag = f"{associates_tag}-{_sub_tag(user_id)}"
    canonical = f"{_AMAZON_BASE}{asin}?tag={tag}"

    if env == "prd" and not creators_approved:
        # 本番未承認は遷移ブロック（US-03-04 AC-4）
        return SpecialLink(url=canonical, tag=tag, blocked=True)
    if env == "dev":
        return SpecialLink(url=f"{canonical}&yudane_env=dev", tag=tag, blocked=False)
    return SpecialLink(url=canonical, tag=tag, blocked=False)


def _sub_tag(user_id: str) -> str:
    """ユーザー単位の commission サブタグ（短く安定なハッシュ片）。"""
    import hashlib

    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]
