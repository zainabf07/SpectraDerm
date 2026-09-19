"""Genuine MCP tool registration for thin, injected SpectraDerm adapters.

Module AE is infrastructure only: it validates tool contracts and delegates to
supplied services. It contains no medical reasoning or external API client.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from math import isfinite
from typing import Any, Protocol

from spectraderm.agents.product_agent import CATALOG


TOOL_NAMES = (
    "reconstruct_spectrum", "analyze_skin", "extract_features", "calculate_warning_score",
    "compare_scans", "retrieve_evidence", "get_skin_history", "find_dermatologists",
    "get_otc_product_categories", "generate_report",
)


class DermatologistProvider(Protocol):
    def find_dermatologists(
        self, location: Mapping[str, Any], radius_km: float, specialty: str = "dermatology"
    ) -> Any: ...


@dataclass(frozen=True)
class MCPCapabilities:
    """Injected existing-module or future-service boundaries for the ten tools."""

    reconstruct_spectrum: Callable[[Mapping[str, Any]], Any] | None = None
    analyze_skin: Callable[[Mapping[str, Any]], Any] | None = None
    extract_features: Callable[[Mapping[str, Any]], Any] | None = None
    calculate_warning_score: Callable[[Mapping[str, Any]], Any] | None = None
    compare_scans: Callable[[Mapping[str, Any]], Any] | None = None
    retrieve_evidence: Callable[[Mapping[str, Any]], Any] | None = None
    get_skin_history: Callable[[Mapping[str, Any]], Any] | None = None
    dermatologist_provider: DermatologistProvider | None = None
    get_otc_product_categories: Callable[[], Any] | None = None
    generate_report: Callable[[Mapping[str, Any]], Any] | None = None


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def _error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error_code": code, "message": message, "data": None}


def _valid_location(location: Any) -> dict[str, Any] | None:
    if not isinstance(location, Mapping):
        return None
    city = location.get("city")
    if isinstance(city, str) and city.strip():
        return {"city": city.strip()}
    latitude, longitude = location.get("latitude"), location.get("longitude")
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (latitude, longitude)):
        return {"latitude": float(latitude), "longitude": float(longitude)}
    return None


def _category_data() -> tuple[dict[str, str], ...]:
    """Expose existing AB's controlled generic categories, never commercial products."""
    return tuple(
        {"category_id": item.category_id, "category_name": item.category_name, "neutral_description": item.neutral_description}
        for item in CATALOG.values()
    )


class SpectraDermMCPServer:
    """A genuine MCPServer plus deterministic direct-call helpers for application tests."""

    def __init__(self, capabilities: MCPCapabilities | None = None) -> None:
        self.capabilities = capabilities or MCPCapabilities()
        # Import lazily so non-MCP SpectraDerm modules retain no runtime SDK dependency.
        from mcp.server import MCPServer

        self.mcp = MCPServer("SpectraDerm MCP")
        self._register_tools()

    @property
    def tool_names(self) -> tuple[str, ...]:
        return TOOL_NAMES

    @property
    def tool_schemas(self) -> dict[str, dict[str, Any]]:
        generic = {"type": "object", "properties": {"input": {"type": "object"}}, "required": ["input"]}
        return {
            **{name: generic for name in TOOL_NAMES[:7]},
            "find_dermatologists": {
                "type": "object", "properties": {
                    "location": {"type": "object"}, "radius_km": {"type": "number", "exclusiveMinimum": 0},
                    "specialty": {"type": "string", "default": "dermatology"},
                }, "required": ["location", "radius_km"],
            },
            "get_otc_product_categories": {"type": "object", "properties": {}},
            "generate_report": generic,
        }

    def _delegate(self, name: str, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            return _error("INVALID_INPUT", "input must be an object.")
        capability = getattr(self.capabilities, name)
        if capability is None:
            return _error("SERVICE_UNAVAILABLE", f"{name} capability is not configured.")
        try:
            return {"success": True, "error_code": None, "message": "", "data": _json_value(capability(dict(payload)))}
        except Exception:
            return _error("SERVICE_FAILURE", f"{name} capability failed.")

    def call_tool(self, name: str, **arguments: Any) -> dict[str, Any]:
        """Deterministic adapter invocation used by application code and unit tests."""
        if name not in TOOL_NAMES:
            return _error("UNKNOWN_TOOL", "The requested MCP tool is not registered.")
        if name == "find_dermatologists":
            location = _valid_location(arguments.get("location"))
            radius = arguments.get("radius_km")
            specialty = arguments.get("specialty", "dermatology")
            if location is None:
                return _error("INVALID_LOCATION", "A valid city or latitude/longitude location is required.")
            if not isinstance(radius, (int, float)) or isinstance(radius, bool) or not isfinite(radius) or radius <= 0:
                return _error("INVALID_RADIUS", "radius_km must be a positive finite number.")
            if not isinstance(specialty, str) or specialty.strip().casefold() != "dermatology":
                return _error("INVALID_SPECIALTY", "Only the broad specialty 'dermatology' is supported.")
            provider = self.capabilities.dermatologist_provider
            if provider is None:
                return _error("SERVICE_UNAVAILABLE", "Dermatologist provider capability is not configured.")
            try:
                data = provider.find_dermatologists(location, float(radius), "dermatology")
                return {"success": True, "error_code": None, "message": "", "data": _json_value(data)}
            except Exception:
                return _error("SERVICE_FAILURE", "Dermatologist provider capability failed.")
        if name == "get_otc_product_categories":
            capability = self.capabilities.get_otc_product_categories
            try:
                data = capability() if capability is not None else _category_data()
                return {"success": True, "error_code": None, "message": "", "data": _json_value(data)}
            except Exception:
                return _error("SERVICE_FAILURE", "Product-category capability failed.")
        return self._delegate(name, arguments.get("input"))

    def _register_tools(self) -> None:
        """Register exactly the specified tools with the official MCP SDK server."""
        def generic(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def handler(input: dict[str, Any]) -> dict[str, Any]:
                return self.call_tool(name, input=input)
            handler.__name__ = name
            return handler

        for name in TOOL_NAMES[:7]:
            self.mcp.add_tool(generic(name), name=name, structured_output=True)

        @self.mcp.tool(name="find_dermatologists", structured_output=True)
        def find_dermatologists(location: dict[str, Any], radius_km: float, specialty: str = "dermatology") -> dict[str, Any]:
            return self.call_tool("find_dermatologists", location=location, radius_km=radius_km, specialty=specialty)

        @self.mcp.tool(name="get_otc_product_categories", structured_output=True)
        def get_otc_product_categories() -> dict[str, Any]:
            return self.call_tool("get_otc_product_categories")

        self.mcp.add_tool(generic("generate_report"), name="generate_report", structured_output=True)


def create_mcp_server(capabilities: MCPCapabilities | None = None) -> SpectraDermMCPServer:
    """Create the independently testable Module AE MCP server wrapper."""
    return SpectraDermMCPServer(capabilities)
