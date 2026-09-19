from spectraderm.rag.llm import DeterministicMockLLM
from spectraderm.rag.rag_pipeline import RAGPipeline, construct_retrieval_query
from spectraderm.rag.retriever import RetrievalResult


def result(chunk_id: str, source_id: str, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id, source_id=source_id, text=text, score=0.75,
        title="Source title", organization="Source organization",
        url="https://example.test/source", topic="appearance context",
    )


class FakeRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.results[:top_k]


def test_retrieval_is_called_and_top_k_is_respected():
    retriever = FakeRetriever([result("a:chunk-0001", "a", "Evidence A"), result("b:chunk-0001", "b", "Evidence B")])
    pipeline = RAGPipeline(retriever, DeterministicMockLLM())
    output = pipeline.run("A model-derived appearance change.", top_k=1)
    assert retriever.calls == [(output.query, 1)]
    assert len(output.retrieved_evidence) == 1


def test_chunk_ids_and_source_metadata_are_preserved_and_prompt_contains_evidence():
    provider = DeterministicMockLLM("Grounded mock explanation.")
    original = result("source-a:chunk-0002", "source-a", "Exact retrieved evidence text.")
    output = RAGPipeline(FakeRetriever([original]), provider).run("Existing model output")
    evidence = output.retrieved_evidence[0]
    assert evidence.chunk_id == original.chunk_id
    assert evidence.text == original.text
    assert evidence.source.source_id == original.source_id
    assert evidence.source.url == original.url
    assert output.source_metadata == (evidence.source,)
    assert "Exact retrieved evidence text." in provider.prompts[0]
    assert "source-a:chunk-0002" in provider.prompts[0]


def test_mock_llm_and_repeated_execution_are_deterministic():
    retriever = FakeRetriever([result("a:chunk-0001", "a", "Evidence A")])
    pipeline = RAGPipeline(retriever, DeterministicMockLLM("Stable response."))
    assert pipeline.run("same finding") == pipeline.run("same finding")


def test_empty_finding_is_safe_and_does_not_call_retriever_or_llm():
    retriever = FakeRetriever([result("a:chunk-0001", "a", "Evidence A")])
    provider = DeterministicMockLLM()
    output = RAGPipeline(retriever, provider).run("   ")
    assert output.query == ""
    assert output.retrieved_evidence == ()
    assert not retriever.calls
    assert not provider.prompts
    assert "No retrieved medical evidence" in output.explanation


def test_no_retrieved_evidence_is_safe_and_does_not_call_llm():
    retriever = FakeRetriever([])
    provider = DeterministicMockLLM()
    output = RAGPipeline(retriever, provider).run("Existing model finding")
    assert output.retrieved_evidence == ()
    assert not provider.prompts
    assert output.safety.no_evidence_message


def test_pipeline_itself_does_not_add_medical_claims_or_reinterpret_findings():
    finding = "Estimated spectral reconstruction changed in an existing model output."
    query = construct_retrieval_query(finding)
    assert finding in query
    assert "not a diagnosis" in query
    assert "biomarker" not in query.lower()
    assert "disease probability" not in query.lower()
