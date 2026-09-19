"""Live retrieval (+ optional generation) adapter over Modules U and W.

When no language provider is configured, this behaves exactly as before:
retrieval-only, with an empty explanation and grounding_status of
"explanation_unavailable". When an LLMProvider is injected (e.g. an
OpenAILLMProvider backed by OPENAI_API_KEY), retrieved, attributed evidence is
also used to generate a real evidence-grounded explanation via Module W's
existing constrained prompt. A failed generation call degrades to the same
retrieval-only output rather than failing the whole request.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from spectraderm.rag.llm import LLMProvider
from spectraderm.rag.rag_pipeline import (
    RAGResult,
    SafetyMetadata,
    SourceMetadata,
    RetrievedEvidence,
    build_evidence_prompt,
    construct_retrieval_query,
)
from spectraderm.rag.retriever import VectorRetriever, load_or_build_retriever


logger = logging.getLogger(__name__)


# Knowledge-base passages carry curator scope notes ("retained for retrieval",
# "does not mean SpectraDerm detects ..."). They are for the model, not the
# reader, so the source-only explanation skips them.
_CURATION_NOTE = re.compile(
    r"spectraderm|retained|limited|scope|this source|source-context|it is not a|it does not|feature|score|estimated spectral",
    re.IGNORECASE,
)


def _first_sentences(text: str, limit: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    kept = [item for item in sentences if item and not _CURATION_NOTE.search(item)][:limit]
    return " ".join(kept)


def _describe_llm_error(error: Exception) -> str:
    response = getattr(error, "response", None)
    if response is not None:
        try:
            detail = response.json().get("error", {})
            return f"HTTP {response.status_code} {detail.get('code') or ''}".strip()
        except Exception:
            return f"HTTP {response.status_code}"
    return type(error).__name__


FALLBACK_CLOSING = (
    "The observed change alone does not identify a specific condition; these sources give general context only."
)


def extractive_explanation(model_finding: str, evidence: tuple[RetrievedEvidence, ...]) -> str:
    """Evidence-grounded explanation assembled only from retrieved source text.

    Used when no language model is available. It restates the model-derived
    finding and quotes the leading sentences of each retrieved passage with
    its organization, so no medical claim is added beyond the sources.
    """
    observed = model_finding.split(" General context", 1)[0].strip()
    lines = [f"What was observed: {observed}", "", "Why it can matter:"]
    for item in evidence:
        summary = _first_sentences(item.text)
        if summary:
            lines.append(f"- {summary} [{item.source.organization}]")
    lines.append("")
    lines.append(FALLBACK_CLOSING)
    return "\n".join(lines)


class RetrievalOnlyRAGPipeline:
    """Use U retrieval, plus W generation only when a language provider is injected."""

    def __init__(self, retriever: VectorRetriever | None = None, llm: LLMProvider | None = None) -> None:
        self._retriever = retriever
        self._llm = llm
        self.last_explanation_source = "none"

    def _get_retriever(self) -> VectorRetriever:
        if self._retriever is None:
            self._retriever = load_or_build_retriever()
        return self._retriever

    def run(self, model_finding: str, top_k: int = 3) -> RAGResult:
        query = construct_retrieval_query(model_finding)
        if not query:
            return RAGResult(
                model_finding="", query="", retrieved_evidence=(), explanation="",
                safety=SafetyMetadata(True, True, True, True, True, True),
            )
        results = self._get_retriever().retrieve(query, top_k=top_k)
        evidence = tuple(
            RetrievedEvidence(
                chunk_id=item.chunk_id, text=item.text, score=item.score,
                source=SourceMetadata(
                    source_id=item.source_id, title=item.title, organization=item.organization,
                    url=item.url, topic=item.topic,
                ),
            )
            for item in results
        )
        explanation = ""
        explanation_source = "none"
        if evidence and self._llm is not None:
            try:
                explanation = self._llm.generate(
                    build_evidence_prompt(model_finding.strip(), evidence)
                ).strip()
            except Exception as error:
                # One concise line: a missing-credit / rate-limit error would
                # otherwise print a full traceback on every analysis.
                logger.warning(
                    "Language-model explanation unavailable (%s); using source-only explanation.",
                    _describe_llm_error(error),
                )
                explanation = ""
            if explanation:
                explanation_source = "language_model"
        if evidence and not explanation:
            # No language model (or it failed, e.g. no API credits): build the
            # explanation only from the retrieved, attributed source text.
            explanation = extractive_explanation(model_finding.strip(), evidence)
            explanation_source = "retrieved_sources"
        self.last_explanation_source = explanation_source
        return RAGResult(
            model_finding=model_finding.strip(), query=query, retrieved_evidence=evidence,
            explanation=explanation,
            safety=SafetyMetadata(True, True, True, True, True, not bool(evidence)),
        )
