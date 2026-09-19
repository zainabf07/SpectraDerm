"""Transparent Module Q subtle skin-pattern change / anomaly analysis.

This module compares a current Module N representation with selected reference
history.  It is an engineering feature-pattern comparison, not a medical
prediction or a disease detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

import numpy as np

from spectraderm.features.combined_features import CombinedFeatureResult

DEFAULT_MINIMUM_REFERENCE_OBSERVATIONS = 4
DEFAULT_EPSILON = 1e-8
STABLE_MAX_SCORE = 39.0
MONITOR_MAX_SCORE = 69.0


@dataclass(frozen=True)
class ChangeAnomalyConfig:
    """Named Q v1 engineering settings.

    ``minimum_reference_observations`` is an engineering requirement for
    estimating reference variability; it has no clinical interpretation.
    """

    minimum_reference_observations: int = DEFAULT_MINIMUM_REFERENCE_OBSERVATIONS
    epsilon: float = DEFAULT_EPSILON
    stable_max_score: float = STABLE_MAX_SCORE
    monitor_max_score: float = MONITOR_MAX_SCORE

    def __post_init__(self) -> None:
        if self.minimum_reference_observations < 2:
            raise ValueError("minimum_reference_observations must be at least 2")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")
        if not 0 <= self.stable_max_score < self.monitor_max_score < 100:
            raise ValueError("category thresholds must satisfy 0 <= stable < monitor < 100")


@dataclass(frozen=True)
class ChangeAnomalyResult:
    """Output of Module Q, with group distances before the bounded mapping."""

    change_score: Optional[float]
    category: Optional[str]
    rgb_change: Optional[float]
    spectral_change: Optional[float]
    features_available: int
    features_compared: int
    features_excluded_nonfinite: int
    features_excluded_zero_variance: int
    reference_available: bool
    sufficient_reference_history: bool
    interpretation: str
    warnings: list[str]


def _feature_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, CombinedFeatureResult):
        return value.current_features
    if isinstance(value, Mapping):
        return value
    raise TypeError("features must be a Module N CombinedFeatureResult or a mapping")


def _scored_features(value: Any) -> dict[str, Any]:
    """Select Q v1 groups only; temporal fields are intentionally reserved."""
    features = _feature_mapping(value)
    output: dict[str, Any] = {}
    for name, feature_value in features.items():
        if not isinstance(name, str):
            raise TypeError("feature names must be strings")
        if name.startswith(("rgb.", "spectral.")):
            output[name] = feature_value
    return output


def _finite_number(value: Any) -> Optional[float]:
    if isinstance(value, (str, bytes, bool)) or not np.isscalar(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


class ChangeAnomalyAnalyzer:
    """Deterministic Q v1 IQR-scaled change/anomaly scorer."""

    def __init__(self, config: Optional[ChangeAnomalyConfig] = None) -> None:
        self.config = config or ChangeAnomalyConfig()

    def analyze_change(
        self, current_features: Any, reference_history: Iterable[Any]
    ) -> ChangeAnomalyResult:
        """Compare current RGB/spectral features against selected history.

        Each feature uses history-only median as its reference value and
        history-only IQR as its scale. A feature is comparable only when it is
        present and finite in current and every reference observation and has a
        non-zero IQR. This prevents imputation or arbitrary zero-scale scores.
        """
        current = _scored_features(current_features)
        if isinstance(reference_history, (str, bytes, Mapping, CombinedFeatureResult)):
            raise TypeError("reference_history must be an iterable of feature observations")
        try:
            history = [_scored_features(item) for item in reference_history]
        except TypeError as exc:
            raise TypeError("reference_history must be an iterable of feature observations") from exc

        sufficient = len(history) >= self.config.minimum_reference_observations
        if not sufficient:
            reason = (
                "Insufficient reference history: "
                f"{len(history)} observation(s) supplied; at least "
                f"{self.config.minimum_reference_observations} are required to estimate reference variability."
            )
            return ChangeAnomalyResult(
                None, None, None, None, len(current), 0, 0, 0, bool(history), False,
                reason, [reason],
            )

        common_names = sorted(set(current).intersection(*(set(item) for item in history)))
        nonfinite = 0
        zero_variance = 0
        rgb_distances: list[float] = []
        spectral_distances: list[float] = []
        for name in common_names:
            current_value = _finite_number(current[name])
            reference_values = [_finite_number(item[name]) for item in history]
            if current_value is None or any(value is None for value in reference_values):
                nonfinite += 1
                continue
            values = np.asarray(reference_values, dtype=float)
            q25, q75 = np.percentile(values, [25, 75])
            iqr = float(q75 - q25)
            if iqr == 0.0:
                zero_variance += 1
                continue
            reference_center = float(np.median(values))
            distance = abs(current_value - reference_center) / (iqr + self.config.epsilon)
            if name.startswith("rgb."):
                rgb_distances.append(float(distance))
            else:
                spectral_distances.append(float(distance))

        rgb_change = float(np.mean(rgb_distances)) if rgb_distances else None
        spectral_change = float(np.mean(spectral_distances)) if spectral_distances else None
        group_distances = [value for value in (rgb_change, spectral_change) if value is not None]
        warnings: list[str] = []
        if nonfinite:
            warnings.append(f"{nonfinite} feature(s) excluded because of non-finite or non-numeric values.")
        if zero_variance:
            warnings.append(f"{zero_variance} feature(s) excluded because of zero reference IQR.")
        if len(group_distances) == 1:
            warnings.append("Reduced group coverage: only one feature group had valid comparable features.")
        if not group_distances:
            reason = "No valid comparable RGB or spectral features were available after exclusions."
            warnings.append(reason)
            return ChangeAnomalyResult(
                None, None, rgb_change, spectral_change, len(current), 0, nonfinite, zero_variance,
                True, True, reason, warnings,
            )

        distance = float(np.mean(group_distances))
        score = float(100.0 * (1.0 - np.exp(-distance)))
        score = min(100.0, max(0.0, score))
        category = self._category(score)
        if category == "Stable":
            interpretation = "The observed feature pattern is close to the selected reference pattern."
        elif category == "Monitor":
            interpretation = "The observed feature pattern differs from the selected reference pattern; further monitoring may be appropriate."
        else:
            interpretation = "The current observation shows a higher degree of feature-pattern change relative to the selected reference."
        return ChangeAnomalyResult(
            score, category, rgb_change, spectral_change, len(current), len(rgb_distances) + len(spectral_distances),
            nonfinite, zero_variance, True, True, interpretation, warnings,
        )

    def _category(self, score: float) -> str:
        if score <= self.config.stable_max_score:
            return "Stable"
        if score <= self.config.monitor_max_score:
            return "Monitor"
        return "Higher Change"


def analyze_change(
    current_features: Any,
    reference_history: Iterable[Any],
    config: Optional[ChangeAnomalyConfig] = None,
) -> ChangeAnomalyResult:
    """Convenience wrapper for :class:`ChangeAnomalyAnalyzer`."""
    return ChangeAnomalyAnalyzer(config).analyze_change(current_features, reference_history)
