from fastapi import APIRouter, Depends
from spectraderm.api.dependencies import ServiceContainer, get_container
from spectraderm.api.exceptions import APIError
from spectraderm.api.routes.scans import _scan
from spectraderm.api.schemas.history import HistoryResponse
router = APIRouter(prefix="/users", tags=["history"])
@router.get("/{user_id}/history", response_model=HistoryResponse)
@router.get("/{user_id}/timeline", response_model=HistoryResponse)
def history(user_id: str, services: ServiceContainer = Depends(get_container)):
    if services.users.get_user(user_id) is None: raise APIError("USER_NOT_FOUND", "User was not found.", 404)
    timeline = []
    for index, item in enumerate(services.scans.list_user_scans(user_id)):
        change = services.scans.load_change_record(item) or {}
        entry = _scan(item)
        timeline.append(entry.model_copy(update={
            "change_score": change.get("change_score"), "change_percent": change.get("change_percent"),
            "status_label": change.get("status_label") or ("Baseline established" if index == 0 else None),
            "trend": change.get("trend"), "scan_number": index + 1,
        }))
    return HistoryResponse(user_id=user_id, timeline=timeline)
