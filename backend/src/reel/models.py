"""Unit-4 Reel ドメイン DTO（Pydantic v2）。

技術非依存の概念モデル（domain-entities.md）を実装型に落としたもの。型宣言中心の
ため TDD 例外（§12.3）。横断型（DomainError 等）は backend.src.common を参照。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StressLevel = Literal["low", "mid", "high"]
CardOrigin = Literal[
    "purchase-related",
    "co-purchase",
    "late-night-boost",
    "calendar",
    "onboarding-seed",
    "curated-popular",
]
TransitionContext = Literal["reel", "debate-agree", "cart-attack"]
CalendarCategory = Literal["presentation", "date", "camping", "other"]


class _Frozen(BaseModel):
    """不変・厳格な基底モデル。"""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProductMeta(_Frozen):
    """商品メタ（カタログ由来）。"""

    asin: str = Field(pattern=r"^[A-Z0-9]{10}$")
    title: str
    price_yen: int = Field(ge=0)
    image_url: str
    review_summary: str = ""
    category: str = ""
    brand: str = ""


class PurchaseHistoryItem(_Frozen):
    """購入履歴 1 件（MVP 候補生成の主軸、CL-1）。"""

    asin: str = Field(pattern=r"^[A-Z0-9]{10}$")
    category: str
    brand: str
    price_yen: int = Field(ge=0)
    purchased_at: str


class RecentTransition(_Frozen):
    """遷移後カテゴリ cooldown 用（FR-AUTH-03 / REEL-RANK-10）。"""

    category: str
    transitioned_at: str


class TimeBucket(_Frozen):
    """時刻バケット（深夜判定）。"""

    local_hour: int = Field(ge=0, le=23)
    is_late_night: bool


class SafeguardContextFlags(_Frozen):
    """推薦時に参照する Safeguard フラグ + NG カテゴリ。"""

    quiet_week: bool = False
    cooldown_on: bool = False
    ng_categories: tuple[str, ...] = ()


class OnboardingPreferences(_Frozen):
    """cold start シード（CL-3）。"""

    brands: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()


class RecommendationContext(_Frozen):
    """推薦スコアリングの入力一式（domain-entities §2.3）。"""

    user_id: str
    purchase_history: tuple[PurchaseHistoryItem, ...] = ()
    onboarding_preferences: OnboardingPreferences = OnboardingPreferences()
    stress_level: StressLevel = "low"
    time_bucket: TimeBucket = TimeBucket(local_hour=12, is_late_night=False)
    calendar_category: CalendarCategory | None = None
    recent_transitions: tuple[RecentTransition, ...] = ()
    safeguard_flags: SafeguardContextFlags = SafeguardContextFlags()
    average_price_yen: int = Field(default=0, ge=0)


class RankingWeights(_Frozen):
    """リランクの重み（REEL-RANK 設定値、調整可能）。"""

    relatedness: float = 1.0
    time_boost: float = 0.6
    stress_boost: float = 0.5
    calendar_match: float = 0.4
    recency_decay: float = 0.3


class ScoreComponents(_Frozen):
    """スコア内訳（説明可能性・検算用、REEL-RANK-03）。"""

    relatedness: float
    time_boost: float
    stress_boost: float
    calendar_match: float
    recency_decay: float

    def total(self) -> float:
        """内訳の総和（= 最終スコア）。"""
        return (
            self.relatedness
            + self.time_boost
            + self.stress_boost
            + self.calendar_match
            + self.recency_decay
        )


class ScoredCandidate(_Frozen):
    """候補生成 → リランクの中間表現。"""

    product: ProductMeta
    base_relatedness: float
    score: float
    origin: CardOrigin
    components: ScoreComponents


class LabelSource(str, Enum):
    """ラベル生成元（Q4=A）。"""

    LLM = "llm"
    TEMPLATE_FALLBACK = "template-fallback"


class OwnershipLabel(_Frozen):
    """所有感ラベル（US-02-05）。"""

    text: str
    rationale: str
    source: LabelSource


class ReelCard(_Frozen):
    """リールカード 1 枚（FR-REEL-01/03）。"""

    card_id: str
    product: ProductMeta
    pitch: str
    ownership_label: OwnershipLabel
    tags: tuple[str, ...]
    origin: CardOrigin
    is_high_price_boost: bool
    rank_score: float


class ReelPage(_Frozen):
    """リールフィードのページ（カーソルページング、Q9=A）。"""

    cards: tuple[ReelCard, ...]
    next_cursor: str | None
    generated_at: str


class CatalogQuery(_Frozen):
    """カタログ検索クエリ（ALG-CATALOG）。"""

    by_category: tuple[str, ...] = ()
    by_brand: tuple[str, ...] = ()
    seed_asins: tuple[str, ...] = ()
    exclude_ng_categories: tuple[str, ...] = ()
    max_results: int = Field(default=50, ge=1)


class AmazonTransitionRequest(_Frozen):
    """Amazon 遷移記録リクエスト（B-13、US-02-02）。"""

    user_id: str
    card_id: str
    asin: str = Field(pattern=r"^[A-Z0-9]{10}$")
    context: TransitionContext = "reel"
    client_transition_id: str


class ExpAward(_Frozen):
    """EXP 加算結果（B-13 が同期付与、US-02-02 AC-4）。"""

    awarded: int
    total_exp: int
    duplicate: bool


class SpecialLink(_Frozen):
    """Amazon Associates Special Link（B-10、純関数生成）。"""

    url: str
    tag: str
    blocked: bool = False
