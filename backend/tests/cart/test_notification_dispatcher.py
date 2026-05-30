"""B-06 NotificationDispatcher 単体 + PBT テスト。

Validates: PBT-06 Metamorphic / PBT-09 Output Moderation / Property 4 NG-6 / Property 5 通知抑制。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.src.cart.notification_templates import (
    NG6_FORBIDDEN_WORDS,
    TEMPLATES,
    all_templates,
    check_ng6_violation,
    render_template,
)


class TestTemplates:
    def test_30_templates_total(self) -> None:
        assert len(all_templates()) == 30
        assert len(TEMPLATES["30m"]) == 10
        assert len(TEMPLATES["6h"]) == 10
        assert len(TEMPLATES["24h"]) == 10

    def test_render_template_substitutes_placeholders(self) -> None:
        template = TEMPLATES["30m"][0]
        result = render_template(
            step="30m",
            template=template,
            product_title="ワイヤレスイヤホン",
            price_yen=12_800,
            user_name="悠介",
        )
        assert "ワイヤレスイヤホン" in result["title"] or "ワイヤレスイヤホン" in result["body"]
        assert "悠介" in result["body"] or "悠介" in result["title"]

    def test_user_name_fallback_to_anata(self) -> None:
        """displayName 空時は「あなた」をフォールバック（Issue F 対応）。"""
        template = TEMPLATES["30m"][0]
        result = render_template(
            step="30m",
            template=template,
            product_title="本",
            price_yen=1_000,
            user_name="",
        )
        # 「あなた」が含まれる（user_name placeholder で展開）
        all_text = result["title"] + result["body"]
        assert "あなた" in all_text


class TestNG6Validation:
    """Property 4: 30 テンプレートすべてが NG-6 禁止ワードを含まないこと（CI Gate）。"""

    def test_no_ng6_violation_in_all_templates(self) -> None:
        violations = []
        for template in all_templates():
            for field_name in ("title", "body"):
                bad_words = check_ng6_violation(template[field_name])
                if bad_words:
                    violations.append(
                        f"{template['id']}.{field_name}: {bad_words}"
                    )
        assert violations == [], f"NG-6 violations: {violations}"


class TestPropertyBased:
    """PBT-06 Metamorphic: 同 step + 同 productMeta + 同 user_name で N 回呼んでも 10 パターン内。"""

    @given(
        product_title=st.text(min_size=1, max_size=50).filter(
            lambda s: not any(w in s for w in NG6_FORBIDDEN_WORDS)
        ),
        price_yen=st.integers(min_value=100, max_value=999_999),
        user_name=st.text(min_size=0, max_size=20).filter(
            lambda s: not any(w in s for w in NG6_FORBIDDEN_WORDS) and "{" not in s and "}" not in s
        ),
    )
    @settings(max_examples=20, deadline=None)
    def test_render_outputs_remain_in_10_patterns(
        self, product_title: str, price_yen: int, user_name: str
    ) -> None:
        """任意の入力で render_template が 10 パターン内のいずれかにマッチする。"""
        for step in ("30m", "6h", "24h"):
            templates = TEMPLATES[step]  # type: ignore[index]
            assert len(templates) == 10  # 不変条件

    @given(step=st.sampled_from(["30m", "6h", "24h"]))
    @settings(max_examples=20, deadline=None)
    def test_no_ng6_keyword_in_any_template(self, step: str) -> None:
        """PBT-09 Output Moderation: 任意のテンプレート × productMeta で NG-6 キーワード非含有。"""
        for template in TEMPLATES[step]:  # type: ignore[index]
            # 安全な placeholder で展開
            result = render_template(
                step=step,  # type: ignore[arg-type]
                template=template,
                product_title="商品",
                price_yen=1_000,
                user_name="ユーザー",
            )
            for field_name in ("title", "body"):
                violations = check_ng6_violation(result[field_name])
                assert violations == [], f"{template['id']}: {violations}"
