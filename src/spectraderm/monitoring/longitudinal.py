"""Deterministic Module S baseline-to-current feature comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from spectraderm.features.combined_features import CombinedFeatureResult
from spectraderm.monitoring.baseline import PersonalBaselineResult


@dataclass(frozen=True)
class LongitudinalComparison:
    """Per-feature comparison of a selected baseline and current Module N result."""

    baseline_values: dict[str, Optional[float]]
    current_values: dict[str, Optional[float]]
    delta: dict[str, Optional[float]]
    absolute_delta: dict[str, Optional[float]]
    relative_change: dict[str, Optional[float]]
    feature_status: dict[str, str]
    summary: dict[str, int]
    metadata: dict[str, Any]


def _number(value: Any) -> Optional[float]:
    if isinstance(value, (str, bytes, bool)) or not np.isscalar(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_longitudinal(
    baseline: PersonalBaselineResult,
    current: CombinedFeatureResult,
) -> LongitudinalComparison:
    """Compare available Module R baseline values with current Module N features.

    Relative change is unavailable when the baseline is zero or when either
    value is unavailable/non-finite. No replacement values are introduced.
    """
    if not isinstance(baseline, PersonalBaselineResult):
        raise TypeError("baseline must be a PersonalBaselineResult from Module R")
    if not isinstance(current, CombinedFeatureResult):
        raise TypeError("current must be a CombinedFeatureResult from Module N")

    baseline_names = set(baseline.feature_contributions) | set(baseline.baseline_features)
    current_names = set(current.current_features)
    if not all(isinstance(name, str) for name in baseline_names | current_names):
        raise TypeError("feature names must be strings")

    baseline_values: dict[str, Optional[float]] = {}
    current_values: dict[str, Optional[float]] = {}
    delta: dict[str, Optional[float]] = {}
    absolute_delta: dict[str, Optional[float]] = {}
    relative_change: dict[str, Optional[float]] = {}
    feature_status: dict[str, str] = {}
    increased = decreased = unchanged = comparable = 0

    for name in sorted(baseline_names | current_names):
        has_baseline = name in baseline.baseline_features
        has_current = name in current.current_features
        baseline_value = _number(baseline.baseline_features[name]) if has_baseline else None
        current_value = _number(current.current_features[name]) if has_current else None
        baseline_values[name] = baseline_value
        current_values[name] = current_value
        delta[name] = absolute_delta[name] = relative_change[name] = None

        if not has_baseline:
            feature_status[name] = "baseline_unavailable" if name in baseline.unavailable_features else "baseline_missing"
            continue
        if not has_current:
            feature_status[name] = "current_missing"
            continue
        if baseline_value is None or not np.isfinite(baseline_value):
            feature_status[name] = "baseline_nonfinite_or_nonnumeric"
            continue
        if current_value is None or not np.isfinite(current_value):
            feature_status[name] = "current_nonfinite_or_nonnumeric"
            continue

        difference = current_value - baseline_value
        delta[name] = float(difference)
        absolute_delta[name] = float(abs(difference))
        comparable += 1
        if difference > 0:
            increased += 1
        elif difference < 0:
            decreased += 1
        else:
            unchanged += 1

        if baseline_value == 0.0:
            feature_status[name] = "comparable_relative_change_unavailable_zero_baseline"
        else:
            relative_change[name] = float(difference / abs(baseline_value))
            feature_status[name] = "usable"

    total = len(feature_status)
    metadata = {
        "baseline_observation_count": baseline.observation_count,
        "baseline_feature_count": len(baseline.baseline_features),
        "current_observation_id": current.metadata.observation_id,
        "current_timestamp": current.metadata.timestamp,
        "current_subject_key": current.metadata.subject_key,
        "current_temporal_status": current.metadata.temporal_status,
    }
    return LongitudinalComparison(
        baseline_values=baseline_values,
        current_values=current_values,
        delta=delta,
        absolute_delta=absolute_delta,
        relative_change=relative_change,
        feature_status=feature_status,
        summary={
            "total_features_considered": total,
            "comparable_features": comparable,
            "unavailable_features": total - comparable,
            "increased_features": increased,
            "decreased_features": decreased,
            "unchanged_features": unchanged,
        },
        metadata=metadata,
    )
