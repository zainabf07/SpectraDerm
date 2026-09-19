import numpy as np
import pytest

from spectraderm.rag.embeddings import FastEmbedEmbedder
from spectraderm.rag.knowledge_base import build_chunks
from spectraderm.rag.retriever import VectorRetriever, build_index


class FakeEmbeddingBackend:
    def embed(self, documents):
        for document in documents:
            lowered = document.lower()
            yield np.asarray([
                3 * sum(word in lowered for word in ("pigmentation", "melanin", "dark spot", "hyperpigmentation")),
                3 * sum(word in lowered for word in ("redness", "flushing", "vascular", "blood vessel", "rosacea")),
                3 * sum(word in lowered for word in ("professional", "assessment", "warning", "mole", "melanoma")),
                1.0,
            ], dtype=np.float32)


def make_retriever(tmp_path):
    model = FastEmbedEmbedder(backend=FakeEmbeddingBackend())
    metadata = build_index(embedder=model, index_dir=tmp_path)
    return VectorRetriever.load(index_dir=tmp_path, embedder=model), metadata


def test_all_existing_chunks_are_indexed_with_metadata(tmp_path):
    _, metadata = make_retriever(tmp_path)
    assert metadata.indexed_chunk_count == len(build_chunks()) == 14
    assert len(metadata.chunk_ids) == 14
    assert len(metadata.source_ids) == 7
    assert metadata.embedding_dimension == 4


def test_retrieval_limits_sorts_and_preserves_exact_attribution(tmp_path):
    retriever, _ = make_retriever(tmp_path)
    results = retriever.retrieve("pigmentation melanin", top_k=3)
    chunks = {chunk.chunk_id: chunk for chunk in build_chunks()}
    assert len(results) == 3
    assert [result.score for result in results] == sorted((result.score for result in results), reverse=True)
    for result in results:
        chunk = chunks[result.chunk_id]
        assert (result.source_id, result.text, result.title, result.organization, result.url, result.topic) == (
            chunk.source_id, chunk.text, chunk.title, chunk.organization, chunk.url, chunk.topic,
        )


def test_identical_queries_produce_deterministic_results(tmp_path):
    retriever, _ = make_retriever(tmp_path)
    assert retriever.retrieve("visible redness", top_k=5) == retriever.retrieve("visible redness", top_k=5)


@pytest.mark.parametrize("query", ["", " "])
def test_invalid_query_and_top_k_are_rejected(tmp_path, query):
    retriever, _ = make_retriever(tmp_path)
    with pytest.raises(ValueError):
        retriever.retrieve(query)
    with pytest.raises(ValueError):
        retriever.retrieve("pigmentation", top_k=0)


def test_pigmentation_redness_and_professional_assessment_queries_retrieve_expected_sources(tmp_path):
    retriever, _ = make_retriever(tmp_path)
    assert retriever.retrieve("pigmentation melanin dark spots", top_k=1)[0].source_id in {
        "medlineplus-skin-pigmentation-disorders", "aad-hyperpigmentation-dark-spots",
    }
    assert retriever.retrieve("visible redness flushing vascular blood vessels", top_k=1)[0].source_id == "aad-rosacea-signs-symptoms"
    assert retriever.retrieve("professional assessment warning signs changing mole melanoma", top_k=1)[0].source_id == "nhs-melanoma-symptoms"
