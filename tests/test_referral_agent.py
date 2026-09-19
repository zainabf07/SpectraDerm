from spectraderm.agents.referral_agent import DermatologistOption, ReferralAgent, ReferralAgentInput


class FakeProvider:
    def __init__(self, results=(), error=False):
        self.results, self.error, self.calls = results, error, []

    def find_dermatologists(self, location, radius_km, specialty="dermatology"):
        self.calls.append((dict(location), radius_km, specialty))
        if self.error:
            raise RuntimeError("synthetic provider error")
        return self.results


def run(provider, decision=True, location={"city": "Example City"}):
    return ReferralAgent(provider).refer(ReferralAgentInput({"professional_assessment_recommended": decision}, location))


def test_referral_required_searches_with_broad_dermatology_specialty():
    provider = FakeProvider((DermatologistOption(name="A", specialty="Dermatology"),))
    output = run(provider)
    assert output.status == "referral_options_available"
    assert provider.calls[0][2] == "dermatology"


def test_not_required_and_missing_decision_do_not_search():
    provider = FakeProvider()
    assert run(provider, False).status == "not_required"
    missing = ReferralAgent(provider).refer(ReferralAgentInput(safety_result={"other": True}, location={"city": "X"}))
    assert missing.status == "not_required" and missing.metadata["decision_available"] is False
    assert provider.calls == []


def test_missing_location_requires_explicit_permission_or_manual_input():
    provider = FakeProvider()
    output = run(provider, location=None)
    assert output.status == "location_required" and provider.calls == []
    assert "manual" in output.reason.lower()


def test_manual_and_coordinate_locations_are_accepted():
    city = FakeProvider()
    coordinates = FakeProvider()
    assert run(city, location={"city": "Example City"}).location_used == {"city": "Example City"}
    assert run(coordinates, location={"latitude": 25.2, "longitude": 55.3}).location_used == {"latitude": 25.2, "longitude": 55.3}


def test_deterministic_ranking_prioritizes_specialty_then_distance_then_hours():
    provider = FakeProvider((
        DermatologistOption(name="Mismatch", specialty="General clinic", distance_km=1),
        DermatologistOption(name="Far skin", specialty="Dermatology", distance_km=8),
        DermatologistOption(name="Near skin", specialty="dermatology", distance_km=2),
    ))
    output = run(provider)
    assert [item.name for item in output.options] == ["Near skin", "Far skin", "Mismatch"]
    assert output.options[0].specialty == "dermatology"


def test_missing_provider_fields_are_not_invented():
    output = run(FakeProvider(({"name": "Sparse provider", "source": "synthetic"},)))
    option = output.options[0]
    assert option.address is option.distance_km is option.opening_hours is option.phone is option.website is None


def test_empty_results_and_provider_failure_are_safe():
    assert run(FakeProvider()).status == "no_results"
    assert run(FakeProvider(error=True)).status == "provider_error"


def test_repeated_inputs_are_deterministic_and_inputs_are_not_mutated():
    location = {"city": "Example City", "extra": "do not retain"}
    safety = {"professional_assessment_recommended": True}
    provider = FakeProvider((DermatologistOption(name="A", specialty="Dermatology", distance_km=2),))
    agent = ReferralAgent(provider)
    source = ReferralAgentInput(safety, location)
    assert agent.refer(source) == agent.refer(source)
    assert location == {"city": "Example City", "extra": "do not retain"}
    assert safety == {"professional_assessment_recommended": True}


def test_output_is_neutral_and_has_no_unneeded_dependencies():
    output = run(FakeProvider((DermatologistOption(name="Neutral", specialty="Dermatology"),)))
    text = " ".join((output.reason, output.safety_message)).lower()
    assert "not a diagnosis" in text
    assert not any(word in text for word in ("probability", "treatment", "medication", "melanoma", "cancer"))
    assert not hasattr(output, "diagnosis") and not hasattr(output, "image") and not hasattr(output, "model")


def test_location_alias_is_accepted_without_accessing_a_device():
    provider = FakeProvider()
    output = run(provider, location={"location": "Example District"})
    assert output.location_used == {"location": "Example District"}
    assert provider.calls[0][0] == {"location": "Example District"}


def test_partial_coordinate_location_is_not_used():
    provider = FakeProvider()
    output = run(provider, location={"latitude": 25.2})
    assert output.status == "location_required"
    assert provider.calls == []


def test_opening_hours_breaks_a_same_distance_and_specialty_tie():
    output = run(FakeProvider((
        DermatologistOption(name="No hours", specialty="Dermatology", distance_km=2),
        DermatologistOption(name="Hours", specialty="Dermatology", distance_km=2, opening_hours="09:00-17:00"),
    )))
    assert [option.name for option in output.options] == ["Hours", "No hours"]


def test_missing_distance_is_ranked_after_returned_distance():
    output = run(FakeProvider((
        DermatologistOption(name="Unknown", specialty="Dermatology"),
        DermatologistOption(name="Known", specialty="Dermatology", distance_km=4),
    )))
    assert [option.name for option in output.options] == ["Known", "Unknown"]


def test_provider_mapping_is_normalized_without_added_data():
    output = run(FakeProvider(({"name": "Mapped", "specialty": "Dermatology", "distance_km": 3},)))
    assert output.options == (DermatologistOption(name="Mapped", specialty="Dermatology", distance_km=3.0),)


def test_radius_is_forwarded_unchanged():
    provider = FakeProvider()
    ReferralAgent(provider).refer(ReferralAgentInput({"professional_assessment_recommended": True}, {"city": "X"}, 12.5))
    assert provider.calls[0][1] == 12.5


def test_false_like_decision_is_not_an_affirmative_referral_gate():
    provider = FakeProvider()
    output = ReferralAgent(provider).refer(ReferralAgentInput({"professional_assessment_recommended": 1}, {"city": "X"}))
    assert output.status == "not_required" and provider.calls == []


def test_no_results_preserves_location_but_does_not_create_options():
    output = run(FakeProvider(), location={"city": "Example City"})
    assert output.location_used == {"city": "Example City"}
    assert output.options == () and output.metadata["provider_count"] == 0


def test_provider_error_does_not_expose_exception_details():
    output = run(FakeProvider(error=True))
    assert output.options == ()
    assert "synthetic provider error" not in output.reason.lower()


def test_metadata_records_the_fixed_broad_specialty_request():
    output = run(FakeProvider())
    assert output.metadata["specialty_requested"] == "dermatology"
    assert "acne" not in output.metadata["specialty_requested"]


def test_module_source_has_no_google_or_credentials_dependency():
    import inspect
    import spectraderm.agents.referral_agent as referral_module

    source = inspect.getsource(referral_module).lower()
    assert "import google" not in source and "from google" not in source
    assert "import requests" not in source and "api_key" not in source


def test_module_accepts_no_raw_image_spectral_or_model_input():
    fields = ReferralAgentInput.__dataclass_fields__
    assert set(fields) == {"safety_result", "location", "radius_km"}
