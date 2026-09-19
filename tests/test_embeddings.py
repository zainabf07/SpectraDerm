import numpy as np
import pytest

from spectraderm.rag.embeddings import FastEmbedEmbedder


class FakeEmbeddingBackend:
    """Deterministic backend for unit tests; production uses FastEmbed."""

    def embed(self, documents):
        for document in documents:
            lowered = document.lower()
            yield np.asarray([
                sum(word in lowered for word in ("pigmentation", "melanin", "dark spot", "hyperpigmentation")),
                sum(word in lowered for word in ("redness", "flushing", "vascular", "blood vessel", "rosacea")),
                sum(word in lowered for word in ("professional", "assessment", "warning", "mole", "melanoma")),
                1.0,
            ], dtype=np.float32)


def embedder():
    return FastEmbedEmbedder(backend=FakeEmbeddingBackend())


def test_multiple_text_embeddings_have_finite_2d_normalized_shape():
    vectors = embedder().embed_texts(["pigmentation and melanin", "visible redness"])
    assert vectors.shape == (2, 4)
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)


def test_query_embedding_is_finite_normalized_1d_vector():
    vector = embedder().embed_query("professional assessment warning signs")
    assert vector.shape == (4,)
    assert np.isfinite(vector).all()
    assert np.isclose(np.linalg.norm(vector), 1.0)


@pytest.mark.parametrize("value", [[], [""], ["  "], "single text"])
def test_empty_or_invalid_text_input_is_rejected(value):
    with pytest.raises((TypeError, ValueError)):
        embedder().embed_texts(value)


def test_empty_or_invalid_query_is_rejected():
    with pytest.raises(ValueError):
        embedder().embed_query("")
    with pytest.raises(ValueError):
        embedder().embed_query("   ")
