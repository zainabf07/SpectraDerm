import numpy as np

from spectraderm.rag.document_processing import (
    clean_document_text,
    clean_documents,
    documents_to_chunks,
    load_source_documents,
    process_knowledge_base,
    validate_chunks,
)
from spectraderm.rag.knowledge_base import build_chunks, load_sources
from spectraderm.rag.embeddings import FastEmbedEmbedder
from spectraderm.rag.retriever import VectorRetriever, build_index


def test_all_existing_chunks_are_processed_by_the_u_builder():
    documents = load_source_documents()
    chunks = process_knowledge_base()
    assert len(documents) == 7
    assert len(chunks) == 14
    assert chunks == build_chunks()


def test_processed_chunks_have_unique_ids_nonempty_text_and_preserved_sources():
    documents = load_source_documents()
    chunks = process_knowledge_base()
    validation = validate_chunks(chunks, tuple(document.source for document in documents))
    assert validation.is_valid
    assert validation.unique_chunk_ids
    assert validation.non_empty_text
    assert validation.source_ids_preserved
    assert validation.metadata_preserved


def test_processing_is_deterministic_for_ids_text_and_metadata():
    first = process_knowledge_base()
    second = process_knowledge_base()
    assert [(chunk.chunk_id, chunk.text, chunk.section, chunk.source_id, chunk.title,
             chunk.organization, chunk.url, chunk.topic, chunk.category, chunk.retrieved_at) for chunk in first] == [
        (chunk.chunk_id, chunk.text, chunk.section, chunk.source_id, chunk.title,
         chunk.organization, chunk.url, chunk.topic, chunk.category, chunk.retrieved_at) for chunk in second
    ]


def test_normalization_is_idempotent_and_preserves_chunking_boundaries():
    raw = "\r\n## Section  \r\nText with space   \r\n\r\n"
    assert clean_document_text(raw) == "## Section\nText with space"
    documents = clean_documents(load_source_documents())
    assert documents_to_chunks(documents) == build_chunks()


def test_frozen_u_step_one_and_step_two_behavior_remains_available(tmp_path):
    class DeterministicBackend:
        def embed(self, documents):
            for document in documents:
                yield np.asarray([len(document), 1.0], dtype=np.float32)

    assert len(load_sources()) == 7
    assert len(build_chunks()) == 14
    embedder = FastEmbedEmbedder(backend=DeterministicBackend())
    metadata = build_index(embedder=embedder, index_dir=tmp_path)
    retriever = VectorRetriever.load(index_dir=tmp_path, embedder=embedder)
    assert metadata.indexed_chunk_count == 14
    assert len(retriever.retrieve("document processing", top_k=2)) == 2
