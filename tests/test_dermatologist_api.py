from spectraderm.referral.dermatologist_api import DermatologistSearchService, GooglePlacesProvider


class FakeProvider:
    def __init__(self, results=(), error=False): self.results, self.error, self.calls = results, error, []
    def search_dermatologists(self, location, radius_meters, limit):
        self.calls.append((dict(location), radius_meters, limit))
        if self.error: raise RuntimeError("secret should not leak")
        return self.results


class FakeHttp:
    def __init__(self, response): self.response, self.calls = response, []
    def get(self, endpoint, params): self.calls.append((endpoint, dict(params))); return self.response


def service(results=(), error=False):
    provider = FakeProvider(results, error); return DermatologistSearchService(provider, "synthetic"), provider


def test_successful_manual_search_returns_normalized_provider():
    api, provider = service(({"place_id": "p1", "name": "Clinic", "formatted_address": "1 Demo St", "types": ["dermatology"], "rating": 4.5},))
    result = api.search_dermatologists({"city": "Demo City"})
    assert result.success and result.query_location_type == "manual" and result.providers[0].name == "Clinic"
    assert provider.calls == [({"city": "Demo City"}, 5000, 10)]


def test_multiple_providers_and_missing_optional_fields_are_preserved():
    api, _ = service(({"name": "One"}, {"name": "Two", "phone": "+1"}))
    providers = api.search_dermatologists({"location": "Demo"}).providers
    assert [item.name for item in providers] == ["One", "Two"]
    assert providers[0].address is providers[0].rating is providers[0].website is None


def test_empty_result_is_successful_without_fabricated_provider():
    result = service()[0].search_dermatologists({"city": "Empty"})
    assert result.success and result.providers == () and result.error_code is None


def test_missing_and_invalid_locations_are_structured_errors():
    api, _ = service()
    assert api.search_dermatologists(None).error_code == "LOCATION_REQUIRED"
    assert api.search_dermatologists({"latitude": 100, "longitude": 1}).error_code == "INVALID_LOCATION"
    assert api.search_dermatologists({"latitude": 1}).error_code == "INVALID_LOCATION"


def test_coordinate_location_is_accepted_when_explicitly_supplied():
    api, provider = service(({"name": "Coordinates", "geometry": {"location": {"lat": 1.1, "lng": 2.1}}},))
    result = api.search_dermatologists({"latitude": 1.0, "longitude": 2.0})
    assert result.success and result.query_location_type == "coordinates"
    assert result.providers[0].distance_source == "calculated" and provider.calls[0][0] == {"latitude": 1.0, "longitude": 2.0}


def test_external_distance_is_preferred_to_calculation():
    api, _ = service(({"name": "Clinic", "distance_meters": 1250, "latitude": 2, "longitude": 2},))
    item = api.search_dermatologists({"latitude": 1, "longitude": 1}).providers[0]
    assert item.distance_km == 1.25 and item.distance_source == "external"


def test_invalid_radius_and_limit_are_structured_errors():
    api, _ = service()
    assert api.search_dermatologists({"city": "X"}, radius_meters=0).error_code == "INVALID_RADIUS"
    assert api.search_dermatologists({"city": "X"}, limit=21).error_code == "INVALID_LIMIT"


def test_provider_failure_and_malformed_response_are_safe():
    failed = service(error=True)[0].search_dermatologists({"city": "X"})
    malformed = service({"raw": "object"})[0].search_dermatologists({"city": "X"})
    assert failed.error_code == malformed.error_code == "PROVIDER_UNAVAILABLE"
    assert "secret" not in failed.error_message.lower()


def test_normalized_output_excludes_unnecessary_raw_fields():
    api, _ = service(({"name": "Clinic", "raw_secret": "no", "photos": ["no"], "user_data": "no"},))
    item = api.search_dermatologists({"city": "X"}).providers[0]
    assert not hasattr(item, "raw_secret") and not hasattr(item, "photos") and not hasattr(item, "user_data")


def test_repeated_fake_results_are_deterministic_and_inputs_are_not_mutated():
    api, _ = service(({"name": "Clinic"},)); location = {"city": "X", "extra": "not retained"}
    first, second = api.search_dermatologists(location), api.search_dermatologists(location)
    assert first == second and location == {"city": "X", "extra": "not retained"}


def test_dependency_injection_supports_replacement_and_ac_adapter():
    api, _ = service(({"name": "Clinic", "types": ["dermatology"]},))
    options = api.find_dermatologists({"city": "X"}, 5, "dermatology")
    assert options[0].name == "Clinic" and options[0].specialty == "dermatology"


def test_ac_adapter_rejects_non_broad_specialty_without_inference():
    api, provider = service(({"name": "Clinic"},))
    assert api.find_dermatologists({"city": "X"}, 5, "acne specialist") == () and provider.calls == []


def test_no_medical_decision_fields_or_disease_logic_exist():
    result = service()[0].search_dermatologists({"city": "X"})
    assert not hasattr(result, "diagnosis") and not hasattr(result, "disease_probability") and not hasattr(result, "treatment")


def test_google_adapter_uses_environment_key_without_returning_it(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "environment-secret")
    client = FakeHttp({"status": "ZERO_RESULTS", "results": []})
    provider = GooglePlacesProvider(client=client)
    result = DermatologistSearchService(provider, "google_places").search_dermatologists({"city": "X"})
    assert result.success and client.calls[0][1]["key"] == "environment-secret"
    assert "environment-secret" not in str(result)


def test_google_adapter_missing_key_is_safe_and_no_http_call_is_made(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    client = FakeHttp({})
    result = DermatologistSearchService(GooglePlacesProvider(client=client), "google_places").search_dermatologists({"city": "X"})
    assert result.error_code == "PROVIDER_UNAVAILABLE" and client.calls == []


def test_google_adapter_requests_broad_dermatology_query_only():
    client = FakeHttp({"status": "ZERO_RESULTS", "results": []})
    GooglePlacesProvider(client=client, api_key="test-key").search_dermatologists({"city": "X"}, 5000, 10)
    assert client.calls[0][1]["query"] == "dermatology in X"


def test_provider_limit_is_applied_to_normalized_results():
    api, _ = service(({"name": "1"}, {"name": "2"}, {"name": "3"}))
    assert len(api.search_dermatologists({"city": "X"}, limit=2).providers) == 2


def test_location_is_not_persisted_on_service_or_result_metadata():
    api, _ = service(); result = api.search_dermatologists({"city": "X"})
    assert not hasattr(api, "location") and not hasattr(result, "location") and result.query_location_type == "manual"


def test_provider_record_has_only_expected_schema():
    api, _ = service(({"name": "Clinic"},)); record = api.search_dermatologists({"city": "X"}).providers[0]
    assert set(record.__dataclass_fields__) == {"provider_id", "name", "address", "latitude", "longitude", "distance_km", "distance_source", "provider_category", "rating", "opening_hours", "phone", "website", "source"}


def test_invalid_provider_coordinates_remain_missing_not_invented():
    api, _ = service(({"name": "Clinic", "latitude": "bad", "longitude": None},))
    item = api.search_dermatologists({"city": "X"}).providers[0]
    assert item.latitude is item.longitude is item.distance_km is None


def test_structured_error_fields_are_consistent():
    result = service()[0].search_dermatologists(None)
    assert result.success is False and result.providers == () and result.error_code and result.error_message


def test_manual_location_is_sanitized_before_provider_call():
    api, provider = service()
    api.search_dermatologists({"city": "  Demo City  ", "latitude": 1})
    assert provider.calls[0][0] == {"city": "Demo City"}


def test_google_response_with_non_success_status_becomes_safe_error():
    client = FakeHttp({"status": "OVER_QUERY_LIMIT", "results": []})
    result = DermatologistSearchService(GooglePlacesProvider(client=client, api_key="test-key")).search_dermatologists({"city": "X"})
    assert result.error_code == "PROVIDER_UNAVAILABLE"


def test_no_real_http_client_is_needed_for_fake_provider_tests():
    api, provider = service(({"name": "Synthetic"},))
    assert api.search_dermatologists({"city": "Synthetic"}).success is True
    assert isinstance(provider, FakeProvider)
