"""B-12 AuditLogger（PAT-OBS-01/02 / PAT-SEC-02）。

AWS Lambda Powertools の Logger / Tracer / Metrics を薄くラップし、
PII マスキング（default-deny）と相関 ID 伝搬を上乗せする（NFR-OBS / tech-stack-decisions §3）。
全 Lambda はこのロガーを使用する。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

from backend.src.common.logging.sanitizer import mask_message, sanitize

LogLevel = Literal["info", "warn", "error"]

_UNIT_FOR_POWERTOOLS = {
    "Count": MetricUnit.Count,
    "Milliseconds": MetricUnit.Milliseconds,
    "None": MetricUnit.NoUnit,
    "Percent": MetricUnit.Percent,
}


class AuditLogger:
    """構造化ログ + PII マスク + EMF メトリクス + X-Ray の統合ロガー。

    Args:
        service: サービス名（Lambda 名 / モジュール名）。
        namespace: メトリクス namespace（既定 YUDANE）。
    """

    def __init__(self, service: str, namespace: str = "YUDANE") -> None:
        self._logger = Logger(service=service)
        self._tracer = Tracer(service=service)
        self._metrics = Metrics(namespace=namespace, service=service)
        self._service = service

    def log(self, level: LogLevel, message: str, context: dict[str, Any]) -> None:
        """構造化ログを出力する（出力直前に 1 回だけ sanitize、PII-05）。

        Args:
            level: ログレベル。
            message: メッセージ（本文も二次マスク、PII-06）。
            context: 付帯情報（default-deny で sanitize、PII-01〜04）。
        """
        safe_context = sanitize(context)
        safe_message = mask_message(message)
        if level == "info":
            self._logger.info(safe_message, extra=safe_context)
        elif level == "warn":
            self._logger.warning(safe_message, extra=safe_context)
        else:
            self._logger.exception(safe_message, extra=safe_context)

    def metric(
        self,
        name: str,
        value: float,
        unit: Literal["Count", "Milliseconds", "None", "Percent"],
        dimensions: dict[str, str],
    ) -> None:
        """EMF カスタムメトリクスを出力する（PAT-OBS-01 / NFR-OBS-01）。

        次元には高カーディナリティ値（userId/asin）を入れない（TEL-07）。

        Args:
            name: メトリクス名（命名規約 `<unit>.<domain>.<metric>`）。
            value: 値。
            unit: 単位。
            dimensions: 低カーディナリティの次元。
        """
        for dim_name, dim_value in dimensions.items():
            self._metrics.add_dimension(name=dim_name, value=dim_value)
        self._metrics.add_metric(name=name, unit=_UNIT_FOR_POWERTOOLS[unit], value=value)

    @contextmanager
    def trace(self, segment_name: str) -> Iterator[None]:
        """X-Ray サブセグメントを作成する（PAT-OBS-02）。

        Args:
            segment_name: セグメント名。
        """
        with self._tracer.provider.in_subsegment(name=segment_name):
            yield
