"""Production composition of AE's existing MCP contracts over API services."""
from __future__ import annotations

from typing import Any, Mapping

from spectraderm.agents.product_agent import CATALOG
from spectraderm.mcp.server import MCPCapabilities, SpectraDermMCPServer, create_mcp_server


def _required(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def create_production_mcp_server(services: Any) -> SpectraDermMCPServer:
    """Bind AE to the same container-owned services used by FastAPI.

    Inputs identify AG-managed scans; no tool accepts browser filenames or
    arbitrary filesystem paths.  Every analysis-related capability delegates
    to the container's real analysis service rather than recreating a module.
    """
    def scan_for(payload: Mapping[str, Any]) -> Any:
        scan = services.scans.get_scan(_required(payload, "user_id"), _required(payload, "scan_id"))
        if scan is None:
            raise ValueError("scan was not found or is not owned by this user")
        return scan

    def analyze(payload: Mapping[str, Any]) -> Any:
        scan = scan_for(payload)
        result = services.analysis.analyze(scan, dict(payload.get("input") or {}))
        services.analysis_results[scan.scan_id] = result
        return result

    def stored_analysis(payload: Mapping[str, Any]) -> Any:
        scan = scan_for(payload)
        result = services.analysis_results.get(scan.scan_id)
        if result is None:
            raise ValueError("scan has not been analyzed")
        return result

    def reconstruct(payload: Mapping[str, Any]) -> Any:
        result = analyze(payload)
        return _field(_field(result, "metadata"), "pipeline")

    def features(payload: Mapping[str, Any]) -> Any:
        result = stored_analysis(payload)
        pipeline = _field(_field(result, "metadata"), "pipeline")
        return {
            "rgb_feature_count": _field(pipeline, "rgb_feature_count"),
            "spectral_reconstruction_available": _field(pipeline, "spectral_reconstruction_available"),
        }

    def monitoring(payload: Mapping[str, Any]) -> Any:
        return _field(stored_analysis(payload), "monitoring_result")

    def evidence(payload: Mapping[str, Any]) -> Any:
        finding = payload.get("model_finding") or payload.get("query")
        if not isinstance(finding, str) or not finding.strip():
            raise ValueError("model_finding or query is required")
        return services.rag.run(finding, top_k=int(payload.get("top_k", 3)))

    def history(payload: Mapping[str, Any]) -> Any:
        user_id = _required(payload, "user_id")
        if services.users.get_user(user_id) is None:
            raise ValueError("user was not found")
        return services.scans.list_user_scans(user_id)

    def report(payload: Mapping[str, Any]) -> Any:
        scan = scan_for(payload)
        result = stored_analysis(payload)
        pipeline = _field(_field(result, "metadata"), "pipeline")
        spectral = {"available": True, "status": "available", "summary": "AI-estimated spectral representation is available.", "reconstruction_method": "MST++ RGB reconstruction"} if _field(pipeline, "spectral_reconstruction_available") is True else None
        return services.reports.generate_report(
            scan, vision=_field(result, "vision_result"), monitoring=_field(result, "monitoring_result"),
            evidence=_field(result, "evidence_result"), safety=_field(result, "safety_result"),
            spectral=spectral, product=_field(result, "product_result"), referral=_field(result, "referral_result"),
        )

    return create_mcp_server(MCPCapabilities(
        reconstruct_spectrum=reconstruct, analyze_skin=analyze, extract_features=features,
        calculate_warning_score=monitoring, compare_scans=monitoring, retrieve_evidence=evidence,
        get_skin_history=history, dermatologist_provider=services.actions.referral_agent._provider,
        get_otc_product_categories=lambda: tuple(CATALOG.values()),
        generate_report=report,
    ))
