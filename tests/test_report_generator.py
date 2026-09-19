from spectraderm.reporting.report_generator import ReportGenerator, ReportSection


def report(**kwargs): return ReportGenerator().generate_report({"scan_id": "scan-1", "user_id": "usr-1", "timestamp": "synthetic", "latitude": 1}, **kwargs)
def values(section): return [item.value for item in section.items]


VISION = {"finding_summary": "Model-derived finding: synthetic appearance feature."}
MONITORING = {"current_change_score": 72, "trend": "stable", "summary": "Supplied model-derived change context."}
EVIDENCE = {"explanation": "Supplied external evidence context.", "retrieved_evidence": ({"text": "Source text", "source": {"source_id": "s1", "title": "Title", "url": "https://example.test"}},)}
SAFETY_FALSE = {"professional_assessment_recommended": False, "safety_status": "safe"}
SAFETY_TRUE = {"professional_assessment_recommended": True, "safety_status": "professional_assessment_consideration"}
PRODUCT = {"recommendations": ({"category_id": "gentle_cleanser", "category_name": "Gentle cleanser", "neutral_description": "General category."},)}
REFERRAL = {"options": ({"name": "Supplied Clinic", "address": "1 Demo Road", "distance_km": 2.0, "phone": "123", "source": "synthetic"},)}


def test_complete_report_has_all_structured_sections():
    output = report(vision=VISION, monitoring=MONITORING, evidence=EVIDENCE, safety=SAFETY_FALSE, spectral={"summary": "Supplied reconstruction metadata."}, ml={"status": "supplied"}, product=PRODUCT)
    assert len(output.sections) == 11 and all(isinstance(item, ReportSection) for item in output.sections)


def test_scan_information_is_whitelisted_and_has_no_location():
    output = report(safety=SAFETY_FALSE)
    assert [item.label for item in output.scan_information.items] == ["scan_id", "user_id", "timestamp"]


def test_vision_finding_and_model_change_are_preserved_with_safe_terminology():
    output = report(vision=VISION, monitoring=MONITORING, safety=SAFETY_FALSE)
    assert "Model-derived finding" in values(output.visual_region_findings)[0]
    assert values(output.model_derived_change)[0] == "model-derived change" and any(item.value == 72 for item in output.model_derived_change.items)


def test_spectral_section_uses_ai_estimated_wording():
    output = report(spectral={"summary": "Supplied reconstruction metadata."}, safety=SAFETY_FALSE)
    assert values(output.spectral_analysis)[0] == "AI-estimated spectral representation"


def test_evidence_and_source_attribution_are_preserved():
    output = report(evidence=EVIDENCE, safety=SAFETY_FALSE)
    assert output.evidence_explanation.status == "available"
    assert ("title", "Title") in output.evidence_explanation.items[1].value


def test_missing_evidence_has_explicit_no_fabrication_notice():
    output = report(safety=SAFETY_FALSE)
    assert output.evidence_explanation.status == "unavailable" and values(output.evidence_explanation) == ["Evidence was not available."]


def test_safety_assessment_is_included():
    output = report(safety=SAFETY_TRUE)
    assert output.safety_assessment.status == "available" and any(item.value is True for item in output.safety_assessment.items)


def test_referral_only_is_included_when_professional_assessment_is_recommended():
    output = report(safety=SAFETY_TRUE, referral=REFERRAL, product=PRODUCT)
    assert output.referral_options.status == "available" and output.otc_categories.status == "not_applicable"
    assert ("name", "Supplied Clinic") in output.referral_options.items[0].value


def test_missing_referral_does_not_create_provider():
    output = report(safety=SAFETY_TRUE)
    assert output.referral_options.status == "unavailable" and output.referral_options.items == ()


def test_product_only_is_included_when_safety_allows_it():
    output = report(safety=SAFETY_FALSE, product=PRODUCT, referral=REFERRAL)
    assert output.otc_categories.status == "available" and output.referral_options.status == "not_applicable"
    assert ("category_id", "gentle_cleanser") in output.otc_categories.items[0].value


def test_missing_product_does_not_create_category():
    output = report(safety=SAFETY_FALSE)
    assert output.otc_categories.status == "unavailable" and output.otc_categories.items == ()


def test_missing_or_invalid_safety_blocks_downstream_sections():
    for safety in (None, {"professional_assessment_recommended": None}):
        output = report(safety=safety, product=PRODUCT, referral=REFERRAL)
        assert output.recommended_next_action.status == "blocked"
        assert output.otc_categories.status == output.referral_options.status == "not_applicable"


def test_no_diagnosis_probability_or_treatment_claim_is_generated():
    output = report(safety=SAFETY_FALSE)
    text = str(output).lower()
    assert not any(term in text for term in ("diagnosis", "disease probability", "treatment plan", "this proves", "this confirms"))


def test_no_measured_spectroscopy_or_physical_change_claim_is_generated():
    output = report(monitoring=MONITORING, spectral={"summary": "synthetic"}, safety=SAFETY_FALSE)
    text = str(output).lower()
    assert "measured spectrum" not in text and "physical skin" not in text and "72% chance" not in text


def test_no_evidence_provider_or_product_is_invented():
    output = report(safety=SAFETY_FALSE)
    assert output.evidence_explanation.items[0].value == "Evidence was not available."
    assert output.referral_options.items == () and output.otc_categories.items == ()


def test_results_are_deterministic_and_inputs_are_not_mutated():
    source = {"finding_summary": "Model-derived finding: unchanged."}
    first, second = report(vision=source, safety=SAFETY_FALSE), report(vision=source, safety=SAFETY_FALSE)
    assert first == second and source == {"finding_summary": "Model-derived finding: unchanged."}


def test_referral_preserves_only_supplied_provider_fields():
    output = report(safety=SAFETY_TRUE, referral={"options": ({"name": "Sparse"},)})
    assert output.referral_options.items[0].value == (("name", "Sparse"),)


def test_product_preserves_only_supplied_category_fields():
    output = report(safety=SAFETY_FALSE, product={"recommendations": ({"category_name": "General"},)})
    assert output.otc_categories.items[0].value == (("category_name", "General"),)


def test_missing_components_use_explicit_states_not_zero_values():
    output = report(safety=SAFETY_FALSE)
    assert output.visual_region_findings.status == "unavailable" and output.model_derived_change.status == "not_provided"


def test_report_has_no_raw_images_spectral_cubes_or_location_history_fields():
    output = report(safety=SAFETY_FALSE)
    assert not hasattr(output, "raw_image") and not hasattr(output, "spectral_cube") and not hasattr(output, "location_history")
