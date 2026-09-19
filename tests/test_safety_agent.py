from spectraderm.agents.safety_agent import SafetyAgent, SafetyAgentInput
from spectraderm.rag.rag_pipeline import RetrievedEvidence, SourceMetadata


def evidence(text="Retrieved context without a referral statement."):
    return RetrievedEvidence(
        chunk_id="source-a:chunk-0001", text=text, score=0.7,
        source=SourceMetadata("source-a", "Title", "Organization", "https://example.test", "topic"),
    )


def evidence_result(items=(evidence(),), status="evidence_found", explanation="Model-derived finding is separate from retrieved context."):
    return {"retrieved_evidence": items, "grounding_status": status, "explanation": explanation}


def evaluate(**kwargs):
    return SafetyAgent().evaluate(SafetyAgentInput(**kwargs))


def test_safe_model_finding_and_evidence_grounded_explanation_are_safe_to_present():
    output = evaluate(finding_summary="Model-derived appearance feature change.", evidence_result=evidence_result())
    assert output.safety_status == "safe_to_present"
    assert output.concern_level == "low"
    assert output.blocked_claims == ()


def test_empty_or_missing_finding_and_missing_evidence_are_insufficient():
    empty = evaluate(finding_summary="", evidence_result=evidence_result())
    missing_evidence = evaluate(finding_summary="Model output", evidence_result=None)
    assert empty.safety_status == "insufficient_evidence"
    assert missing_evidence.safety_status == "insufficient_evidence"
    assert missing_evidence.professional_assessment_recommended is False


def test_z_insufficient_evidence_is_preserved_without_fabrication():
    output = evaluate(finding_summary="Model output", evidence_result=evidence_result((), "insufficient_evidence", ""))
    assert output.safety_status == "insufficient_evidence"
    assert output.evidence_used == ()
    assert any("insufficient grounding" in reason for reason in output.reasons)


def test_diagnostic_probability_progression_biomarker_and_treatment_claims_are_blocked():
    unsafe = (
        "This proves you have acne. You have a 70% chance of disease. "
        "The disease is progressing. This spectral band proves melanin biomarker. Take medication."
    )
    output = evaluate(finding_summary="Model output", evidence_result=evidence_result(), proposed_action=unsafe)
    kinds = {item.classification for item in output.claim_assessment}
    assert output.safety_status == "caution_required"
    assert output.blocked_claims == (unsafe,)
    assert "diagnostic_claim" in kinds


def test_increasing_model_change_is_not_converted_to_disease_progression():
    output = evaluate(
        finding_summary="Model-derived change score increased.",
        monitoring_result={"trend": "increasing_change", "current_change_score": 80},
        evidence_result=evidence_result(),
    )
    assert output.safety_status == "safe_to_present"
    assert "disease progression" not in " ".join(output.allowed_claims).lower()
    assert output.professional_assessment_recommended is False


def test_estimated_spectrum_and_biomarker_boundaries_and_professional_context():
    safe = evaluate(finding_summary="Estimated spectral reconstruction changed.", evidence_result=evidence_result())
    referral = evaluate(
        finding_summary="Model output", evidence_result=evidence_result((evidence("The supplied evidence says consider professional assessment."),))
    )
    assert safe.safety_status == "safe_to_present"
    assert "measured spectroscopy" in safe.safety_message
    assert referral.safety_status == "professional_assessment_consideration"
    assert referral.professional_assessment_recommended is True


def test_evidence_provenance_is_preserved_and_inputs_are_not_mutated():
    item = evidence()
    source = evidence_result((item,))
    output = evaluate(finding_summary="Model output", evidence_result=source)
    provenance = output.evidence_used[0]
    assert (provenance.chunk_id, provenance.source_id, provenance.title, provenance.url, provenance.text) == (
        item.chunk_id, item.source.source_id, item.source.title, item.source.url, item.text
    )
    assert source["retrieved_evidence"] == (item,)


def test_repeated_execution_missing_agent_data_and_safety_message_are_deterministic():
    input_value = SafetyAgentInput(finding_summary="Model output", evidence_result=evidence_result())
    agent = SafetyAgent()
    assert agent.evaluate(input_value) == agent.evaluate(input_value)
    missing = agent.evaluate(SafetyAgentInput())
    assert missing.input_summary["monitoring_available"] is False
    assert "not a diagnostic system" in missing.safety_message
    assert not hasattr(missing, "diagnosis")
    assert not hasattr(missing, "disease_probability")
