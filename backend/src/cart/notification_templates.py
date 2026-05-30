"""Unit-5 Cart Intercept — 30 通知テンプレート（Q3=A テンプレートベース）。

30m / 6h / 24h × 各 10 パターン = 30 件。
NG-6 静的検証 (Property 4) の対象 = 各テンプレート文字列が脅迫・罪悪感強要キーワードを含まない。
プレースホルダ: {product_title} / {price_yen} / {user_name}（user_name 空時は「あなた」）。

設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md §2.3
"""

from __future__ import annotations

from typing import Literal

NotificationStep = Literal["30m", "6h", "24h"]


# 30m: 「まだ気になってる？」軽いリマインド系
TEMPLATES_30M: list[dict[str, str]] = [
    {
        "id": "30m-1",
        "title": "{product_title}、まだ気になってる？",
        "body": "{user_name}、迷ってたあれ、今日のうちに決めちゃう？",
    },
    {
        "id": "30m-2",
        "title": "{product_title} の見過ぎ防止？",
        "body": "30 分前の {user_name} の判断、まだ揺らいでいるみたい",
    },
    {
        "id": "30m-3",
        "title": "{product_title}、決めてしまおう",
        "body": "{price_yen} 円で気分が変わるなら、安いものだよ",
    },
    {
        "id": "30m-4",
        "title": "あの {product_title} はどう?",
        "body": "30 分経ったよ、{user_name}。今が決断のタイミング",
    },
    {
        "id": "30m-5",
        "title": "{product_title} の後悔回避",
        "body": "迷ってる時間も {user_name} の時間。サクッと決めよう",
    },
    {
        "id": "30m-6",
        "title": "{product_title} 30 分セッション",
        "body": "{user_name}、忘れる前に YUDANE で確認してみない？",
    },
    {
        "id": "30m-7",
        "title": "気になる {product_title}",
        "body": "{price_yen} 円、{user_name} の頑張りに見合うかも",
    },
    {
        "id": "30m-8",
        "title": "{product_title} のリマインド",
        "body": "30 分後も気になってるなら、それは買い時かも",
    },
    {
        "id": "30m-9",
        "title": "{user_name}、{product_title} はどう?",
        "body": "迷ってる時って楽しいけど、決めるとスッキリするよ",
    },
    {
        "id": "30m-10",
        "title": "{product_title}、サクッと決める？",
        "body": "{user_name} の気分を変える {price_yen} 円かもしれない",
    },
]


# 6h: 「半日経ったね」少し説得系
TEMPLATES_6H: list[dict[str, str]] = [
    {
        "id": "6h-1",
        "title": "{product_title}、半日経ったよ",
        "body": "{user_name}、まだ覚えてる？それは買うサインかもね",
    },
    {
        "id": "6h-2",
        "title": "6 時間後の {product_title}",
        "body": "{user_name} の脳が「欲しい」と言ってる証拠じゃない?",
    },
    {
        "id": "6h-3",
        "title": "あれから 6 時間",
        "body": "{product_title} を覚えてるなら、{user_name} に必要なもの",
    },
    {
        "id": "6h-4",
        "title": "{product_title}、決めごろ",
        "body": "{user_name}、半日迷えたなら、もう 1 時間悩んでも結論同じだよ",
    },
    {
        "id": "6h-5",
        "title": "{product_title} の出会い",
        "body": "{price_yen} 円で {user_name} の今日が変わるかも",
    },
    {
        "id": "6h-6",
        "title": "{user_name}、まだ {product_title} 気になる？",
        "body": "気になり続けるってことは、本当に欲しいってことだよ",
    },
    {
        "id": "6h-7",
        "title": "{product_title} の 6 時間",
        "body": "迷う時間も価値、決断する時間も価値",
    },
    {
        "id": "6h-8",
        "title": "再考タイム: {product_title}",
        "body": "{user_name}、半日後の今、もう一度考えてみない？",
    },
    {
        "id": "6h-9",
        "title": "{product_title} を確認",
        "body": "{price_yen} 円、{user_name} のリラックス代として安いかも",
    },
    {
        "id": "6h-10",
        "title": "あの {product_title}、覚えてる?",
        "body": "{user_name} が忘れない商品は、{user_name} に合ってる商品",
    },
]


# 24h: 「1 日経ったね」最終リマインド系
TEMPLATES_24H: list[dict[str, str]] = [
    {
        "id": "24h-1",
        "title": "{product_title}、24 時間経過",
        "body": "{user_name}、丸 1 日覚えてた商品。それは買い時",
    },
    {
        "id": "24h-2",
        "title": "1 日経った {product_title}",
        "body": "{user_name} の選択は最終段階。納得できる決断を",
    },
    {
        "id": "24h-3",
        "title": "最終確認: {product_title}",
        "body": "24 時間迷った {user_name}、答えは出てる？",
    },
    {
        "id": "24h-4",
        "title": "{product_title} の翌日",
        "body": "{price_yen} 円。1 日考えた価値、もう十分かも",
    },
    {
        "id": "24h-5",
        "title": "{user_name}、最終チェック",
        "body": "{product_title}、覚えてる気持ちが答えだよ",
    },
    {
        "id": "24h-6",
        "title": "あれから 1 日",
        "body": "{product_title} を忘れない {user_name} は買い時",
    },
    {
        "id": "24h-7",
        "title": "{product_title}、最後の通知",
        "body": "{user_name} の判断が出るのを待ってる",
    },
    {
        "id": "24h-8",
        "title": "1 日後の {product_title}",
        "body": "{price_yen} 円で {user_name} のモヤモヤが消えるなら",
    },
    {
        "id": "24h-9",
        "title": "{user_name}、{product_title} はどう?",
        "body": "24 時間悩むって、それは欲しいってこと",
    },
    {
        "id": "24h-10",
        "title": "{product_title} の最終結論",
        "body": "{user_name}、納得した決断ならどっちでも OK",
    },
]


TEMPLATES: dict[NotificationStep, list[dict[str, str]]] = {
    "30m": TEMPLATES_30M,
    "6h": TEMPLATES_6H,
    "24h": TEMPLATES_24H,
}


def all_templates() -> list[dict[str, str]]:
    """全 30 テンプレートを 1 リストで返す（NG-6 静的検証 / PBT-09 用）。"""
    return TEMPLATES_30M + TEMPLATES_6H + TEMPLATES_24H


def render_template(
    step: NotificationStep,
    template: dict[str, str],
    product_title: str,
    price_yen: int,
    user_name: str,
) -> dict[str, str]:
    """テンプレートに変数を展開する。

    user_name 空時は「あなた」をフォールバック（functional-design.md §2.3 Issue F）。
    """
    safe_user_name = user_name if user_name else "あなた"
    placeholders = {
        "product_title": product_title,
        "price_yen": price_yen,
        "user_name": safe_user_name,
    }
    return {
        "title": template["title"].format(**placeholders),
        "body": template["body"].format(**placeholders),
    }


# NG-6 禁止ワード辞書（脅迫 / 罪悪感強要、Property 4 静的検証対象）
NG6_FORBIDDEN_WORDS: tuple[str, ...] = (
    "ストレス悪化",
    "罪悪感",
    "失敗",
    "後悔するよ",
    "ダメな人",
    "情けない",
    "恥ずかしい",
    "残念",
    "やっぱりだめ",
    "向いてない",
    "我慢できない",
    "弱い",
    "どうせ",
    "結局",
    "意志が弱い",
)


def check_ng6_violation(text: str) -> list[str]:
    """テキスト内に NG-6 禁止ワードが含まれているか検査する。

    Returns:
        該当した禁止ワードのリスト（空なら違反なし）。
    """
    return [word for word in NG6_FORBIDDEN_WORDS if word in text]
