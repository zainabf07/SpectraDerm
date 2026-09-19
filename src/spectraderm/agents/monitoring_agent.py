"""Deterministic interpretation of existing Module Q/R/S monitoring outputs.

This module coordinates supplied results only. It does not recalculate a
baseline, longitudinal comparison, or anomaly/change score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any


STABLE_SCORE_RANGE = 2.0


@dataclass(frozen=True)
class HistoricalScanRecord:
    """One supplied historical engineering record, retained without inference."""

    scan_id: str
    timestamp: str
    change_score: float | None = None
    status: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class MonitoringAgentInput:
    """Already-computed Module R, S, and Q outputs plus historical records."""

    baseline_reference: Any | None = None
    current_comparison: Any | None = None
    change_anomaly_result: Any | None = None
    historical_scan_records: tuple[HistoricalScanRecord, ...] = ()
    current_scan_id: str | None = None
    current_timestamp: str | None = None
    previous_monitoring_results: tuple[Any, ...] = ()


@dataclass(frozen=True)
class MonitoringAgentResult:
    """Structured, non-diagnostic monitoring interpretation."""

    current_status: str
    trend: str
    current_change_score: float | None
    previous_change_score: float | None
    historical_records: tuple[HistoricalScanRecord, ...]
    number_of_valid_scans: int
    summary: str
    evidence_inputs: Mapping[str, Any]
    limitations: tuple[str, ...]
    safety_message: str


_SAFETY_MESSAGE = (
    "All change information is model-derived engineering output, not disease probability or a diagnosis. "
    "An increasing change score is not proof of disease progression. Estimated spectral information is not "
    "measured spectroscopy, and missing values are not replaced. Professional assessment is not recommended "
    "merely because a numerical score increases; any such action requires appropriate existing evidence or context."
)


def _field(value: Any, name: str) -> Any | None:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _finite_score(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if isfinite(score) else None


def _ordered_records(records: Sequence[HistoricalScanRecord]) -> tuple[HistoricalScanRecord, ...]:
    if any(not isinstance(record, HistoricalScanRecord) for record in records):
        raise TypeError("historical_scan_records must contain HistoricalScanRecord objects")
    # ISO-like timestamps and scan IDs yield a stable ordering without changing
    # record contents. Equal timestamps are ordered by the supplied scan ID.
    return tuple(sorted(records, key=lambda record: (record.timestamp, record.scan_id)))


def _trend(valid_scores: tuple[float, ...]) -> str:
    """Apply the documented fixed engineering trend rule to supplied scores."""
    if len(valid_scores) < 2:
        return "insufficient_history"
    if len(valid_scores) >= 3 and all(
        later > earlier for earlier, later in zip(valid_scores, valid_scores[1:])
    ):
        return "increasing_change"
    if max(valid_scores) - min(valid_scores) <= STABLE_SCORE_RANGE:
        return "stable"
    return "changed"


def _current_status(change_output: Any | None) -> str:
    """Use only the explicit Module Q category, never a score threshold."""
    category = _field(change_output, "category") if change_output is not None else None
    normalized = str(category).strip().lower() if category is not None else ""
    if normalized == "stable":
        return "stable"
    if normalized:
        return "changed"
    return "unavailable"


class MonitoringAgent:
    """Plain-Python coordinator for supplied historical and Q/R/S outputs."""

    def interpret(self, agent_input: MonitoringAgentInput) -> MonitoringAgentResult:
        if not isinstance(agent_input, MonitoringAgentInput):
            raise TypeError("agent_input must be a MonitoringAgentInput")
        records = _ordered_records(agent_input.historical_scan_records)
        valid_records = tuple(
            (record, score) for record in records if (score := _finite_score(record.change_score)) is not None
        )
        valid_scores = tuple(score for _, score in valid_records)
        current_score = _finite_score(_field(agent_input.change_anomaly_result, "change_score"))
        previous_candidates = valid_records
        if agent_input.current_scan_id is not None:
            previous_candidates = tuple(
                item for item in valid_records if item[0].scan_id != agent_input.current_scan_id
            )
        previous_score = previous_candidates[-1][1] if previous_candidates else None
        trend = _trend(valid_scores)
        status = _current_status(agent_input.change_anomaly_result)
        supplied_names = tuple(
            name for name, value in (
                ("baseline_reference", agent_input.baseline_reference),
                ("current_comparison", agent_input.current_comparison),
                ("change_anomaly_result", agent_input.change_anomaly_result),
                ("previous_monitoring_results", agent_input.previous_monitoring_results),
            ) if value is not None and (not isinstance(value, tuple) or bool(value))
        )
        summary = (
            f"Current engineering status: {status}. Trend from {len(valid_scores)} valid supplied historical "
            f"change score(s): {trend}."
        )
        limitations = [
            "The agent reuses supplied Module Q/R/S outputs and does not recalculate their algorithms.",
            "The agent interprets records only; it does not establish medical progression or diagnosis.",
        ]
        if trend == "insufficient_history":
            limitations.append("Fewer than two valid historical change scores are available; a longitudinal trend cannot yet be established.")
        if current_score is None:
            limitations.append("The current change score is unavailable in the supplied Module Q output.")
        evidence_inputs = {
            "baseline_reference": agent_input.baseline_reference,
            "current_comparison": agent_input.current_comparison,
            "change_anomaly_result": agent_input.change_anomaly_result,
            "previous_monitoring_results": agent_input.previous_monitoring_results,
            "supplied_input_names": supplied_names,
        }
        return MonitoringAgentResult(
            current_status=status,
            trend=trend,
            current_change_score=current_score,
            previous_change_score=previous_score,
            historical_records=records,
            number_of_valid_scans=len(valid_scores),
            summary=summary,
            evidence_inputs=evidence_inputs,
            limitations=tuple(limitations),
            safety_message=_SAFETY_MESSAGE,
        )
