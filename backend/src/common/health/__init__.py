"""ヘルスチェック（GET /v1/health、PAT-RESIL-04）。"""

from backend.src.common.health.handler import evaluate_health

__all__ = ["evaluate_health"]
