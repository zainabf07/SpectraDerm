from dataclasses import dataclass

from spectraderm.agents.orchestrator_agent import OrchestratorAgent, OrchestratorInput
from spectraderm.agents.product_agent import ProductAgentInput


@dataclass(frozen=True)
class SafetyOutput:
    professional_assessment_recommended: bool


class FakeAgent:
    def __init__(self, method, result=None, error=False, trace=None, label="agent"):
        self.method, self.result, self.error = method, result, error
        self.calls, self.trace, self.label = [], trace if trace is not None else [], label

    def _call(self, value):
        self.calls.append(value)
        self.trace.append(self.label)
        if self.error:
            raise RuntimeError(self.label)
        return self.result

    def interpret(self, value): return self._call(value)
    def evaluate(self, value): return self._call(value)
    def recommend(self, value): return self._call(value)
    def refer(self, value): return self._call(value)


def make_agents(decision=False, failures=()):
    trace = []
    return trace, (
        FakeAgent("interpret", {"vision": "structured"}, "vision" in failures, trace, "vision"),
        FakeAgent("interpret", {"monitoring": "structured"}, "monitoring" in failures, trace, "monitoring"),
        FakeAgent("interpret", {"evidence": "structured"}, "evidence" in failures, trace, "evidence"),
        FakeAgent("evaluate", SafetyOutput(decision), "safety" in failures, trace, "safety"),
        FakeAgent("recommend", {"product": "synthetic"}, "product" in failures, trace, "product"),
        FakeAgent("refer", {"referral": "synthetic"}, "referral" in failures, trace, "referral"),
    )


def execute(decision=False, failures=(), source=None):
    trace, agents = make_agents(decision, failures)
    result = OrchestratorAgent(*agents).run(source or OrchestratorInput(vision_input={"v": 1}, monitoring_input={"m": 1}))
    return result, trace, agents


def test_complete_product_workflow_succeeds_in_order():
    result, trace, _ = execute(False)
    assert result.status == "completed" and result.recommended_path == "product"
    assert trace == ["vision", "monitoring", "evidence", "safety", "product"]


def test_structured_outputs_are_passed_to_evidence_and_safety():
    result, _, agents = execute(False)
    evidence_input, safety_input = agents[2].calls[0], agents[3].calls[0]
    assert evidence_input.structured_finding is result.vision_result
    assert evidence_input.monitoring_result is result.monitoring_result
    assert safety_input.evidence_result is result.evidence_result


def test_referral_decision_calls_only_referral():
    result, trace, agents = execute(True)
    assert result.recommended_path == "referral" and result.product_result is None
    assert len(agents[5].calls) == 1 and agents[4].calls == [] and trace[-1] == "referral"


def test_product_decision_calls_only_product_when_supported():
    result, _, agents = execute(False)
    assert result.referral_result is None and len(agents[4].calls) == 1 and agents[5].calls == []


def test_safety_decision_is_preserved_without_modification():
    result, _, agents = execute(True)
    assert result.safety_result is agents[3].result
    assert result.referral_result == {"referral": "synthetic"}


def test_missing_safety_result_blocks_both_downstream_agents():
    result, _, agents = execute(False, ("safety",))
    assert result.status == "blocked" and result.recommended_path == "insufficient_information"
    assert agents[4].calls == [] and agents[5].calls == []


def test_invalid_safety_decision_blocks_both_downstream_agents():
    trace, agents = make_agents(False)
    agents[3].result = {"professional_assessment_recommended": None}
    result = OrchestratorAgent(*agents).run(OrchestratorInput(vision_input={}))
    assert result.status == "blocked" and agents[4].calls == [] and agents[5].calls == []


def test_vision_failure_is_explicit_and_preserves_later_results():
    result, _, _ = execute(False, ("vision",), OrchestratorInput(monitoring_input={}, product_input=ProductAgentInput()))
    assert "vision_failed:RuntimeError" in result.errors and result.monitoring_result is not None


def test_monitoring_failure_is_explicit_and_preserves_vision_result():
    result, _, _ = execute(False, ("monitoring",))
    assert "monitoring_failed:RuntimeError" in result.errors and result.vision_result is not None


def test_evidence_failure_is_explicit_and_preserves_previous_results():
    result, _, _ = execute(False, ("evidence",))
    assert "evidence_failed:RuntimeError" in result.errors and result.vision_result is not None


def test_product_failure_preserves_upstream_results():
    result, _, _ = execute(False, ("product",))
    assert result.status == "partial" and result.product_result is None and result.safety_result is not None


def test_referral_failure_preserves_upstream_results():
    result, _, _ = execute(True, ("referral",))
    assert result.status == "partial" and result.referral_result is None and result.safety_result is not None


def test_no_missing_value_is_replaced_with_a_fabricated_value():
    result, _, _ = execute(False, ("evidence",))
    assert result.evidence_result is None
    assert not hasattr(result, "diagnosis") and not hasattr(result, "disease_probability")


def test_no_diagnosis_or_treatment_is_generated_by_ad():
    result, _, _ = execute(False)
    assert not hasattr(result, "diagnosis") and not hasattr(result, "treatment") and not hasattr(result, "medication")


def test_referral_receives_safety_result_and_transient_location():
    source = OrchestratorInput(vision_input={}, referral_location={"city": "Synthetic City"})
    result, _, agents = execute(True, source=source)
    referral_input = agents[5].calls[0]
    assert referral_input.safety_result is result.safety_result
    assert referral_input.location == {"city": "Synthetic City"}


def test_product_receives_original_structured_agent_outputs():
    result, _, agents = execute(False)
    product_input = agents[4].calls[0]
    assert product_input.vision_result is result.vision_result
    assert product_input.monitoring_result is result.monitoring_result


def test_false_safety_with_no_product_context_does_not_invent_a_path():
    result, _, agents = execute(False, source=OrchestratorInput())
    assert result.recommended_path == "insufficient_information" and agents[4].calls == []


def test_repeated_identical_mocked_inputs_are_deterministic():
    source = OrchestratorInput(vision_input={"same": True}, monitoring_input={"same": True})
    first, _, _ = execute(False, source=source)
    second, _, _ = execute(False, source=source)
    assert first == second


def test_input_is_not_mutated():
    vision, monitoring = {"v": 1}, {"m": 1}
    source = OrchestratorInput(vision_input=vision, monitoring_input=monitoring)
    execute(False, source=source)
    assert vision == {"v": 1} and monitoring == {"m": 1}


def test_no_google_mcp_or_external_service_is_called_or_required():
    result, _, agents = execute(False)
    assert result.status == "completed"
    assert all(len(agent.calls) <= 1 for agent in agents)


def test_orchestrator_input_has_no_raw_image_or_spectral_cube_requirement():
    assert set(OrchestratorInput.__dataclass_fields__) == {
        "vision_input", "monitoring_input", "evidence_input", "safety_input", "product_input",
        "referral_location", "referral_radius_km",
    }
