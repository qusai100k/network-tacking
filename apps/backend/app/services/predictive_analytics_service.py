from typing import Optional

from app.schemas import PredictionRecord, TelemetrySnapshot


class _Trend:
    __slots__ = ("slope", "intercept", "r_squared", "last_value")

    def __init__(self, slope: float, intercept: float, r_squared: float, last_value: float) -> None:
        self.slope = slope
        self.intercept = intercept
        self.r_squared = r_squared
        self.last_value = last_value


def _fit_linear_trend(values: list[float]) -> Optional[_Trend]:
    n = len(values)
    if n < 4:
        return None

    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    ss_total = sum((y - mean_y) ** 2 for y in values)
    if ss_total == 0:
        r_squared = 1.0
    else:
        ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, values))
        r_squared = max(0.0, 1.0 - (ss_residual / ss_total))

    return _Trend(slope=slope, intercept=intercept, r_squared=r_squared, last_value=values[-1])


def _confidence_from(trend: _Trend, sample_count: int) -> int:
    sample_factor = min(sample_count / 30.0, 1.0)
    base = 35 + (trend.r_squared * 50) * sample_factor
    return int(max(15, min(95, round(base))))


class PredictiveAnalyticsService:
    """Projects near-future network conditions from real collected telemetry history.

    All predictions are derived from linear trend extrapolation over actual
    samples; no synthetic or placeholder data is produced. When there isn't
    enough history to support a statistically meaningful trend, no prediction
    is generated for that metric.
    """

    _horizon_label = "next 15 minutes"
    _horizon_steps = 30

    def predict(self, history: list[TelemetrySnapshot]) -> list[PredictionRecord]:
        if len(history) < 4:
            return []

        predictions: list[PredictionRecord] = []

        predictions.extend(
            self._predict_metric(
                history,
                metric="latency_ms",
                label="Latency",
                unit="ms",
                extractor=lambda s: s.latency_ms,
                lower_bound=0.0,
            )
        )
        predictions.extend(
            self._predict_metric(
                history,
                metric="packet_loss_percent",
                label="Packet Loss",
                unit="%",
                extractor=lambda s: s.packet_loss_percent,
                lower_bound=0.0,
                upper_bound=100.0,
            )
        )
        predictions.extend(
            self._predict_metric(
                history,
                metric="bandwidth_usage_percent",
                label="Bandwidth Utilization",
                unit="%",
                extractor=lambda s: s.bandwidth_usage_percent,
                lower_bound=0.0,
                upper_bound=100.0,
            )
        )
        predictions.extend(
            self._predict_metric(
                history,
                metric="cpu_usage_percent",
                label="CPU Utilization",
                unit="%",
                extractor=lambda s: s.cpu_usage_percent,
                lower_bound=0.0,
                upper_bound=100.0,
            )
        )

        return predictions

    def _predict_metric(
        self,
        history: list[TelemetrySnapshot],
        *,
        metric: str,
        label: str,
        unit: str,
        extractor,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
    ) -> list[PredictionRecord]:
        values = [extractor(sample) for sample in history]
        trend = _fit_linear_trend(values)
        if trend is None:
            return []

        projected = trend.last_value + (trend.slope * self._horizon_steps)
        if lower_bound is not None:
            projected = max(lower_bound, projected)
        if upper_bound is not None:
            projected = min(upper_bound, projected)

        confidence = _confidence_from(trend, len(history))
        interpretation = self._interpret(label, trend, projected)

        return [
            PredictionRecord(
                metric=metric,
                horizon=self._horizon_label,
                predicted_value=round(projected, 2),
                unit=unit,
                confidence_score=confidence,
                interpretation=interpretation,
            )
        ]

    def _interpret(self, label: str, trend: _Trend, projected: float) -> str:
        if abs(trend.slope) < 1e-3:
            return f"{label} is expected to remain stable near current levels."
        direction = "rising" if trend.slope > 0 else "falling"
        return (
            f"{label} has been {direction} across recent samples and is projected "
            f"to reach approximately {projected:.1f} if the current trend continues."
        )