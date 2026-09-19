from fastapi import APIRouter, Depends
from spectraderm.api.dependencies import ServiceContainer, get_container, to_data
from spectraderm.api.exceptions import APIError
from spectraderm.api.schemas.analysis import AnalysisRequest, AnalysisResponse
router = APIRouter(prefix="/scans", tags=["analysis"])
def _field(value, name): return value.get(name) if isinstance(value, dict) else getattr(value, name, None)
@router.post("/{scan_id}/analyze", response_model=AnalysisResponse)
def analyze(scan_id: str, body: AnalysisRequest, user_id: str, services: ServiceContainer = Depends(get_container)):
    scan = services.scans.get_scan(user_id, scan_id)
    if scan is None: raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
    try: result = services.analysis.analyze(scan, body.input)
    except APIError: raise
    except Exception as error: raise APIError("ANALYSIS_FAILED", "Analysis could not be completed.", 503) from error
    services.analysis_results[scan_id] = result
    safety = _field(result, "safety_result")
    return AnalysisResponse(status=str(_field(result, "status") or "completed"), result=to_data(result), safety=to_data(safety) if safety is not None else None, next_action=_field(result, "recommended_path"))
