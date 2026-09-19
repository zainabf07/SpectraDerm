"""Deterministic document-processing façade for the frozen Module U corpus.

Module U Step 1 owns the curated source catalog and the chunking algorithm.
This module deliberately does not implement another chunker: it makes the
loading, normalization inspection, processing, and validation steps explicit
for callers that need a small reusable document-processing API.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .knowledge_base import KnowledgeChunk, KnowledgeSource, build_chunks, load_sources


_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"
_SOURCE_METADATA_FIELDS = (
    "title",
    "organization",
    "url",
    "topic",
    "category",
    "retrieved_at",
)


@dataclass(frozen=True)
class SourceDocument:
    """One locally cached source document with its Module U attribution."""

    source: KnowledgeSource
    path: Path
    text: str


@dataclass(frozen=True)
class ValidationResult:
    """Summary of integrity checks completed for a processed corpus."""

    source_count: int
    chunk_count: int
    unique_chunk_ids: bool
    non_empty_text: bool
    source_ids_preserved: bool
    metadata_preserved: bool

    @property
    def is_valid(self) -> bool:
        return all((
            self.unique_chunk_ids,
            self.non_empty_text,
            self.source_ids_preserved,
            self.metadata_preserved,
        ))


def clean_document_text(text: str) -> str:
    """Apply the idempotent, heading-safe normalization used for inspection.

    Module U source notes are already curated and cleaned.  This helper only
    standardizes line endings and incidental surrounding/trailing whitespace;
    it intentionally preserves headings and paragraph boundaries relied on by
    the frozen U Step 1 builder.
    """
    if not isinstance(text, str):
        raise TypeError("document text must be a string")
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def load_source_documents(data_dir: Path = _DATA_DIR) -> tuple[SourceDocument, ...]:
    """Load the U catalog and its seven cached ``sources/`` text documents."""
    manifest = json.loads((data_dir / "source_manifest.json").read_text(encoding="utf-8"))
    paths_by_source_id = {
        item["source_id"]: data_dir / item["cleaned_text_file"] for item in manifest["sources"]
    }
    documents = []
    for source in load_sources(data_dir):
        documents.append(SourceDocument(
            source=source, path=paths_by_source_id[source.source_id], text=source.cleaned_text
        ))
    return tuple(documents)


def clean_documents(documents: tuple[SourceDocument, ...]) -> tuple[SourceDocument, ...]:
    """Return a normalized, metadata-preserving view of source documents."""
    return tuple(
        SourceDocument(source=document.source, path=document.path, text=clean_document_text(document.text))
        for document in documents
    )


def documents_to_chunks(
    documents: tuple[SourceDocument, ...], data_dir: Path = _DATA_DIR
) -> tuple[KnowledgeChunk, ...]:
    """Convert the canonical document set through the frozen U Step 1 builder.

    The function validates that callers supplied the catalog for ``data_dir``;
    it then delegates all chunk IDs, sections, text, and metadata creation to
    :func:`spectraderm.rag.knowledge_base.build_chunks`.
    """
    canonical = load_source_documents(data_dir)
    if tuple(document.source.source_id for document in documents) != tuple(
        document.source.source_id for document in canonical
    ):
        raise ValueError("documents must be the complete canonical Module U source set")
    if tuple(clean_document_text(document.text) for document in documents) != tuple(
        clean_document_text(document.text) for document in canonical
    ):
        raise ValueError("documents do not match the canonical Module U source text")
    return build_chunks(data_dir)


def validate_chunks(
    chunks: tuple[KnowledgeChunk, ...], sources: tuple[KnowledgeSource, ...]
) -> ValidationResult:
    """Validate IDs, text, source coverage, and exact U attribution metadata."""
    source_by_id = {source.source_id: source for source in sources}
    unique_chunk_ids = len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    non_empty_text = all(bool(chunk.text.strip()) for chunk in chunks)
    source_ids_preserved = (
        bool(chunks)
        and {chunk.source_id for chunk in chunks} == set(source_by_id)
        and all(chunk.source_id in source_by_id for chunk in chunks)
    )
    metadata_preserved = all(
        chunk.source_id in source_by_id
        and all(getattr(chunk, field) == getattr(source_by_id[chunk.source_id], field) for field in _SOURCE_METADATA_FIELDS)
        for chunk in chunks
    )
    result = ValidationResult(
        source_count=len(sources), chunk_count=len(chunks), unique_chunk_ids=unique_chunk_ids,
        non_empty_text=non_empty_text, source_ids_preserved=source_ids_preserved,
        metadata_preserved=metadata_preserved,
    )
    if not result.is_valid:
        raise ValueError("processed chunks failed document-processing validation")
    return result


def process_knowledge_base(data_dir: Path = _DATA_DIR) -> tuple[KnowledgeChunk, ...]:
    """Process the complete local corpus using the U Step 1 source-of-truth builder."""
    documents = clean_documents(load_source_documents(data_dir))
    chunks = documents_to_chunks(documents, data_dir)
    validate_chunks(chunks, tuple(document.source for document in documents))
    return chunks
