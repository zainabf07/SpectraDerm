from spectraderm.agents.vision_agent import VisionAgent, VisionAgentInput


def complete_input():
    return VisionAgentInput(
        image_quality_result={"status": "GOOD", "passed": True, "metric": 7},
        localization_result={"method": "supplied_localizer", "candidates": ["roi-1"]},
        reconstruction_result={"estimated": True, "output_bands": 31},
        spectral_features={"features": {"spectral.ratio_540_650": 1.2}},
        monitoring_change_result={"change_score": 81.0, "category": "Higher Change"},
        ml_output={"label": "evaluation-only output"},
    )


def test_complete_structured_input_preserves_outputs_and_uses_engineering_status():
    source = complete_input()
    output = VisionAgent().interpret(source)
    assert output.overall_status == "review_recommended"
    assert output.image_quality_summary.supplied_output is source.image_quality_result
    assert output.localization_summary.supplied_output is source.localization_result
    assert output.spectral_summary.supplied_output is source.reconstruction_result
    assert set(output.available_evidence) == {
        "image_quality", "localization", "reconstruction", "spectral_features", "monitoring_change", "ml_output"
    }


def test_image_quality_only_and_missing_quality_are_explicitly_represented():
    quality_only = VisionAgent().interpret(VisionAgentInput(image_quality_result={"status": "REJECT", "passed": False}))
    missing_quality = VisionAgent().interpret(VisionAgentInput(localization_result={"method": "supplied"}))
    assert quality_only.overall_status == "insufficient_quality"
    assert quality_only.localization_summary.available is False
    assert missing_quality.image_quality_summary.available is False
    assert "image_quality output was not supplied." in missing_quality.limitations


def test_reconstruction_and_features_are_available_but_not_described_as_measurement():
    output = VisionAgent().interpret(VisionAgentInput(
        reconstruction_result={"estimated": True, "output_bands": 31}, spectral_features={"features": {"x": 1.0}}
    ))
    assert output.spectral_summary.available
    assert output.feature_summary.available
    assert "not measured spectroscopy" in output.spectral_summary.summary
    assert "biomarker" in output.feature_summary.summary.lower()


def test_monitoring_status_is_used_without_recalculating_score_or_probability():
    output = VisionAgent().interpret(VisionAgentInput(
        monitoring_change_result={"change_score": 99.9, "category": "Stable"}
    ))
    assert output.overall_status == "no_actionable_change"
    assert "99.9" not in output.change_summary.summary
    assert "disease probability" in output.change_summary.summary
    assert "probability" not in output.finding_summary.lower()


def test_optional_ml_output_is_reported_only_when_supplied():
    supplied = VisionAgent().interpret(VisionAgentInput(ml_output={"label": "external model output"}))
    absent = VisionAgent().interpret(VisionAgentInput())
    assert supplied.ml_summary.available
    assert supplied.ml_summary.supplied_output == {"label": "external model output"}
    assert "not converted into a diagnosis" in supplied.ml_summary.summary
    assert absent.ml_summary.available is False


def test_repeated_execution_is_deterministic_and_no_values_are_fabricated():
    source = complete_input()
    agent = VisionAgent()
    first = agent.interpret(source)
    second = agent.interpret(source)
    assert first == second
    assert first.change_summary.supplied_output == source.monitoring_change_result
    assert "81.0" not in first.finding_summary


def test_no_op_model_or_raw_image_is_required_and_safety_is_present():
    output = VisionAgent().interpret(VisionAgentInput(image_quality_result={"status": "GOOD", "passed": True}))
    assert output.overall_status == "no_actionable_change"
    assert "raw image" in output.limitations[-2]
    assert "not a diagnosis" in output.safety_message
    assert "not disease probabilities" in output.safety_message
