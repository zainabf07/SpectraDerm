"""User-facing longitudinal progress: baseline, change from baseline, and trend.

Module Q's IQR scorer needs at least four reference scans before it can
estimate normal variation. The monitoring journey needs something earlier:

* scan 1 establishes the personal baseline (no change, no trend);
* scan 2 is compared with the baseline, giving a first change percentage;
* scan 3 onward adds a trend across successive change scores.

This module provides that journey from a small, named set of RGB and
AI-estimated spectral features. It is an engineering deviation measure from the
person's own first scan; it is not a disease probability or a diagnosis.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp, isfinite
from typing import Any, Mapping, Sequence

from spectraderm.monitoring.anomaly import ChangeAnomalyResult

# (key, plain-language label, feature name). Labels describe what was
# measured, never what it means medically.
KEY_PARAMETERS: tuple[tuple[str, str, str], ...] = (
    ("pigmentation", "Pigmentation-related feature", "rgb.pigmentation_darkness_proxy"),
    ("pigmentation_spectral", "Pigmentation-related spectral feature", "spectral.pigmentation_related_spectral_proxy"),
    ("redness", "Redness-related feature", "rgb.pigmentation_red_green_ratio"),
    # Reflectance at 570 nm (a hemoglobin absorption region) relative to 650 nm.
    # A positive ratio keeps percentages meaningful, unlike the zero-crossing
    # vascular proxy.
    ("vascular_spectral", "Hemoglobin-related spectral feature", "spectral.ratio_570_650"),
    ("colour_intensity", "Colour intensity", "rgb.pigmentation_chroma_proxy"),
    ("brightness", "Brightness", "rgb.grayscale_mean"),
    ("spectral_intensity", "Estimated spectral intensity", "spectral.regional_spectral_mean"),
    ("texture", "Texture / local contrast", "rgb.local_contrast_gray"),
)
# Relative change below this is reported as "unchanged".
UNCHANGED_RELATIVE = 0.02
# Per-parameter relative changes are capped so one unstable ratio cannot
# dominate the overall percentage.
MAX_RELATIVE = 1.0
# overall change % -> 0..100 score: score = 100 * (1 - exp(-pct / SCALE)).
# 5% -> 28, 10% -> 49, 18% -> 70, 30% -> 86.
SCORE_SCALE_PERCENT = 15.0
STABLE_MAX_SCORE = 39.0
MONITOR_MAX_SCORE = 69.0
# Trend step (in score points) below which successive scans count as stable.
TREND_STEP = 5.0

STATUS_LABELS = {
    "baseline": "Baseline established",
    "Stable": "Stable",
    "Monitor": "Slight change",
    "Higher Change": "Change detected",
}


@dataclass(frozen=True)
class ParameterChange:
    key: str
    label: str
    feature: str
    baseline: float | None
    previous: float | None
    current: float | None
    change: float | None
    change_percent: float | None
    direction: str  # increased | decreased | unchanged | unavailable


@dataclass(frozen=True)
class HistoryPoint:
    scan_id: str
    timestamp: str
    scan_number: int
    change_score: float | None
    change_percent: float | None
    status_label: str


@dataclass(frozen=True)
class ProgressResult:
    stage: str  # baseline | first_comparison | trend
    scan_number: int
    baseline_scan_id: str | None
    previous_scan_id: str | None
    change_percent: float | None
    change_score: float | None
    category: str | None
    status_label: str
    direction_vs_previous: str | None  # increased | decreased | similar
    trend: str | None  # increasing | decreasing | stable
    trend_text: str | None
    parameters: tuple[ParameterChange, ...]
    history: tuple[HistoryPoint, ...]
    method: str = "baseline_relative_deviation"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _relative(current: float | None, reference: float | None) -> float | None:
    if current is None or reference is None:
        return None
    scale = abs(reference)
    if scale < 1e-6:
        return None
    return (current - reference) / scale


def _direction(relative: float | None) -> str:
    if relative is None:
        return "unavailable"
    if abs(relative) < UNCHANGED_RELATIVE:
        return "unchanged"
    return "increased" if relative > 0 else "decreased"


def score_from_percent(change_percent: float) -> float:
    return round(100.0 * (1.0 - exp(-max(0.0, change_percent) / SCORE_SCALE_PERCENT)), 1)


def category_from_score(score: float) -> str:
    if score <= STABLE_MAX_SCORE:
        return "Stable"
    if score <= MONITOR_MAX_SCORE:
        return "Monitor"
    return "Higher Change"


def _trend(previous_scores: Sequence[float], current: float) -> tuple[str, str]:
    step = current - previous_scores[-1]
    if step > TREND_STEP:
        trend = "increasing"
    elif step < -TREND_STEP:
        trend = "decreasing"
    else:
        trend = "stable"
    series = [*previous_scores, current]
    rising = all(later > earlier + TREND_STEP for earlier, later in zip(series, series[1:]))
    if trend == "increasing" and rising and len(series) >= 3:
        text = f"Change has increased across the last {len(series)} comparisons."
    elif trend == "increasing":
        text = "Change is increasing compared with the previous scan."
    elif trend == "decreasing":
        text = "Change is decreasing compared with the previous scan."
    else:
        text = "Change is stable compared with the previous scan."
    return trend, text


def summarize_progress(
    current_features: Mapping[str, Any],
    history: Sequence[tuple[str, str, Mapping[str, Any], Mapping[str, Any] | None]],
    current_scan_id: str | None = None,
    current_timestamp: str | None = None,
) -> ProgressResult:
    """Summarize the current scan against the person's earlier scans.

    ``history`` holds earlier scans in time order as
    ``(scan_id, timestamp, feature_snapshot, persisted_change_record)``.
    """
    scan_number = len(history) + 1
    points = tuple(
        HistoryPoint(
            scan_id=scan_id, timestamp=timestamp, scan_number=index + 1,
            change_score=_number((record or {}).get("change_score")) if index else None,
            change_percent=_number((record or {}).get("change_percent")) if index else None,
            status_label=STATUS_LABELS["baseline"] if index == 0 else str((record or {}).get("status_label") or "Recorded"),
        )
        for index, (scan_id, timestamp, _, record) in enumerate(history)
    )
    if not history:
        parameters = tuple(
            ParameterChange(key, label, name, _number(current_features.get(name)), None,
                            _number(current_features.get(name)), None, None, "unavailable")
            for key, label, name in KEY_PARAMETERS
        )
        return ProgressResult(
            stage="baseline", scan_number=1, baseline_scan_id=current_scan_id, previous_scan_id=None,
            change_percent=None, change_score=None, category=None, status_label=STATUS_LABELS["baseline"],
            direction_vs_previous=None, trend=None, trend_text=None, parameters=parameters, history=(),
            notes=("This first scan is your personal baseline. Later scans are compared with it.",),
        )

    baseline_id, _, baseline_features, _ = history[0]
    previous_id, _, previous_features, previous_record = history[-1]
    parameters = []
    magnitudes = []
    for key, label, name in KEY_PARAMETERS:
        base = _number(baseline_features.get(name))
        prev = _number(previous_features.get(name))
        cur = _number(current_features.get(name))
        relative = _relative(cur, base)
        if relative is not None:
            magnitudes.append(min(abs(relative), MAX_RELATIVE))
        parameters.append(ParameterChange(
            key, label, name, base, prev, cur,
            None if cur is None or base is None else cur - base,
            None if relative is None else round(100.0 * relative, 1),
            _direction(relative),
        ))
    change_percent = round(100.0 * sum(magnitudes) / len(magnitudes), 1) if magnitudes else None
    score = score_from_percent(change_percent) if change_percent is not None else None
    category = category_from_score(score) if score is not None else None

    previous_percent = _number((previous_record or {}).get("change_percent")) if len(history) > 1 else 0.0
    direction = None
    if change_percent is not None and previous_percent is not None:
        difference = change_percent - previous_percent
        direction = "similar" if abs(difference) < 1.0 else ("increased" if difference > 0 else "decreased")

    previous_scores = [point.change_score for point in points[1:] if point.change_score is not None]
    trend = trend_text = None
    if score is not None and previous_scores:
        trend, trend_text = _trend(previous_scores, score)

    stage = "first_comparison" if len(history) == 1 else "trend"
    notes = ["Compared with your personal baseline (scan 1)."]
    if stage == "first_comparison":
        notes.append("A trend becomes available from your third scan.")
    return ProgressResult(
        stage=stage, scan_number=scan_number, baseline_scan_id=baseline_id, previous_scan_id=previous_id,
        change_percent=change_percent, change_score=score, category=category,
        status_label=STATUS_LABELS.get(category or "", "Recorded"),
        direction_vs_previous=direction, trend=trend, trend_text=trend_text,
        parameters=tuple(parameters), history=points, notes=tuple(notes),
    )


def as_change_result(progress: ProgressResult) -> ChangeAnomalyResult | None:
    """Expose the progress score through the Module Q result shape agents read."""
    if progress.change_score is None:
        return None
    compared = sum(1 for item in progress.parameters if item.change_percent is not None)
    interpretation = {
        "Stable": "The monitored region is close to the personal baseline.",
        "Monitor": "The monitored region differs slightly from the personal baseline; further monitoring may be appropriate.",
        "Higher Change": "The monitored region shows a higher degree of change relative to the personal baseline.",
    }[progress.category or "Stable"]
    return ChangeAnomalyResult(
        change_score=progress.change_score, category=progress.category, rgb_change=None, spectral_change=None,
        features_available=len(progress.parameters), features_compared=compared,
        features_excluded_nonfinite=len(progress.parameters) - compared, features_excluded_zero_variance=0,
        reference_available=True, sufficient_reference_history=True, interpretation=interpretation, warnings=[],
    )


def plain_language_finding(progress: ProgressResult) -> str:
    """A short, non-diagnostic description used as the RAG query and LLM finding."""
    if progress.stage == "baseline":
        return (
            "First skin monitoring scan of a region; it establishes your personal baseline. "
            "No change comparison is available yet. General context on skin colour, pigmentation and "
            "noticing skin changes over time is relevant."
        )
    changed = sorted(
        (item for item in progress.parameters if item.change_percent is not None and item.direction in {"increased", "decreased"}),
        key=lambda item: abs(item.change_percent or 0.0), reverse=True,
    )[:3]
    parts = [
        f"Compared with your baseline photo, the monitored skin region shows an overall model-derived "
        f"change of {progress.change_percent:.0f}% ({progress.status_label.lower()})."
    ]
    if changed:
        parts.append("Largest changes: " + "; ".join(
            f"{item.label.lower()} {item.direction} by {abs(item.change_percent or 0):.0f}%" for item in changed
        ) + ".")
    if progress.trend_text:
        parts.append(progress.trend_text)
    return " ".join(parts)
