"""Deterministic Module R personal feature-baseline construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import numpy as np

from spectraderm.features.combined_features import CombinedFeatureResult


@dataclass(frozen=True)
class PersonalBaselineResult:
    """Selected-reference feature medians and their source availability."""

    baseline_features: dict[str, float]
    feature_contributions: dict[str, int]
    unavailable_features: tuple[str, ...]
    observation_count: int


def _feature_mapping(observation: Any) -> Mapping[str, Any]:
    if isinstance(observation, CombinedFeatureResult):
        return observation.current_features
    if isinstance(observation, Mapping):
        return observation
    raise TypeError("observations must be Module N CombinedFeatureResult objects or feature mappings")


def _finite_feature_value(name: str, value: Any) -> float | None:
    if not isinstance(name, str):
        raise TypeError("feature names must be strings")
    if isinstance(value, (str, bytes, bool)) or not np.isscalar(value):
        raise TypeError(f"feature '{name}' must be a numeric scalar")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"feature '{name}' must be a numeric scalar") from exc
    return numeric if np.isfinite(numeric) else None


def build_personal_baseline(observations: Iterable[Any]) -> PersonalBaselineResult:
    """Build per-feature medians from one or more selected historical observations.

    Non-finite values are ignored. Features without a finite source value are
    reported as unavailable rather than assigned a fabricated value.
    """
    if isinstance(observations, (str, bytes, Mapping, CombinedFeatureResult)):
        raise TypeError("observations must be an iterable of feature observations")
    try:
        history = [_feature_mapping(observation) for observation in observations]
    except TypeError as exc:
        raise TypeError("observations must be an iterable of feature observations") from exc
    if not history:
        raise ValueError("at least one historical observation is required")

    values_by_feature: dict[str, list[float]] = {}
    feature_names: set[str] = set()
    for observation in history:
        for name, value in observation.items():
            numeric = _finite_feature_value(name, value)
            feature_names.add(name)
            if numeric is not None:
                values_by_feature.setdefault(name, []).append(numeric)

    baseline_features: dict[str, float] = {}
    feature_contributions: dict[str, int] = {}
    unavailable: list[str] = []
    for name in sorted(feature_names):
        values = values_by_feature.get(name, [])
        feature_contributions[name] = len(values)
        if not values:
            unavailable.append(name)
            continue
        baseline_features[name] = float(np.median(np.asarray(values, dtype=float)))

    return PersonalBaselineResult(
        baseline_features=baseline_features,
        feature_contributions=feature_contributions,
        unavailable_features=tuple(unavailable),
        observation_count=len(history),
    )
