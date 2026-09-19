"""Agent-level delegation to the frozen Module W evidence-grounded RAG pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from spectraderm.rag.rag_pipeline import RAGResult, RetrievedEvidence, SourceMetadata


class RAGPipelineLike(Protocol):
    """The existing Module W interface consumed through dependency injection."""

    def run(self, model_finding: str, top_k: int = 3) -> RAGResult: ...


@dataclass(frozen=True)
class EvidenceAgentInput:
    """Structured upstream finding and optional monitoring context for Module W."""

    structured_finding: Any | None = None
    monitoring_result: Any | None = None
    query: str | None = None
    top_k: int = 3
    additional_context: str | None = None


@dataclass(frozen=True)
class EvidenceAgentResult:
    """Preserves Module W evidence separately from its grounded explanation."""

    query: str
    finding_summary: str
    monitoring_context: Any | None
    retrieved_evidence: tuple[RetrievedEvidence, ...]
    source_metadata: tuple[SourceMetadata, ...]
    explanation: str | None
    evidence_count: int
    grounding_status: str
    limitations: tuple[str, ...]
    safety_message: str


_SAFETY_MESSAGE = (
    "This agent delegates to Module W for evidence-grounded language. Model-derived findings and monitoring "
    "trends are not diagnoses or disease probabilities. An increasing model-derived change is not proof of disease "
    "progression. Estimated spectral information is not measured spectroscopy, and spectral features are not "
    "confirmed biomarkers. Retrieved evidence and source attribution are preserved without fabrication."
)


def _field(value: Any, name: str) -> Any | None:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _finding_text(value: Any | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    for field in ("structured_finding", "finding_summary", "summary"):
        candidate = _field(value, field)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _monitoring_text(value: Any | None) -> str:
    """Use only supplied engineering labels; do not interpret numerical scores."""
    if value is None:
        return ""
    trend = _field(value, "trend")
    status = _field(value, "current_status")
    parts = []
    if trend is not None and str(trend).strip():
        parts.append(f"Model-derived monitoring trend: {str(trend).strip()}.")
    if status is not None and str(status).strip():
        parts.append(f"Model-derived monitoring status: {str(status).strip()}.")
    return " ".join(parts)


def construct_evidence_request(agent_input: EvidenceAgentInput) -> str:
    """Select explicit query or combine only supplied model-derived context."""
    if not isinstance(agent_input, EvidenceAgentInput):
        raise TypeError("agent_input must be an EvidenceAgentInput")
    if agent_input.query is not None:
        if not isinstance(agent_input.query, str):
            raise TypeError("query must be a string when supplied")
        if agent_input.query.strip():
            return agent_input.query.strip()
    finding = _finding_text(agent_input.structured_finding)
    additional = agent_input.additional_context
    if additional is not None and not isinstance(additional, str):
        raise TypeError("additional_context must be a string when supplied")
    parts = [part for part in (finding, additional.strip() if additional else "", _monitoring_text(agent_input.monitoring_result)) if part]
    return "\n".join(parts)


class EvidenceAgent:
    """Thin deterministic wrapper that delegates retrieval and generation to Module W."""

    def __init__(self, rag_pipeline: RAGPipelineLike) -> None:
        self.rag_pipeline = rag_pipeline

    def interpret(self, agent_input: EvidenceAgentInput) -> EvidenceAgentResult:
        if not isinstance(agent_input, EvidenceAgentInput):
            raise TypeError("agent_input must be an EvidenceAgentInput")
        if not isinstance(agent_input.top_k, int) or isinstance(agent_input.top_k, bool) or agent_input.top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        request = construct_evidence_request(agent_input)
        finding = _finding_text(agent_input.structured_finding)
        if not request:
            return EvidenceAgentResult(
                query="", finding_summary=finding, monitoring_context=agent_input.monitoring_result,
                retrieved_evidence=(), source_metadata=(), explanation=None, evidence_count=0,
                grounding_status="no_query",
                limitations=("No model-derived finding, explicit query, or usable context was supplied.",),
                safety_message=_SAFETY_MESSAGE,
            )
        rag_result = self.rag_pipeline.run(request, top_k=agent_input.top_k)
        evidence = tuple(rag_result.retrieved_evidence)
        metadata = tuple(rag_result.source_metadata)
        explanation = rag_result.explanation.strip() if isinstance(rag_result.explanation, str) and rag_result.explanation.strip() else None
        if not evidence:
            grounding_status = "insufficient_evidence"
            limitations = ("No retrieved evidence was returned; no medical evidence is manufactured.",)
        elif explanation is None:
            grounding_status = "explanation_unavailable"
            limitations = ("Retrieved evidence is available, but no generated explanation was returned.",)
        else:
            grounding_status = "evidence_found"
            limitations = ("Explanation grounding and source handling remain governed by delegated Module W.",)
        return EvidenceAgentResult(
            query=rag_result.query, finding_summary=finding, monitoring_context=agent_input.monitoring_result,
            retrieved_evidence=evidence, source_metadata=metadata, explanation=explanation,
            evidence_count=len(evidence), grounding_status=grounding_status,
            limitations=limitations, safety_message=_SAFETY_MESSAGE,
        )
