from dataclasses import dataclass

from spectraderm.mcp.server import MCPCapabilities, TOOL_NAMES, create_mcp_server


class Provider:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def find_dermatologists(self, location, radius_km, specialty="dermatology"):
        self.calls.append((dict(location), radius_km, specialty))
        if self.fail: raise RuntimeError("synthetic")
        return ({"name": "Synthetic Dermatology", "source": "synthetic"},)


def capability(name, calls, fail=False):
    def run(value):
        calls.append((name, dict(value)))
        if fail: raise RuntimeError("synthetic")
        return {"delegated": name, "received": dict(value)}
    return run


def server(fail_name=None):
    calls = []
    kwargs = {name: capability(name, calls, name == fail_name) for name in TOOL_NAMES if name not in {"find_dermatologists", "get_otc_product_categories"}}
    return create_mcp_server(MCPCapabilities(**kwargs, dermatologist_provider=Provider())), calls


def test_server_initializes_with_genuine_mcp_server():
    instance, _ = server()
    assert instance.mcp is not None and instance.tool_names == TOOL_NAMES


def test_exactly_ten_expected_tools_are_registered_deterministically():
    instance, _ = server()
    assert len(instance.tool_names) == 10
    assert instance.tool_names == TOOL_NAMES
    assert "get_partner_products" not in instance.tool_names


def test_tool_schemas_are_explicit_and_valid():
    instance, _ = server()
    assert set(instance.tool_schemas) == set(TOOL_NAMES)
    assert instance.tool_schemas["find_dermatologists"]["required"] == ["location", "radius_km"]


def test_generic_invalid_input_is_a_structured_error():
    instance, _ = server()
    output = instance.call_tool("reconstruct_spectrum", input="not-an-object")
    assert output == {"success": False, "error_code": "INVALID_INPUT", "message": "input must be an object.", "data": None}


def test_reconstruct_delegates_to_injected_capability():
    instance, calls = server()
    assert instance.call_tool("reconstruct_spectrum", input={"scan": 1})["success"] is True
    assert calls == [("reconstruct_spectrum", {"scan": 1})]


def test_analyze_skin_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("analyze_skin", input={"input": "x"})
    assert calls[0][0] == "analyze_skin"


def test_extract_features_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("extract_features", input={"input": "x"})
    assert calls[0][0] == "extract_features"


def test_warning_score_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("calculate_warning_score", input={"engineering": "output"})
    assert calls[0][0] == "calculate_warning_score"


def test_compare_scans_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("compare_scans", input={"scans": []})
    assert calls[0][0] == "compare_scans"


def test_retrieve_evidence_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("retrieve_evidence", input={"query": "supplied"})
    assert calls[0][0] == "retrieve_evidence"


def test_history_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("get_skin_history", input={"scan_id": "x"})
    assert calls[0][0] == "get_skin_history"


def test_find_dermatologists_delegates_without_external_service():
    provider = Provider()
    instance = create_mcp_server(MCPCapabilities(dermatologist_provider=provider))
    output = instance.call_tool("find_dermatologists", location={"city": "Synthetic City"}, radius_km=10)
    assert output["success"] is True and provider.calls == [({"city": "Synthetic City"}, 10.0, "dermatology")]


def test_find_dermatologists_validates_location_radius_and_specialty():
    instance, _ = server()
    assert instance.call_tool("find_dermatologists", location=None, radius_km=2)["error_code"] == "INVALID_LOCATION"
    assert instance.call_tool("find_dermatologists", location={"city": "X"}, radius_km=0)["error_code"] == "INVALID_RADIUS"
    assert instance.call_tool("find_dermatologists", location={"city": "X"}, radius_km=2, specialty="oncology")["error_code"] == "INVALID_SPECIALTY"


def test_provider_failure_is_structured_without_exception_details():
    output = create_mcp_server(MCPCapabilities(dermatologist_provider=Provider(True))).call_tool(
        "find_dermatologists", location={"city": "X"}, radius_km=2
    )
    assert output["error_code"] == "SERVICE_FAILURE" and "synthetic" not in output["message"]


def test_default_otc_categories_are_general_categories_only():
    instance, _ = server()
    output = instance.call_tool("get_otc_product_categories")
    text = str(output["data"]).lower()
    assert output["success"] is True and "gentle_cleanser" in text
    assert not any(term in text for term in ("http", "price", "affiliate"))


def test_otc_category_capability_can_be_injected():
    instance = create_mcp_server(MCPCapabilities(get_otc_product_categories=lambda: ({"category_id": "custom"},)))
    assert instance.call_tool("get_otc_product_categories")["data"] == [{"category_id": "custom"}]


def test_report_delegates_to_injected_capability():
    instance, calls = server()
    instance.call_tool("generate_report", input={"result": "structured"})
    assert calls[0][0] == "generate_report"


def test_service_unavailable_and_unknown_tool_are_machine_readable():
    instance = create_mcp_server()
    assert instance.call_tool("analyze_skin", input={})["error_code"] == "SERVICE_UNAVAILABLE"
    assert instance.call_tool("unknown")["error_code"] == "UNKNOWN_TOOL"


def test_generic_service_failure_is_machine_readable():
    instance, _ = server("analyze_skin")
    assert instance.call_tool("analyze_skin", input={})["error_code"] == "SERVICE_FAILURE"


def test_mcp_preserves_input_objects_and_is_deterministic():
    instance, _ = server()
    payload = {"nested": {"value": 1}}
    first = instance.call_tool("calculate_warning_score", input=payload)
    second = instance.call_tool("calculate_warning_score", input=payload)
    assert first == second and payload == {"nested": {"value": 1}}


def test_output_has_no_medical_decision_fields_or_claims():
    instance, _ = server()
    output = instance.call_tool("calculate_warning_score", input={})
    text = str(output).lower()
    assert not hasattr(instance, "diagnosis") and not hasattr(instance, "disease_probability")
    assert not any(term in text for term in ("diagnosis", "treatment", "medication", "melanoma"))


def test_coordinate_location_is_accepted_without_device_access():
    provider = Provider()
    instance = create_mcp_server(MCPCapabilities(dermatologist_provider=provider))
    instance.call_tool("find_dermatologists", location={"latitude": 25.2, "longitude": 55.3}, radius_km=3)
    assert provider.calls[0][0] == {"latitude": 25.2, "longitude": 55.3}


def test_valid_specialty_is_normalized_to_the_broad_dermatology_contract():
    provider = Provider()
    instance = create_mcp_server(MCPCapabilities(dermatologist_provider=provider))
    output = instance.call_tool("find_dermatologists", location={"city": "X"}, radius_km=2, specialty="DERMATOLOGY")
    assert output["success"] is True and provider.calls[0][2] == "dermatology"


def test_tool_outputs_have_the_same_structured_envelope():
    instance, _ = server()
    for name in ("reconstruct_spectrum", "get_otc_product_categories", "find_dermatologists"):
        arguments = {"input": {}} if name == "reconstruct_spectrum" else (
            {"location": {"city": "X"}, "radius_km": 1} if name == "find_dermatologists" else {}
        )
        assert set(instance.call_tool(name, **arguments)) == {"success", "error_code", "message", "data"}
