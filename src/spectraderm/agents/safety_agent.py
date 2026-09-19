"""Deterministic safety gate for supplied SpectraDerm agent outputs.

This module checks presentation safety only. It does not inspect images,
calculate Q/R/S outputs, retrieve evidence, or make a diagnosis.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SafetyAgentInput:
    """Optional outputs from X/Y/Z and text proposed for downstream presentation."""

    vision_result: Any | None = None
    monitoring_result: Any | None = None
    evidence_result: Any | None = None
    finding_summary: str | None = None
    structured_finding: str | None = None
    proposed_action: str | None = None
    generated_text: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ClaimAssessment:
    """Transparent classification of one supplied presentation text."""

    claim: str
    classification: str
    allowed: bool


@dataclass(frozen=True)
class EvidenceProvenance:
    """Source-attributed evidence copied from Module Z without fabrication."""

    chunk_id: str | None
    source_id: str | None
    title: str | None
    organization: str | None
    url: str | None
    topic: str | None
    text: str | None


@dataclass(frozen=True)
class SafetyAgentResult:
    """Serializable safety decision for a future orchestrator consumer."""

    safety_status: str
    concern_level: str
    claim_assessment: tuple[ClaimAssessment, ...]
    professional_assessment_recommended: bool
    reasons: tuple[str, ...]
    blocked_claims: tuple[str, ...]
    allowed_claims: tuple[str, ...]
    evidence_used: tuple[EvidenceProvenance, ...]
    input_summary: Mapping[str, Any]
    limitations: tuple[str, ...]
    safety_message: str


_SAFETY_MESSAGE = (
    "This is an engineering safety gate, not a diagnostic system. It does not calculate medical risk, inspect raw "
    "images, recalculate change scores, establish disease progression, treat estimated spectral information as "
    "measured spectroscopy, or prescribe treatment. Model-derived change is not disease probability."
)
_PROFESSIONAL_CONTEXT_PATTERNS = (
    "professional assessment", "consult a healthcare professional", "seek medical attention",
    "see a doctor", "see a dermatologist", "contact a healthcare provider",
    "contact a gp", "contacting a gp", "see a gp", "speak to a gp",
    "see a board-certified dermatologist", "consult a dermatologist",
)
# Monitoring patterns that count as persistent (not one-off) model-derived
# change. Persistence alone never triggers a referral; it must be paired with
# retrieved evidence that itself contains professional-assessment context.
_PERSISTENT_TRENDS = {"increasing_change"}
_PERSISTENT_PREVIOUS_SCORE = 39.0  # Module Q "Stable" upper bound


def _field(value: Any, name: str) -> Any | None:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _text(value: Any | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _source_value(evidence: Any, name: str) -> Any | None:
    source = _field(evidence, "source")
    source_value = _field(source, name) if source is not None else None
    return source_value if source_value is not None else _field(evidence, name)


def _provenance(evidence_result: Any | None) -> tuple[EvidenceProvenance, ...]:
    items = _field(evidence_result, "retrieved_evidence") if evidence_result is not None else ()
    if not items:
        return ()
    return tuple(EvidenceProvenance(
        chunk_id=_source_value(item, "chunk_id"), source_id=_source_value(item, "source_id"),
        title=_source_value(item, "title"), organization=_source_value(item, "organization"),
        url=_source_value(item, "url"), topic=_source_value(item, "topic"), text=_field(item, "text"),
    ) for item in items)


def _classify(text: str, evidence_available: bool) -> tuple[ClaimAssessment, ...]:
    """Classify simple unsafe patterns; this is a transparent safety filter, not clinical NLP."""
    lowered = text.lower()
    patterns = (
        ("disease_probability_claim", r"\b\d+(?:\.\d+)?%\s*(?:chance|risk|probability)\b|\bdisease probability\b"),
        ("diagnostic_claim", r"\b(this|it|model)\s+(?:proves?|confirms?|is definitely)\b|\byou have\b|\bthe patient has\b"),
        ("progression_claim", r"\bdisease (?:is )?(?:progressing|worsening)\b|\bcondition is worsening\b"),
        ("biomarker_claim", r"\b(?:spectral )?band\b.*\b(?:proves?|confirms?)\b|\b(?:hemoglobin|melanin|collagen|water) biomarker\b|\breconstructed spectrum measures\b"),
        ("treatment_claim", r"\b(?:prescription|prescribe|take \w+|apply \w+|medication|treatment plan)\b"),
    )
    unsafe_assessments = tuple(
        ClaimAssessment(text, classification, False)
        for classification, pattern in patterns
        if re.search(pattern, lowered)
    )
    if unsafe_assessments:
        return unsafe_assessments
    if any(term in lowered for term in ("model-derived", "estimated", "change score", "monitoring trend")):
        return (ClaimAssessment(text, "acceptable_model_claim", True),)
    if evidence_available:
        return (ClaimAssessment(text, "acceptable_evidence_claim", True),)
    return (ClaimAssessment(text, "unsupported_medical_claim", False),)


def _professional_context(evidence: tuple[EvidenceProvenance, ...]) -> bool:
    return any(
        any(pattern in (item.text or "").lower() for pattern in _PROFESSIONAL_CONTEXT_PATTERNS)
        for item in evidence
    )


def _persistent_change(monitoring: Any | None) -> bool:
    """True when supplied monitoring output shows sustained, not single-scan, change."""
    if monitoring is None:
        return False
    if str(_field(monitoring, "trend") or "").lower() in _PERSISTENT_TRENDS:
        return True
    previous = _field(monitoring, "previous_change_score")
    return (
        str(_field(monitoring, "current_status") or "").lower() == "changed"
        and isinstance(previous, (int, float)) and not isinstance(previous, bool)
        and previous > _PERSISTENT_PREVIOUS_SCORE
    )


class SafetyAgent:
    """Evaluate supplied output safety using fixed, deterministic rules."""

    def evaluate(self, agent_input: SafetyAgentInput) -> SafetyAgentResult:
        if not isinstance(agent_input, SafetyAgentInput):
            raise TypeError("agent_input must be a SafetyAgentInput")
        vision = agent_input.vision_result
        evidence_result = agent_input.evidence_result
        finding = _first_text(
            agent_input.finding_summary, agent_input.structured_finding,
            _field(vision, "structured_finding"), _field(vision, "finding_summary"),
        )
        evidence = _provenance(evidence_result)
        grounding = _field(evidence_result, "grounding_status") if evidence_result is not None else None
        explanation = _first_text(_field(evidence_result, "explanation"), agent_input.generated_text)
        texts = tuple(text for text in (explanation, _text(agent_input.proposed_action), _text(agent_input.generated_text)) if text)
        assessments = tuple(item for text in texts for item in _classify(text, bool(evidence)))
        blocked = tuple(text for text in texts if any(item.claim == text and not item.allowed for item in assessments))
        allowed = tuple(text for text in texts if all(item.allowed for item in assessments if item.claim == text))
        unsafe = bool(blocked)
        missing_finding = not finding
        insufficient_grounding = grounding in {"insufficient_evidence", "no_query"}
        missing_evidence = not evidence
        reasons: list[str] = []
        limitations: list[str] = []
        if missing_finding:
            reasons.append("No model-derived finding was supplied.")
            limitations.append("A meaningful interpretation cannot be supported without a supplied finding.")
        if missing_evidence:
            reasons.append("No retrieved evidence was supplied.")
            limitations.append("No outside medical knowledge is used to fill missing evidence.")
        if insufficient_grounding:
            reasons.append("The supplied evidence result reports insufficient grounding.")
        if unsafe:
            reasons.append("Potentially unsafe or overly strong supplied claim language was detected.")
        if unsafe:
            status, concern = "caution_required", "high"
        elif missing_finding or missing_evidence or insufficient_grounding:
            status, concern = "insufficient_evidence", "low"
        elif _professional_context(evidence) and (
            agent_input.monitoring_result is None or _persistent_change(agent_input.monitoring_result)
        ):
            status, concern = "professional_assessment_consideration", "moderate"
            reasons.append("Retrieved evidence explicitly contains context for considering professional assessment.")
            if agent_input.monitoring_result is not None:
                reasons.append("Supplied monitoring output shows persistent model-derived change across observations.")
        else:
            status, concern = "safe_to_present", "low"
            reasons.append("Supplied finding and evidence contain no blocked deterministic claim patterns.")
        professional = status == "professional_assessment_consideration"
        monitoring = agent_input.monitoring_result
        input_summary = {
            "finding_available": bool(finding),
            "monitoring_available": monitoring is not None,
            "evidence_result_available": evidence_result is not None,
            "grounding_status": grounding,
            "evidence_count": len(evidence),
            "proposed_action_available": bool(_text(agent_input.proposed_action)),
            "generated_text_available": bool(_text(agent_input.generated_text)),
        }
        if monitoring is None:
            limitations.append("Monitoring context was not supplied.")
        if evidence_result is None:
            limitations.append("Evidence Agent output was not supplied.")
        if vision is None and not agent_input.finding_summary and not agent_input.structured_finding:
            limitations.append("Vision Agent output was not supplied.")
        return SafetyAgentResult(
            safety_status=status, concern_level=concern, claim_assessment=assessments,
            professional_assessment_recommended=professional, reasons=tuple(reasons),
            blocked_claims=blocked, allowed_claims=allowed, evidence_used=evidence,
            input_summary=input_summary, limitations=tuple(limitations), safety_message=_SAFETY_MESSAGE,
        )
