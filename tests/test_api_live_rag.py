from spectraderm.api.rag_adapter import RetrievalOnlyRAGPipeline


def test_live_retrieval_preserves_existing_source_attribution():
    result = RetrievalOnlyRAGPipeline().run("Model-derived observation: image quality output available.")

    assert result.retrieved_evidence
    assert all(item.source.title and item.source.organization and item.source.url for item in result.retrieved_evidence)
    # Without a language model the explanation is built only from retrieved,
    # attributed source text, with curator notes removed.
    assert result.explanation.startswith("What was observed:")
    assert "Why it can matter:" in result.explanation
    assert "retained" not in result.explanation and "SpectraDerm" not in result.explanation
