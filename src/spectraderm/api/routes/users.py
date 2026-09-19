from fastapi import APIRouter, Depends
from spectraderm.api.dependencies import ServiceContainer, get_container
from spectraderm.api.exceptions import APIError
from spectraderm.api.schemas.users import ConsentUpdateRequest, CreateUserRequest, UserResponse
router = APIRouter(prefix="/users", tags=["users"])
def _user(record): return UserResponse(user_id=record.user_id, scan_ids=list(record.scan_ids), created_at=record.created_at, updated_at=record.updated_at, general_consent=record.general_consent, location_consent=record.location_consent)
@router.post("", response_model=UserResponse, status_code=201)
def create(body: CreateUserRequest, services: ServiceContainer = Depends(get_container)): return _user(services.users.create_user(body.general_consent, body.location_consent))
@router.get("/{user_id}", response_model=UserResponse)
def get(user_id: str, services: ServiceContainer = Depends(get_container)):
    record = services.users.get_user(user_id)
    if record is None: raise APIError("USER_NOT_FOUND", "User was not found.", 404)
    return _user(record)
@router.patch("/{user_id}/consent", response_model=UserResponse)
def consent(user_id: str, body: ConsentUpdateRequest, services: ServiceContainer = Depends(get_container)):
    record = services.users.get_user(user_id)
    if record is None: raise APIError("USER_NOT_FOUND", "User was not found.", 404)
    if body.general_consent is not None: record = services.users.update_consent(user_id, body.general_consent)
    if body.location_consent is not None: record = services.users.update_location_consent(user_id, body.location_consent)
    return _user(record)
