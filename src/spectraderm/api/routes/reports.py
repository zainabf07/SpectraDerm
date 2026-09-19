from fastapi import APIRouter, Depends
from spectraderm.api.dependencies import ServiceContainer, get_container, to_data
from spectraderm.api.exceptions import APIError
from spectraderm.api.schemas.reports import ReportResponse, ReportSectionResponse
from spectraderm.reporting.monitoring_report import build_monitoring_report
router = APIRouter(prefix="/scans", tags=["reports"])
def _field(value, name): return value.get(name) if isinstance(value, dict) else getattr(value, name, None)
@router.get("/{scan_id}/report", response_model=ReportResponse)
def report(scan_id: str, user_id: str, services: ServiceContainer = Depends(get_container)):
    scan = services.scans.get_scan(user_id, scan_id)
    if scan is None: raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
    analysis = services.analysis_results.get(scan_id)
    pipeline = _field(_field(analysis, "metadata"), "pipeline")
    reconstruction_available = _field(pipeline, "spectral_reconstruction_available")
    spectral = {
        "available": True,
        "status": "available",
        "summary": "AI-estimated spectral representation is available.",
        "reconstruction_method": "MST++ RGB reconstruction",
    } if reconstruction_available is True else None
    result = services.reports.generate_report(scan, vision=_field(analysis, "vision_result"), monitoring=_field(analysis, "monitoring_result"), evidence=_field(analysis, "evidence_result"), safety=_field(analysis, "safety_result"), spectral=spectral, product=_field(analysis, "product_result"), referral=_field(analysis, "referral_result"))
    return ReportResponse(sections=[ReportSectionResponse(title=section.title, status=section.status, items=[{"label": item.label, "value": item.value} for item in section.items]) for section in result.sections])


@router.get("/{scan_id}/monitoring-report")
def monitoring_report(scan_id: str, user_id: str, services: ServiceContainer = Depends(get_container)) -> dict:
    """User-facing report combining analysis, change, history, evidence, safety and next action."""
    scan = services.scans.get_scan(user_id, scan_id)
    if scan is None: raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
    analysis = services.analysis_results.get(scan_id)
    if analysis is None:
        # Results live in memory; after a restart, re-run the analysis so the
        # report is always available for a stored scan.
        try: analysis = services.analysis.analyze(scan, {})
        except APIError: raise
        except Exception as error: raise APIError("ANALYSIS_FAILED", "Analysis could not be completed.", 503) from error
        services.analysis_results[scan_id] = analysis
    return build_monitoring_report(scan, to_data(analysis))
