from fastapi import APIRouter, Depends
from spectraderm.api.dependencies import ServiceContainer, get_container, to_data
from spectraderm.api.exceptions import APIError
from spectraderm.api.schemas.actions import ActionResponse, LocationRequest
router = APIRouter(prefix="/scans", tags=["actions"])
def _field(value, name): return value.get(name) if isinstance(value, dict) else getattr(value, name, None)
def _analysis(scan_id, user_id, services):
    if services.scans.get_scan(user_id, scan_id) is None: raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
    value = services.analysis_results.get(scan_id)
    if value is None: raise APIError("ANALYSIS_NOT_AVAILABLE", "No orchestrated analysis result is available for this scan.", 409)
    return value
@router.get("/{scan_id}/products", response_model=ActionResponse)
def products(scan_id: str, user_id: str, services: ServiceContainer = Depends(get_container)):
    try: output = services.actions.products(_analysis(scan_id, user_id, services))
    except APIError: raise
    except Exception as error: raise APIError("PRODUCT_SERVICE_FAILURE", "Product service is unavailable.", 503) from error
    if output is None: return ActionResponse(status="not_applicable", items=[])
    return ActionResponse(status=str(_field(output, "status") or "available"), items=to_data(_field(output, "recommendations") or []))
@router.post("/{scan_id}/referrals", response_model=ActionResponse)
def referrals(scan_id: str, body: LocationRequest, user_id: str, services: ServiceContainer = Depends(get_container)):
    location = {key: value for key, value in (("city", body.city), ("latitude", body.latitude), ("longitude", body.longitude)) if value is not None}
    try: output = services.actions.referrals(_analysis(scan_id, user_id, services), location or None, body.radius_km)
    except APIError: raise
    except Exception as error: raise APIError("PROVIDER_UNAVAILABLE", "Referral provider service is unavailable.", 503) from error
    if output is None: return ActionResponse(status="not_applicable", items=[])
    return ActionResponse(status=str(_field(output, "status") or "available"), items=to_data(_field(output, "options") or []))
