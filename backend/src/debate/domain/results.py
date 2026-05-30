"""Unit-3 Debate 結果 DTO（Phase 1 Step 3.3 + Phase 2 Step 1.3 で追加）。

クールダウン判定 (`ALG-COOLDOWN-CHECK`) の戻り値型と、DDB Cooldowns テーブルのレコード型、
ストレス推定の戻り値型、プロンプト合成の戻り値型を集約する。
DDB 属性名は camelCase（domain-entities §4.1）、Python 内部は snake_case（Pydantic alias で変換）。

参照: aidlc-docs/construction/unit-3-debate/functional-design/domain-entities.md §4 / §5 / §6
参照: aidlc-docs/construction/unit-3-debate/functional-design/business-rules.md COOLDOWN-01〜04 / STRESS / PROMPT
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: ストレスレベル（'low' / 'mid' / 'high' のいずれか、PBT-07 集合性）
StressLevel = Literal["low", "mid", "high"]

#: 論破軸（fact / psychology / reward）
DebateAxis = Literal["fact", "psychology", "reward"]


class CooldownDecision(BaseModel):
    """クールダウン判定結果（value object、ALG-COOLDOWN-CHECK の戻り値）。

    Attributes:
        active: True ならクールダウン中（Bedrock を呼ばずに即時 cooldown_triggered イベント発火）。
        cooldown_until: クールダウン解除時刻（active=True のとき必ず存在）。
        consecutive_refuses: 現在の連続拒否回数（自然解除後の最初の拒否で 1 にリセット）。

    不変条件:
        - active == True のとき cooldown_until が必ず存在
        - 純関数の戻り値（同一入力 → 同一出力）
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    active: bool
    cooldown_until: datetime | None = None
    consecutive_refuses: int = Field(default=0, ge=0)


class CooldownState(BaseModel):
    """DDB Cooldowns テーブルのレコード（camelCase 属性、Pydantic alias で snake_case 変換）。

    DDB 属性名は **camelCase** で統一（domain-entities §4.1 / business-rules COOLDOWN-CONFIG）。
    Python 実装では `Item['cooldownUntil']` のように DDB 属性名で dict アクセスし、
    `CooldownState.model_validate(item)` で Python オブジェクト化する際に
    `Field(alias=...)` で snake_case に変換する。

    Attributes:
        pk: DDB Partition Key（'USER#<actor_id>'）。
        sk: DDB Sort Key（'COOLDOWN#current'、1 ユーザー 1 レコード）。
        consecutive_refuses: 連続拒否回数（自然解除後の次回拒否で 1 にリセット、COOLDOWN-04）。
        last_refuse_at: 最終拒否時刻（ISO 8601）。
        cooldown_until: クールダウン解除時刻（None なら未発動）。
        ttl: UNIX timestamp（30 日後に DDB 自動削除）。

    不変条件（PBT-03 重点）:
        - consecutive_refuses == 3 に達した瞬間に必ず cooldown_until = now + 3h
        - ttl == int((now + 30d).timestamp())
        - consecutive_refuses は自然解除後の次回拒否で 1 にリセット（M3-1 修正、COOLDOWN-04）
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pk: str = Field(alias="PK")
    sk: str = Field(alias="SK")
    consecutive_refuses: int = Field(alias="consecutiveRefuses", ge=0)
    last_refuse_at: datetime = Field(alias="lastRefuseAt")
    cooldown_until: datetime | None = Field(default=None, alias="cooldownUntil")
    ttl: int = Field(ge=0)


class StressLevelResult(BaseModel):
    """ストレス推定結果（value object、ALG-STRESS の戻り値）。

    Attributes:
        level: 'low' / 'mid' / 'high' のいずれか（PBT-07 不変条件）。
        score: 計算されたスコア（>= 0、デバッグ用）。
        signals_used: スコア計算に使われた要因のラベル（PII を含まない、debug 用）。
            Telemetry には level のみ送信、signals_used は送らない（business-rules STRESS-06）。

    不変条件（PBT-07 重点）:
        - level in {'low', 'mid', 'high'}
        - score >= 0
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    level: StressLevel
    score: int = Field(ge=0)
    signals_used: list[str] = Field(default_factory=list)


class ComposedPrompt(BaseModel):
    """プロンプト合成結果（value object、ALG-PROMPT の戻り値）。

    Attributes:
        text: 合成されたプロンプトテキスト（最大 PROMPT_MAX_LENGTH_CHARS=8000）。
        axes: 含まれる軸のリスト（PBT-03 検証用）。

    不変条件（PBT-03 / PBT-08 重点）:
        - 'fact' in axes（必須）
        - 'psychology' in axes（必須）
        - 'reward' in axes  ⟺  stress_level in {'mid', 'high'}（PROMPT-02）
        - len(text) <= 8000
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: str = Field(..., max_length=8000)
    axes: list[DebateAxis] = Field(min_length=2)
