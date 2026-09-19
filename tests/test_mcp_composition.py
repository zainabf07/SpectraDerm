from spectraderm.api.config import APISettings
from spectraderm.api.dependencies import ServiceContainer
from spectraderm.mcp.composition import create_production_mcp_server
from spectraderm.mcp.server import TOOL_NAMES


def test_production_mcp_composes_the_existing_service_container(tmp_path):
    services = ServiceContainer(APISettings(storage_root=tmp_path))

    server = create_production_mcp_server(services)
    evidence = server.call_tool(
        "retrieve_evidence", input={"model_finding": "Model-derived observation: image quality output available."}
    )

    assert server.tool_names == TOOL_NAMES
    assert evidence["success"] is True
    assert evidence["data"]["retrieved_evidence"]
    assert server.call_tool("get_otc_product_categories")["success"] is True
