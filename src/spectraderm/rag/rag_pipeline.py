"""Evidence-grounded RAG orchestration for precomputed SpectraDerm findings.

This module receives an existing model-derived finding.  It does not calculate,
reinterpret, diagnose from, or assign probabilities to SpectraDerm outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .llm import LLMProvider
from .retriever import RetrievalResult


_NO_EVIDENCE_EXPLANATION = (
    "No retrieved medical evidence is available for this model-derived finding, "
    "so no evidence-grounded explanation can be provided."
)


class Retriever(Protocol):
    """The subset of the frozen Module U Step 2 retriever used by Module W."""

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]: ...


@dataclass(frozen=True)
class SourceMetadata:
    """Source attribution carried alongside one retrieved evidence chunk."""

    source_id: str
    title: str
    organization: str
    url: str
    topic: str


@dataclass(frozen=True)
class RetrievedEvidence:
    """An unmodified retrieved chunk plus its score and source attribution."""

    chunk_id: str
    text: str
    score: float
    source: SourceMetadata


@dataclass(frozen=True)
class SafetyMetadata:
    """Fixed boundaries communicated to callers of the RAG layer."""

    evidence_grounded: bool
    diagnosis_prohibited: bool
    disease_probabilities_prohibited: bool
    measured_spectrum_claims_prohibited: bool
    confirmed_biomarker_claims_prohibited: bool
    no_evidence_message: bool


@dataclass(frozen=True)
class RAGResult:
    """Separates model input, retrieved evidence, and generated explanation."""

    model_finding: str
    query: str
    retrieved_evidence: tuple[RetrievedEvidence, ...]
    explanation: str
    safety: SafetyMetadata

    @property
    def source_metadata(self) -> tuple[SourceMetadata, ...]:
        """Return the source metadata in the same order as retrieved evidence."""
        return tuple(item.source for item in self.retrieved_evidence)


def construct_retrieval_query(model_finding: str) -> str:
    """Create a deterministic retrieval query without adding medical interpretation."""
    if not isinstance(model_finding, str):
        raise TypeError("model_finding must be a string")
    finding = model_finding.strip()
    if not finding:
        return ""
    return (
        "SpectraDerm model-derived finding (not a diagnosis): "
        f"{finding}\n"
        "Retrieve only relevant source-attributed medical context."
    )


def _evidence_from_result(result: RetrievalResult) -> RetrievedEvidence:
    """Copy retrieval output without changing its text, IDs, or attribution."""
    return RetrievedEvidence(
        chunk_id=result.chunk_id,
        text=result.text,
        score=result.score,
        source=SourceMetadata(
            source_id=result.source_id,
            title=result.title,
            organization=result.organization,
            url=result.url,
            topic=result.topic,
        ),
    )


def build_evidence_prompt(model_finding: str, evidence: Sequence[RetrievedEvidence]) -> str:
    """Build a constrained prompt whose only medical context is retrieved evidence."""
    if not evidence:
        raise ValueError("evidence is required to build an evidence-grounded prompt")
    evidence_blocks = "\n\n".join(
        "[EVIDENCE chunk_id={chunk_id} source_id={source_id}]\n"
        "title: {title}\norganization: {organization}\nurl: {url}\ntopic: {topic}\n"
        "text: {text}\n[END EVIDENCE]".format(
            chunk_id=item.chunk_id,
            source_id=item.source.source_id,
            title=item.source.title,
            organization=item.source.organization,
            url=item.source.url,
            topic=item.source.topic,
            text=item.text,
        )
        for item in evidence
    )
    return f"""You are an evidence-grounded explanation component for SpectraDerm.

Model-derived finding (not medical knowledge and not a diagnosis):
{model_finding}

Rules:
- Use only the supplied evidence for any medical claim.
- Clearly distinguish the model-derived finding from retrieved medical knowledge.
- Never state or imply that the finding proves a disease, and never provide disease probabilities.
- Never call estimated spectral reconstruction a measured spectrum.
- Never claim RGB or spectral features are confirmed biomarkers.
- If the evidence is insufficient, say so explicitly.
- Recommend professional evaluation only when appropriate according to supplied evidence.
- Do not invent, alter, or add citations, source IDs, URLs, or facts.

Supplied retrieved evidence:
{evidence_blocks}

Write for a non-expert reading their own skin-monitoring report, in plain language,
at most 150 words, in exactly two short paragraphs:
1. Start with "What was observed:" and restate the model-derived finding simply.
2. Start with "Why it can matter:" and summarise what the supplied sources say,
   naming each source you use in square brackets, e.g. [NHS]. Say that the
   observed change alone does not identify a specific condition.
Follow every rule above."""


class RAGPipeline:
    """Retrieve attributed evidence and ask a language-only provider to explain it."""

    def __init__(self, retriever: Retriever, llm: LLMProvider) -> None:
        self.retriever = retriever
        self.llm = llm

    def run(self, model_finding: str, top_k: int = 3) -> RAGResult:
        """Run retrieval then generation; safely stop before generation without evidence."""
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        query = construct_retrieval_query(model_finding)
        if not query:
            return RAGResult(
                model_finding="", query="", retrieved_evidence=(), explanation=_NO_EVIDENCE_EXPLANATION,
                safety=SafetyMetadata(True, True, True, True, True, True),
            )
        retrieved = self.retriever.retrieve(query, top_k=top_k)
        evidence = tuple(_evidence_from_result(item) for item in retrieved)
        if not evidence:
            return RAGResult(
                model_finding=model_finding.strip(), query=query, retrieved_evidence=(),
                explanation=_NO_EVIDENCE_EXPLANATION,
                safety=SafetyMetadata(True, True, True, True, True, True),
            )
        explanation = self.llm.generate(build_evidence_prompt(model_finding.strip(), evidence))
        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("LLM provider returned an empty explanation")
        return RAGResult(
            model_finding=model_finding.strip(), query=query, retrieved_evidence=evidence,
            explanation=explanation.strip(),
            safety=SafetyMetadata(True, True, True, True, True, False),
        )
