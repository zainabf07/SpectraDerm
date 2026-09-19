from spectraderm.agents.product_agent import CATALOG, ProductAgent, ProductAgentInput


def run(pattern, safety=False, monitoring=None):
    return ProductAgent().recommend(ProductAgentInput(
        detected_pattern=pattern, safety_result={"professional_assessment_recommended": safety},
        monitoring_result=monitoring,
    ))


def ids(result):
    return [item.category_id for item in result.recommendations]


def test_supported_patterns_get_distinct_relevant_category_lists():
    pigmentation = run("pigmentation")
    redness = run("redness_irritation")
    acne = run("acne_like_texture")
    dryness = run("dryness_barrier")
    assert ids(pigmentation) == ["pigment_support_skincare", "topical_antioxidant_skincare", "gentle_chemical_exfoliation", "broad_spectrum_sunscreen", "gentle_cleanser", "moisturizer"]
    assert ids(redness) == ["fragrance_free_moisturizer", "soothing_skincare", "gentle_cleanser", "broad_spectrum_sunscreen"]
    assert ids(acne) == ["gentle_cleanser", "non_comedogenic_moisturizer", "salicylic_acid_bha_skincare", "benzoyl_peroxide_skincare", "broad_spectrum_sunscreen"]
    assert ids(dryness) == ["gentle_cleanser", "fragrance_free_moisturizer", "moisturizer"]
    assert len({tuple(ids(item)) for item in (pigmentation, redness, acne, dryness)}) == 4


def test_unknown_pattern_has_no_targeted_recommendation():
    output = run("unknown")
    assert output.status == "insufficient_context"
    assert output.recommendations == ()


def test_reason_is_pattern_aware_and_persistent_change_without_referral_is_allowed():
    monitoring = {"trend": "increasing_change", "current_change_score": 90}
    output = run("redness/irritation", monitoring=monitoring)
    assert output.status == "recommendations_available"
    assert all("redness/irritation" in item.reason for item in output.recommendations)
    assert output.monitoring_context is monitoring


def test_aa_professional_assessment_gate_returns_no_products():
    output = run("pigmentation", safety=True, monitoring={"trend": "increasing_change"})
    assert output.status == "referral_preferred"
    assert output.recommendations == ()
    assert output.professional_assessment_recommended is True


def test_no_diagnosis_probability_treatment_brands_or_prescriptions_are_generated():
    output = run("acne_like_texture")
    text = " ".join(item.category_name + " " + item.neutral_description + " " + item.reason for item in output.recommendations).lower()
    assert "diagnosis" in output.safety_message.lower()
    assert "diagnoses" in output.safety_message.lower()
    assert "prescriptions" in output.safety_message.lower()
    assert "probability" not in text
    assert "prescription" not in text
    assert "treats" not in text
    assert not hasattr(output, "diagnosis")
    assert not hasattr(output, "disease_probability")
    assert all("http" not in item.neutral_description.lower() for item in CATALOG.values())
    assert all("corticosteroid" not in item.neutral_description.lower() for item in CATALOG.values())


def test_inputs_are_preserved_and_execution_is_deterministic():
    safety = {"professional_assessment_recommended": False}
    monitoring = {"trend": "stable", "current_change_score": 5.0}
    source = ProductAgentInput(detected_pattern="dryness_barrier", safety_result=safety, monitoring_result=monitoring)
    agent = ProductAgent()
    assert agent.recommend(source) == agent.recommend(source)
    assert safety == {"professional_assessment_recommended": False}
    assert monitoring == {"trend": "stable", "current_change_score": 5.0}
