from spectraderm.agents.evidence_agent import EvidenceAgent, EvidenceAgentInput, construct_evidence_request
from spectraderm.rag.rag_pipeline import RAGResult, RetrievedEvidence, SafetyMetadata, SourceMetadata


def evidence():
    return RetrievedEvidence(
        chunk_id="source-a:chunk-0001", text="Exact retrieved evidence.", score=0.8,
        source=SourceMetadata("source-a", "Source A", "Organization", "https://example.test/a", "context"),
    )


class FakeModuleW:
    def __init__(self, items=(evidence(),), explanation="Grounded explanation."):
        self.items = tuple(items)
        self.explanation = explanation
        self.calls = []

    def run(self, model_finding, top_k=3):
        self.calls.append((model_finding, top_k))
        return RAGResult(
            model_finding=model_finding, query=f"W query: {model_finding}", retrieved_evidence=self.items[:top_k],
            explanation=self.explanation, safety=SafetyMetadata(True, True, True, True, True, not bool(self.items)),
        )


def test_valid_finding_is_passed_to_module_w_and_retrieves_evidence():
    pipeline = FakeModuleW()
    output = EvidenceAgent(pipeline).interpret(EvidenceAgentInput(structured_finding="Model-derived feature change.", top_k=1))
    assert pipeline.calls == [("Model-derived feature change.", 1)]
    assert output.grounding_status == "evidence_found"
    assert output.evidence_count == 1


def test_monitoring_context_is_preserved_and_only_uses_supplied_engineering_labels():
    monitoring = {"trend": "increasing_change", "current_status": "changed", "current_change_score": 90}
    pipeline = FakeModuleW()
    output = EvidenceAgent(pipeline).interpret(EvidenceAgentInput(structured_finding="Existing model finding", monitoring_result=monitoring))
    sent, _ = pipeline.calls[0]
    assert output.monitoring_context is monitoring
    assert "Model-derived monitoring trend: increasing_change." in sent
    assert "90" not in sent
    assert "disease" not in sent.lower()


def test_explicit_query_has_precedence_and_top_k_is_forwarded():
    pipeline = FakeModuleW(items=(evidence(), evidence()))
    output = EvidenceAgent(pipeline).interpret(EvidenceAgentInput(
        structured_finding="ignored finding", query="Explicit model-derived request", top_k=2
    ))
    assert pipeline.calls == [("Explicit model-derived request", 2)]
    assert output.evidence_count == 2


def test_evidence_chunk_ids_source_metadata_and_explanation_remain_separate():
    original = evidence()
    output = EvidenceAgent(FakeModuleW((original,), "Separate explanation.")).interpret(EvidenceAgentInput(query="request"))
    assert output.retrieved_evidence == (original,)
    assert output.retrieved_evidence[0].chunk_id == "source-a:chunk-0001"
    assert output.source_metadata == (original.source,)
    assert output.explanation == "Separate explanation."
    assert output.explanation != output.retrieved_evidence[0].text


def test_no_query_and_empty_finding_do_not_call_module_w():
    pipeline = FakeModuleW()
    output = EvidenceAgent(pipeline).interpret(EvidenceAgentInput(structured_finding="   "))
    assert output.grounding_status == "no_query"
    assert output.retrieved_evidence == ()
    assert not pipeline.calls


def test_no_evidence_and_unavailable_explanation_are_explicit():
    no_evidence = EvidenceAgent(FakeModuleW((), "unused")).interpret(EvidenceAgentInput(query="request"))
    no_explanation = EvidenceAgent(FakeModuleW((evidence(),), " ")).interpret(EvidenceAgentInput(query="request"))
    assert no_evidence.grounding_status == "insufficient_evidence"
    assert no_evidence.explanation == "unused"
    assert no_explanation.grounding_status == "explanation_unavailable"
    assert no_explanation.explanation is None


def test_repeated_execution_is_deterministic_and_agent_has_no_probability_or_measurement_claim():
    pipeline = FakeModuleW()
    agent = EvidenceAgent(pipeline)
    source = EvidenceAgentInput(structured_finding="Estimated reconstruction feature output")
    assert agent.interpret(source) == agent.interpret(source)
    safety = agent.interpret(source).safety_message.lower()
    assert "disease probabilities" in safety
    assert "not measured spectroscopy" in safety


def test_query_constructor_does_not_fabricate_medical_evidence():
    request = construct_evidence_request(EvidenceAgentInput(
        structured_finding="Model output", additional_context="Non-sensitive capture context"
    ))
    assert request == "Model output\nNon-sensitive capture context"
    assert "diagnos" not in request.lower()
