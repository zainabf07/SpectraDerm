"""Renderer-agnostic Module T change-visualization view models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from spectraderm.monitoring.anomaly import ChangeAnomalyResult
from spectraderm.monitoring.baseline import PersonalBaselineResult
from spectraderm.monitoring.longitudinal import LongitudinalComparison


@dataclass(frozen=True)
class FeatureChangeRow:
    """One labeled baseline/current feature-comparison row for presentation."""

    feature_name: str
    baseline_value: Optional[float]
    current_value: Optional[float]
    delta: Optional[float]
    absolute_delta: Optional[float]
    relative_change: Optional[float]
    status: str
    direction: str


@dataclass(frozen=True)
class ChangeVisualization:
    """Deterministic presentation data derived from Modules R, S, and Q."""

    labels: dict[str, str]
    feature_rows: tuple[FeatureChangeRow, ...]
    score_panel: dict[str, Any]
    summary: dict[str, int]
    metadata: dict[str, Any]


def _direction(delta: Optional[float], status: str) -> str:
    if delta is None or not status.startswith(("usable", "comparable")):
        return "unavailable"
    if delta > 0:
        return "increased"
    if delta < 0:
        return "decreased"
    return "unchanged"


def build_change_visualization(
    baseline: PersonalBaselineResult,
    comparison: LongitudinalComparison,
    anomaly: ChangeAnomalyResult,
) -> ChangeVisualization:
    """Build labeled presentation data from existing R/S/Q result structures.

    This function performs no clinical inference and does not recalculate the
    Module Q score. Consumers may render the returned rows as a table, bars,
    or another interface appropriate to their application.
    """
    if not isinstance(baseline, PersonalBaselineResult):
        raise TypeError("baseline must be a PersonalBaselineResult from Module R")
    if not isinstance(comparison, LongitudinalComparison):
        raise TypeError("comparison must be a LongitudinalComparison from Module S")
    if not isinstance(anomaly, ChangeAnomalyResult):
        raise TypeError("anomaly must be a ChangeAnomalyResult from Module Q")

    feature_names = sorted(comparison.feature_status)
    rows = tuple(
        FeatureChangeRow(
            feature_name=name,
            baseline_value=comparison.baseline_values.get(name),
            current_value=comparison.current_values.get(name),
            delta=comparison.delta.get(name),
            absolute_delta=comparison.absolute_delta.get(name),
            relative_change=comparison.relative_change.get(name),
            status=comparison.feature_status[name],
            direction=_direction(comparison.delta.get(name), comparison.feature_status[name]),
        )
        for name in feature_names
    )
    return ChangeVisualization(
        labels={
            "baseline": "Personal Baseline",
            "current": "Current Scan",
            "feature_change": "Feature Change",
            "score": "Model-Derived Change Score",
        },
        feature_rows=rows,
        score_panel={
            "change_score": anomaly.change_score,
            "category": anomaly.category,
            "sufficient_reference_history": anomaly.sufficient_reference_history,
            "interpretation": anomaly.interpretation,
            "warnings": list(anomaly.warnings),
        },
        summary=dict(comparison.summary),
        metadata={
            "baseline_observation_count": baseline.observation_count,
            "baseline_unavailable_feature_count": len(baseline.unavailable_features),
            **comparison.metadata,
        },
    )
