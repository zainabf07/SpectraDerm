"""Deterministic workflow coordinator for the specialized SpectraDerm agents.

The orchestrator preserves agent results and uses only Module AA's explicit
professional-assessment decision to select the downstream branch.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from spectraderm.agents.evidence_agent import EvidenceAgentInput
from spectraderm.agents.monitoring_agent import MonitoringAgentInput
from spectraderm.agents.product_agent import ProductAgentInput
from spectraderm.agents.referral_agent import ReferralAgentInput
from spectraderm.agents.safety_agent import SafetyAgentInput
from spectraderm.agents.vision_agent import VisionAgentInput


@dataclass(frozen=True)
class OrchestratorInput:
    """Existing structured agent inputs and the transient location for an AC call."""

    vision_input: Any | None = None
    monitoring_input: Any | None = None
    evidence_input: EvidenceAgentInput | None = None
    safety_input: SafetyAgentInput | None = None
    product_input: ProductAgentInput | None = None
    referral_location: dict[str, Any] | None = None
    referral_radius_km: float = 25.0


@dataclass(frozen=True)
class OrchestratorResult:
    status: str
    vision_result: Any | None
    monitoring_result: Any | None
    evidence_result: Any | None
    safety_result: Any | None
    product_result: Any | None
    referral_result: Any | None
    recommended_path: str
    errors: tuple[str, ...]
    metadata: dict[str, Any]


def _field(value: Any, name: str) -> Any | None:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _invoke(agent: Any, method: str, value: Any, label: str, errors: list[str]) -> Any | None:
    """Call a specialized agent once and retain an explicit, non-fabricated failure."""
    try:
        return getattr(agent, method)(value)
    except Exception as exc:  # The downstream branch must not conceal an agent failure.
        errors.append(f"{label}_failed:{type(exc).__name__}")
        return None


class OrchestratorAgent:
    """Coordinate existing agents without reproducing any specialized decision logic."""

    def __init__(
        self, vision_agent: Any, monitoring_agent: Any, evidence_agent: Any,
        safety_agent: Any, product_agent: Any, referral_agent: Any,
    ) -> None:
        self._vision_agent = vision_agent
        self._monitoring_agent = monitoring_agent
        self._evidence_agent = evidence_agent
        self._safety_agent = safety_agent
        self._product_agent = product_agent
        self._referral_agent = referral_agent

    def run(self, agent_input: OrchestratorInput) -> OrchestratorResult:
        if not isinstance(agent_input, OrchestratorInput):
            raise TypeError("agent_input must be an OrchestratorInput")
        errors: list[str] = []
        completed_steps: list[str] = []

        vision_payload = agent_input.vision_input if agent_input.vision_input is not None else VisionAgentInput()
        vision = _invoke(self._vision_agent, "interpret", vision_payload, "vision", errors)
        if vision is not None:
            completed_steps.append("vision")
        monitoring_payload = agent_input.monitoring_input if agent_input.monitoring_input is not None else MonitoringAgentInput()
        monitoring = _invoke(self._monitoring_agent, "interpret", monitoring_payload, "monitoring", errors)
        if monitoring is not None:
            completed_steps.append("monitoring")
        evidence_template = agent_input.evidence_input or EvidenceAgentInput()
        evidence_input = replace(evidence_template, structured_finding=vision, monitoring_result=monitoring)
        evidence = _invoke(self._evidence_agent, "interpret", evidence_input, "evidence", errors)
        if evidence is not None:
            completed_steps.append("evidence")
        safety_template = agent_input.safety_input or SafetyAgentInput()
        safety_input = replace(
            safety_template, vision_result=vision, monitoring_result=monitoring, evidence_result=evidence,
        )
        safety = _invoke(self._safety_agent, "evaluate", safety_input, "safety", errors)
        if safety is not None:
            completed_steps.append("safety")

        decision = _field(safety, "professional_assessment_recommended") if safety is not None else None
        metadata = {"completed_steps": tuple(completed_steps), "downstream_called": None}
        if type(decision) is not bool:
            if safety is not None:
                errors.append("safety_invalid_or_missing_referral_decision")
            return OrchestratorResult(
                "blocked", vision, monitoring, evidence, safety, None, None, "insufficient_information",
                tuple(errors), metadata,
            )
        if decision:
            referral_input = ReferralAgentInput(
                safety_result=safety, location=agent_input.referral_location, radius_km=agent_input.referral_radius_km,
            )
            referral = _invoke(self._referral_agent, "refer", referral_input, "referral", errors)
            metadata["downstream_called"] = "referral"
            status = "partial" if errors else "completed"
            return OrchestratorResult(
                status, vision, monitoring, evidence, safety, None, referral, "referral", tuple(errors), metadata,
            )

        # A product path has support only when the caller supplied vision context or explicit AB input.
        if agent_input.vision_input is None and agent_input.product_input is None:
            return OrchestratorResult(
                "partial" if errors else "blocked", vision, monitoring, evidence, safety, None, None,
                "insufficient_information", tuple(errors), metadata,
            )
        product_template = agent_input.product_input or ProductAgentInput()
        product_input = replace(
            product_template, vision_result=vision, monitoring_result=monitoring,
            evidence_result=evidence, safety_result=safety,
        )
        product = _invoke(self._product_agent, "recommend", product_input, "product", errors)
        metadata["downstream_called"] = "product"
        status = "partial" if errors else "completed"
        return OrchestratorResult(
            status, vision, monitoring, evidence, safety, product, None, "product", tuple(errors), metadata,
        )

    orchestrate = run
