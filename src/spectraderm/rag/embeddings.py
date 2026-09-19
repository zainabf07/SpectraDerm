"""FastEmbed-backed, normalized text embeddings for Module U retrieval."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingBackend(Protocol):
    """Minimal protocol implemented by ``fastembed.TextEmbedding``."""

    def embed(self, documents: Sequence[str]) -> Any: ...


def _validate_texts(texts: Sequence[str]) -> list[str]:
    if isinstance(texts, (str, bytes)):
        raise TypeError("texts must be a sequence of strings, not a single string")
    values = list(texts)
    if not values:
        raise ValueError("texts must not be empty")
    if any(not isinstance(text, str) or not text.strip() for text in values):
        raise ValueError("texts must contain only non-empty strings")
    return values


def _normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("embedding backend must return a non-empty 2D matrix")
    if not np.isfinite(matrix).all():
        raise ValueError("embedding backend returned non-finite values")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding backend returned a zero-norm vector")
    return matrix / norms


def _cache_dir() -> str:
    """Keep the downloaded ONNX model with the project instead of the OS temp dir.

    FastEmbed defaults to the system temp directory, which is cleared by the OS
    and forces a re-download. ``FASTEMBED_CACHE_PATH`` still overrides this.
    """
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    configured = os.getenv("FASTEMBED_CACHE_PATH")
    if configured:
        return configured
    from spectraderm.config import get_settings

    return str(get_settings().models_dir / "fastembed_cache")


class FastEmbedEmbedder:
    """Lazy CPU embedding wrapper using FastEmbed's ONNX-backed text model."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, backend: EmbeddingBackend | None = None) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string")
        self.model_name = model_name
        self._backend = backend

    def _get_backend(self) -> EmbeddingBackend:
        if self._backend is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:  # pragma: no cover - depends on local setup
                raise ImportError("FastEmbed is required; install the project's FastEmbed dependency.") from exc
            self._backend = TextEmbedding(model_name=self.model_name, cache_dir=_cache_dir())
        return self._backend

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Return finite, L2-normalized embeddings with shape ``(n, dimension)``."""
        values = _validate_texts(texts)
        vectors = np.asarray(list(self._get_backend().embed(values)), dtype=np.float32)
        return _normalize(vectors)

    def embed_query(self, text: str) -> np.ndarray:
        """Return a finite, L2-normalized embedding with shape ``(dimension,)``."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("query must be a non-empty string")
        return self.embed_texts([text])[0]


_DEFAULT_EMBEDDER: FastEmbedEmbedder | None = None


def _default_embedder() -> FastEmbedEmbedder:
    global _DEFAULT_EMBEDDER
    if _DEFAULT_EMBEDDER is None:
        _DEFAULT_EMBEDDER = FastEmbedEmbedder()
    return _DEFAULT_EMBEDDER


def embed_texts(texts: Sequence[str]) -> np.ndarray:
    """Embed texts with the default FastEmbed model."""
    return _default_embedder().embed_texts(texts)


def embed_query(text: str) -> np.ndarray:
    """Embed one query with the default FastEmbed model."""
    return _default_embedder().embed_query(text)
