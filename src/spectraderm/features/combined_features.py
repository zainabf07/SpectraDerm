"""Combined RGB, estimated-spectral, and temporal feature representation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np

from .rgb_features import RGBFeatureResult
from .spectral_features import SpectralFeatureResult


_EPSILON = 1e-8


@dataclass(frozen=True)
class FeatureMetadata:
    observation_id: Optional[str]
    timestamp: Optional[datetime]
    subject_key: Optional[str]
    history_available: bool
    temporal_status: str
    baseline_observation_id: Optional[str]
    elapsed_days: Optional[float]
    roi_available: bool
    roi_pixel_count: int


@dataclass(frozen=True)
class CombinedFeatureResult:
    current_features: dict[str, float]
    temporal_features: dict[str, float]
    combined_features: dict[str, float]
    ml_vector: np.ndarray
    feature_names: list[str]
    metadata: FeatureMetadata
    warnings: list[str]


def _finite_scalars(features: dict[str, Any], prefix: str, warnings: list[str]) -> dict[str, float]:
    if not isinstance(features, dict):
        raise TypeError("source result features must be a dictionary")
    output: dict[str, float] = {}
    for name, value in features.items():
        if not isinstance(name, str):
            raise TypeError("feature names must be strings")
        if not np.isscalar(value) or isinstance(value, (str, bytes, bool)):
            warnings.append(f"{prefix}{name} was excluded because it is not a numeric scalar.")
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            warnings.append(f"{prefix}{name} was excluded because it is not numeric.")
            continue
        if not np.isfinite(numeric):
            warnings.append(f"{prefix}{name} was excluded because it is not finite.")
            continue
        output[f"{prefix}{name}"] = numeric
    return output


def _current_schema(rgb: RGBFeatureResult, spectral: SpectralFeatureResult, warnings: list[str]) -> dict[str, float]:
    if not isinstance(rgb, RGBFeatureResult):
        raise TypeError("rgb_features must be an RGBFeatureResult from Module L")
    if not isinstance(spectral, SpectralFeatureResult):
        raise TypeError("spectral_features must be a SpectralFeatureResult from Module M")
    current = _finite_scalars(rgb.features, "rgb.", warnings)
    current.update(_finite_scalars(spectral.features, "spectral.", warnings))
    signature = np.asarray(spectral.spectral_signature)
    wavelengths = np.asarray(spectral.wavelengths_nm)
    if signature.shape != (31,) or wavelengths.shape != (31,):
        raise ValueError("Module M spectral signature and wavelengths must both have shape (31,)")
    if not np.isfinite(signature).all() or not np.isfinite(wavelengths).all():
        raise ValueError("Module M spectral signature and wavelengths must be finite")
    for wavelength, value in zip(wavelengths, signature):
        label = str(int(wavelength)) if float(wavelength).is_integer() else f"{wavelength:g}".replace(".", "_")
        current[f"spectral.signature_{label}"] = float(value)
    return dict(sorted(current.items()))


def _baseline_current(baseline: Any) -> dict[str, float]:
    if isinstance(baseline, CombinedFeatureResult):
        return baseline.current_features
    if isinstance(baseline, tuple) and len(baseline) == 2:
        warnings: list[str] = []
        return _current_schema(baseline[0], baseline[1], warnings)
    raise TypeError("baseline_features must be a CombinedFeatureResult or (RGBFeatureResult, SpectralFeatureResult)")


def _timestamp(value: Optional[datetime], label: str) -> Optional[datetime]:
    if value is not None and not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime or None")
    if value is not None and value > datetime.now(value.tzinfo):
        raise ValueError(f"{label} must not be in the future")
    return value


def _metadata(metadata: Optional[dict[str, Any]], timestamp: Optional[datetime], history: bool,
              status: str, baseline_id: Optional[str], elapsed: Optional[float], rgb: RGBFeatureResult,
              spectral: SpectralFeatureResult) -> FeatureMetadata:
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dictionary or None")
    roi_count = metadata.get("roi_pixel_count", min(rgb.roi_pixel_count, spectral.roi_pixel_count))
    if not isinstance(roi_count, (int, np.integer)):
        raise TypeError("metadata roi_pixel_count must be an integer")
    return FeatureMetadata(
        observation_id=metadata.get("observation_id"), timestamp=timestamp,
        subject_key=metadata.get("subject_key"), history_available=history,
        temporal_status=status, baseline_observation_id=baseline_id,
        elapsed_days=elapsed, roi_available=bool(metadata.get("roi_available", True)),
        roi_pixel_count=int(roi_count),
    )


def combine_features(
    rgb_features: RGBFeatureResult,
    spectral_features: SpectralFeatureResult,
    baseline_features: Optional[Any] = None,
    current_timestamp: Optional[datetime] = None,
    baseline_timestamp: Optional[datetime] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> CombinedFeatureResult:
    """Combine Module L/M outputs and optional matching-observation changes.

    Raw unavailable temporal values remain NaN. The aligned ML vector replaces
    only unavailable temporal values with zero and includes availability flags.
    """
    warnings: list[str] = []
    current = _current_schema(rgb_features, spectral_features, warnings)
    current_timestamp = _timestamp(current_timestamp, "current_timestamp")
    baseline_timestamp = _timestamp(baseline_timestamp, "baseline_timestamp")
    history = baseline_features is not None
    status = "follow_up" if history else "baseline"
    baseline: dict[str, float] = _baseline_current(baseline_features) if history else {}
    if history:
        missing = sorted(set(current).symmetric_difference(baseline))
        if missing:
            warnings.append("Temporal comparison skipped unmatched feature names: " + ", ".join(missing))

    elapsed_days: Optional[float] = None
    rate_possible = False
    if history and current_timestamp is not None and baseline_timestamp is not None:
        elapsed_days = (current_timestamp - baseline_timestamp).total_seconds() / 86400.0
        rate_possible = elapsed_days > 0
        if not rate_possible:
            warnings.append("Rate per day is undefined because elapsed_days is zero or negative.")
    elif history and (current_timestamp is not None or baseline_timestamp is not None):
        warnings.append("Rate per day is unavailable because both timestamps are required.")

    source_names = sorted(current)
    temporal: dict[str, float] = {}
    availability: dict[str, float] = {}
    for name in source_names:
        base = baseline.get(name)
        available = history and base is not None and np.isfinite(base)
        prefix = f"temporal.{name}"
        availability[f"{prefix}.available"] = float(available)
        if not available:
            temporal[f"{prefix}.delta"] = float("nan")
            temporal[f"{prefix}.abs_delta"] = float("nan")
            temporal[f"{prefix}.relative_change"] = float("nan")
            temporal[f"{prefix}.rate_per_day"] = float("nan")
            continue
        delta = current[name] - base
        temporal[f"{prefix}.delta"] = float(delta)
        temporal[f"{prefix}.abs_delta"] = float(abs(delta))
        if abs(base) <= _EPSILON:
            temporal[f"{prefix}.relative_change"] = float("nan")
            warnings.append(f"{prefix}.relative_change is undefined because the baseline is zero or near zero.")
        else:
            temporal[f"{prefix}.relative_change"] = float(delta / (abs(base) + _EPSILON))
        temporal[f"{prefix}.rate_per_day"] = float(delta / elapsed_days) if rate_possible else float("nan")

    temporal["temporal.history_available"] = float(history)
    temporal.update(availability)
    metadata_value = _metadata(
        metadata, current_timestamp, history, status,
        baseline_features.metadata.observation_id if isinstance(baseline_features, CombinedFeatureResult) else None,
        elapsed_days, rgb_features, spectral_features,
    )

    current_names = sorted(current)
    groups = [
        [f"temporal.{name}.delta" for name in source_names],
        [f"temporal.{name}.abs_delta" for name in source_names],
        [f"temporal.{name}.relative_change" for name in source_names],
        [f"temporal.{name}.rate_per_day" for name in source_names],
        ["temporal.history_available"] + [f"temporal.{name}.available" for name in source_names],
    ]
    feature_names = current_names + [name for group in groups for name in group]
    combined = dict(current)
    combined.update(temporal)
    vector_values = [combined[name] for name in feature_names]
    ml_vector = np.asarray([value if np.isfinite(value) else 0.0 for value in vector_values], dtype=np.float32)
    return CombinedFeatureResult(current, temporal, combined, ml_vector, feature_names, metadata_value, warnings)
