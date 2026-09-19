"""Persisted NumPy cosine-similarity retrieval over Module U Step 1 chunks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .embeddings import DEFAULT_EMBEDDING_MODEL, FastEmbedEmbedder
from .knowledge_base import KnowledgeChunk, build_chunks


DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base" / "index"
_MATRIX_FILE = "embeddings.npy"
_CHUNKS_FILE = "chunks.json"
_METADATA_FILE = "index_metadata.json"


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    source_id: str
    text: str
    score: float
    title: str
    organization: str
    url: str
    topic: str


@dataclass(frozen=True)
class IndexMetadata:
    embedding_model: str
    embedding_dimension: int
    indexed_chunk_count: int
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    created_at_utc: str
    normalization: str


def _normalized_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("index embedding matrix must be non-empty and 2D")
    if not np.isfinite(matrix).all():
        raise ValueError("index embedding matrix contains non-finite values")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("index embedding matrix contains a zero-norm vector")
    return matrix / norms


def build_index(
    embedder: FastEmbedEmbedder | None = None,
    index_dir: Path = DEFAULT_INDEX_DIR,
) -> IndexMetadata:
    """Embed frozen Step 1 chunks and persist a rebuildable NumPy index."""
    chunks = build_chunks()
    if not chunks:
        raise ValueError("Module U Step 1 returned no chunks")
    embedder = embedder or FastEmbedEmbedder()
    matrix = _normalized_matrix(embedder.embed_texts([chunk.text for chunk in chunks]))
    if matrix.shape[0] != len(chunks):
        raise ValueError("embedding count does not match Module U chunk count")
    index_dir.mkdir(parents=True, exist_ok=True)
    metadata = IndexMetadata(
        embedding_model=embedder.model_name,
        embedding_dimension=int(matrix.shape[1]),
        indexed_chunk_count=len(chunks),
        source_ids=tuple(sorted({chunk.source_id for chunk in chunks})),
        chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        normalization="l2",
    )
    np.save(index_dir / _MATRIX_FILE, matrix)
    (index_dir / _CHUNKS_FILE).write_text(
        json.dumps([asdict(chunk) for chunk in chunks], indent=2, sort_keys=True), encoding="utf-8"
    )
    (index_dir / _METADATA_FILE).write_text(
        json.dumps(asdict(metadata), indent=2, sort_keys=True), encoding="utf-8"
    )
    return metadata


class VectorRetriever:
    """Top-K attributed cosine retrieval; retrieval is not medical interpretation."""

    def __init__(
        self,
        matrix: np.ndarray,
        chunks: tuple[KnowledgeChunk, ...],
        metadata: IndexMetadata,
        embedder: FastEmbedEmbedder | None = None,
    ) -> None:
        self.matrix = _normalized_matrix(matrix)
        self.chunks = chunks
        self.metadata = metadata
        self.embedder = embedder or FastEmbedEmbedder(metadata.embedding_model)
        if self.matrix.shape != (len(chunks), metadata.embedding_dimension):
            raise ValueError("index matrix, chunks, and metadata dimensions do not agree")
        if tuple(chunk.chunk_id for chunk in chunks) != metadata.chunk_ids:
            raise ValueError("persisted chunk IDs do not agree with index metadata")

    @classmethod
    def load(cls, index_dir: Path = DEFAULT_INDEX_DIR, embedder: FastEmbedEmbedder | None = None) -> "VectorRetriever":
        """Load a previously built index without modifying chunk text or metadata."""
        try:
            matrix = np.load(index_dir / _MATRIX_FILE, allow_pickle=False)
            raw_chunks = json.loads((index_dir / _CHUNKS_FILE).read_text(encoding="utf-8"))
            raw_metadata: dict[str, Any] = json.loads((index_dir / _METADATA_FILE).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError("retrieval index is missing; call build_index() first") from exc
        raw_metadata["source_ids"] = tuple(raw_metadata["source_ids"])
        raw_metadata["chunk_ids"] = tuple(raw_metadata["chunk_ids"])
        return cls(matrix, tuple(KnowledgeChunk(**item) for item in raw_chunks), IndexMetadata(**raw_metadata), embedder)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Return at most ``top_k`` source-attributed candidates by cosine similarity."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        query_vector = self.embedder.embed_query(query)
        if query_vector.shape != (self.metadata.embedding_dimension,):
            raise ValueError("query embedding dimension does not match index")
        if not np.isfinite(query_vector).all():
            raise ValueError("query embedding contains non-finite values")
        query_norm = float(np.linalg.norm(query_vector))
        if query_norm == 0.0:
            raise ValueError("query embedding has zero norm")
        query_vector = query_vector / query_norm
        scores = self.matrix @ query_vector
        ranking = sorted(range(len(self.chunks)), key=lambda index: (-float(scores[index]), self.chunks[index].chunk_id))
        return [
            RetrievalResult(
                chunk_id=chunk.chunk_id, source_id=chunk.source_id, text=chunk.text,
                score=float(scores[index]), title=chunk.title, organization=chunk.organization,
                url=chunk.url, topic=chunk.topic,
            )
            for index in ranking[:top_k]
            for chunk in (self.chunks[index],)
        ]


def load_or_build_retriever(
    index_dir: Path = DEFAULT_INDEX_DIR,
    embedder: FastEmbedEmbedder | None = None,
) -> VectorRetriever:
    """Load the persisted index, building it from Step 1 chunks when absent."""
    if not (index_dir / _MATRIX_FILE).exists():
        build_index(embedder=embedder, index_dir=index_dir)
    return VectorRetriever.load(index_dir=index_dir, embedder=embedder)
