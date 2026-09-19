from dataclasses import FrozenInstanceError

import pytest

from spectraderm.catalog.otc_catalog import OTC_CATEGORY_IDS, OTCCategory, get_categories_for_pattern, get_category, has_category, list_categories


def ids(pattern): return [item.category_id for item in get_categories_for_pattern(pattern)]


def test_all_controlled_categories_exist():
    assert set(OTC_CATEGORY_IDS) == {"pigment_correctors", "topical_antioxidants", "aha_exfoliants", "broad_spectrum_sunscreen", "barrier_repair_moisturizers", "soothing_topicals", "low_potency_topical_corticosteroid", "steroid_free_anti_itch", "topical_retinoid", "bha_comedolytic", "antimicrobial_acne_care", "keratolytic", "fragrance_free_moisturizer", "gentle_cleanser"}


def test_category_ids_are_unique(): assert len(OTC_CATEGORY_IDS) == len(set(OTC_CATEGORY_IDS))
def test_listing_is_structured_and_stable(): assert list_categories() == list_categories() and all(isinstance(item, OTCCategory) for item in list_categories())
def test_category_retrieval_and_has_category_work(): assert get_category("gentle_cleanser").category_name == "Gentle cleanser" and has_category("gentle_cleanser")
def test_unsupported_category_is_clear(): assert get_category("unknown_category") is None and has_category("unknown_category") is False
def test_pigmentation_mapping_is_exact(): assert ids("pigmentation") == ["pigment_correctors", "topical_antioxidants", "aha_exfoliants", "broad_spectrum_sunscreen"]
def test_redness_mapping_is_exact(): assert ids("redness_irritation") == ["barrier_repair_moisturizers", "soothing_topicals", "low_potency_topical_corticosteroid", "steroid_free_anti_itch", "broad_spectrum_sunscreen"]
def test_acne_like_texture_mapping_is_exact(): assert ids("acne_like_texture") == ["topical_retinoid", "bha_comedolytic", "antimicrobial_acne_care", "keratolytic", "gentle_cleanser"]
def test_dryness_mapping_is_exact(): assert ids("dryness_barrier") == ["barrier_repair_moisturizers", "fragrance_free_moisturizer", "gentle_cleanser"]
def test_unknown_has_no_targeted_categories(): assert get_categories_for_pattern("unknown") == ()
def test_unsupported_pattern_is_clear():
    with pytest.raises(ValueError): get_categories_for_pattern("disease")
def test_non_string_inputs_are_handled_explicitly():
    with pytest.raises(TypeError): get_category(None)
    assert has_category(None) is False
def test_no_commercial_fields_or_brand_information_exist():
    fields = set(OTCCategory.__dataclass_fields__); text = str(list_categories()).lower()
    assert not fields.intersection({"brand", "partner", "price", "affiliate_url", "shopping_url"})
    assert not any(term in text for term in ("http", "affiliate", "$"))
def test_no_user_scan_or_location_data_exist():
    fields = set(OTCCategory.__dataclass_fields__)
    assert not fields.intersection({"user_id", "scan_id", "latitude", "longitude", "location"})
def test_no_prescription_plan_or_diagnosis_fields_exist():
    fields = set(OTCCategory.__dataclass_fields__)
    assert not fields.intersection({"diagnosis", "probability", "prescription", "treatment_plan", "medical_risk"})
def test_entries_and_results_cannot_be_mutated_by_callers():
    entry = get_category("gentle_cleanser")
    with pytest.raises(FrozenInstanceError): entry.category_name = "Changed"
    with pytest.raises(AttributeError): list_categories().append(entry)
def test_repeated_pattern_queries_are_deterministic(): assert get_categories_for_pattern("pigmentation") == get_categories_for_pattern("pigmentation")
def test_relevant_patterns_are_controlled_vocabulary_only(): assert all(set(item.relevant_patterns).issubset({"pigmentation", "redness_irritation", "acne_like_texture", "dryness_barrier"}) for item in list_categories())
def test_jurisdiction_notes_are_present_for_regulated_categories(): assert get_category("topical_retinoid").jurisdiction_note is not None and get_category("low_potency_topical_corticosteroid").jurisdiction_note is not None
def test_catalog_text_has_no_cure_or_guarantee_claims(): assert not any(term in str(list_categories()).lower() for term in ("cure", "guarantee", "will remove", "your acne"))
