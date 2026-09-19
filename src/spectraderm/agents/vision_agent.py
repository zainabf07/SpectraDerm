"""Deterministic interpretation of existing SpectraDerm structured outputs.

The Vision Agent does not accept or inspect raw images. It is an orchestration
boundary for already-produced engineering outputs and does not diagnose,
estimate disease probability, or calculate monitoring scores.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisionAgentInput:
    """Optional structured outputs supplied by existing analysis modules."""

    image_quality_result: Any | None = None
    localization_result: Any | None = None
    reconstruction_result: Any | None = None
    spectral_features: Any | None = None
    monitoring_change_result: Any | None = None
    ml_output: Any | None = None


@dataclass(frozen=True)
class ComponentSummary:
    """Availability label and exact supplied output for one pipeline component."""

    available: bool
    summary: str
    supplied_output: Any | None


@dataclass(frozen=True)
class VisionAgentResult:
    """A non-diagnostic, source-preserving interpretation of supplied outputs."""

    overall_status: str
    finding_summary: str
    image_quality_summary: ComponentSummary
    localization_summary: ComponentSummary
    spectral_summary: ComponentSummary
    feature_summary: ComponentSummary
    change_summary: ComponentSummary
    ml_summary: ComponentSummary
    available_evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    safety_message: str

    @property
    def structured_finding(self) -> str:
        """A deterministic handoff string suitable for an optional Module W call."""
        return self.finding_summary


_SAFETY_MESSAGE = (
    "This is an AI/model-derived engineering interpretation of supplied outputs, not a diagnosis. "
    "Estimated spectral information is not measured spectroscopy; change or anomaly outputs are not disease "
    "probabilities; and RGB or spectral features are not confirmed biological biomarkers. Professional assessment "
    "may be appropriate only when existing evidence or warning context warrants it."
)


def _field(value: Any, name: str) -> Any | None:
    """Read a field from either a supplied mapping or an existing result object."""
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _availability(component: str, output: Any | None, detail: str = "") -> ComponentSummary:
    if output is None:
        return ComponentSummary(False, f"{component} output unavailable.", None)
    suffix = f" {detail}" if detail else ""
    return ComponentSummary(True, f"{component} output available.{suffix}", output)


def _quality_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Image-quality", None)
    status = _field(output, "status")
    if status is None:
        return _availability("Image-quality", output)
    return _availability("Image-quality", output, f"Supplied status: {status}.")


def _localization_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Localization", None)
    method = _field(output, "method")
    detail = f"Supplied method: {method}." if method is not None else ""
    return _availability("Localization", output, detail)


def _reconstruction_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Spectral reconstruction", None)
    return _availability(
        "Spectral reconstruction", output,
        "It is treated as supplied reconstruction output, not measured spectroscopy.",
    )


def _feature_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Spectral feature", None)
    return _availability(
        "Spectral feature", output,
        "No biological biomarker inference is made from supplied features.",
    )


def _change_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Monitoring/change", None)
    category = _field(output, "category")
    detail = f"Supplied engineering category: {category}." if category is not None else ""
    return _availability(
        "Monitoring/change", output,
        f"{detail} Change/anomaly output is not a disease probability.",
    )


def _ml_summary(output: Any | None) -> ComponentSummary:
    if output is None:
        return _availability("Optional ML", None)
    return _availability(
        "Optional ML", output,
        "Reported only as supplied model output; it is not converted into a diagnosis.",
    )


def _quality_is_insufficient(output: Any | None) -> bool:
    if output is None:
        return False
    status = _field(output, "status")
    status_text = str(getattr(status, "value", status) or "").upper()
    # REVIEW is a borderline result: analysis continues and the quality
    # caveat is surfaced. Only REJECT (or a failed check without any status)
    # stops the comparison and asks for a retake.
    if status_text.endswith("REJECT"):
        return True
    if status_text.endswith(("REVIEW", "GOOD")):
        return False
    return _field(output, "passed") is False


def _overall_status(image_quality: Any | None, monitoring_change: Any | None) -> str:
    """Apply only explicit engineering-status rules; never inspect a score threshold."""
    if _quality_is_insufficient(image_quality):
        return "insufficient_quality"
    category = _field(monitoring_change, "category") if monitoring_change is not None else None
    normalized = str(category).strip().lower() if category is not None else ""
    if normalized in {"higher change", "review", "review recommended"}:
        return "review_recommended"
    if normalized in {"monitor", "change detected", "change_detected"}:
        return "change_detected"
    return "no_actionable_change"


class VisionAgent:
    """Plain-Python deterministic interpreter for existing structured results."""

    def interpret(self, agent_input: VisionAgentInput) -> VisionAgentResult:
        if not isinstance(agent_input, VisionAgentInput):
            raise TypeError("agent_input must be a VisionAgentInput")
        summaries = (
            ("image_quality", _quality_summary(agent_input.image_quality_result)),
            ("localization", _localization_summary(agent_input.localization_result)),
            ("reconstruction", _reconstruction_summary(agent_input.reconstruction_result)),
            ("spectral_features", _feature_summary(agent_input.spectral_features)),
            ("monitoring_change", _change_summary(agent_input.monitoring_change_result)),
            ("ml_output", _ml_summary(agent_input.ml_output)),
        )
        available = tuple(name for name, summary in summaries if summary.available)
        unavailable = tuple(name for name, summary in summaries if not summary.available)
        status = _overall_status(agent_input.image_quality_result, agent_input.monitoring_change_result)
        finding = (
            f"Engineering status: {status}. Available structured outputs: "
            f"{', '.join(available) if available else 'none'}; unavailable outputs: "
            f"{', '.join(unavailable) if unavailable else 'none'}."
        )
        limitations = tuple(
            [f"{name} output was not supplied." for name in unavailable]
            + [
                "The agent receives structured outputs only and does not analyze a raw image.",
                "No diagnosis, disease probability, medical severity score, or clinical risk percentage is produced.",
            ]
        )
        summary_by_name = dict(summaries)
        return VisionAgentResult(
            overall_status=status,
            finding_summary=finding,
            image_quality_summary=summary_by_name["image_quality"],
            localization_summary=summary_by_name["localization"],
            spectral_summary=summary_by_name["reconstruction"],
            feature_summary=summary_by_name["spectral_features"],
            change_summary=summary_by_name["monitoring_change"],
            ml_summary=summary_by_name["ml_output"],
            available_evidence=available,
            limitations=limitations,
            safety_message=_SAFETY_MESSAGE,
        )
