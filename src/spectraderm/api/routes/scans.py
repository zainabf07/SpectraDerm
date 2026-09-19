from fastapi import APIRouter, Depends, File, UploadFile
from spectraderm.api.dependencies import ServiceContainer, get_container
from spectraderm.api.exceptions import APIError
from spectraderm.api.schemas.scans import CreateScanRequest, ImageArtifactResponse, ScanListResponse, ScanResponse
from spectraderm.storage.scan_storage import MAX_IMAGE_ARTIFACT_BYTES
router = APIRouter(tags=["scans"])
def _scan(record): return ScanResponse(scan_id=record.scan_id, user_id=record.user_id, timestamp=record.timestamp, feature_reference=record.feature_reference, analysis_reference=record.analysis_reference, change_reference=record.change_reference, created_at=record.created_at)

@router.post("/users/{user_id}/image-artifacts", response_model=ImageArtifactResponse, status_code=201)
def upload_image(user_id: str, file: UploadFile = File(...), services: ServiceContainer = Depends(get_container)):
    try:
        content = file.file.read(MAX_IMAGE_ARTIFACT_BYTES + 1)
        reference = services.scans.store_image_artifact(user_id, content)
        return ImageArtifactResponse(image_reference=reference)
    except ValueError as error:
        message = str(error)
        if "maximum allowed size" in message:
            raise APIError("IMAGE_TOO_LARGE", "The image exceeds the 10 MB upload limit.", 413) from error
        if "user_id" in message:
            raise APIError("USER_NOT_FOUND", "User was not found.", 404) from error
        raise APIError("UNSUPPORTED_IMAGE", "Upload a JPEG, PNG, or WebP image.", 415) from error
@router.post("/users/{user_id}/scans", response_model=ScanResponse, status_code=201)
def create(user_id: str, body: CreateScanRequest, services: ServiceContainer = Depends(get_container)):
    payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    try: return _scan(services.scans.create_scan(user_id, **payload))
    except ValueError as error: raise APIError("INVALID_SCAN", "Scan could not be created.", 400) from error
@router.get("/users/{user_id}/scans", response_model=ScanListResponse)
def list_scans(user_id: str, services: ServiceContainer = Depends(get_container)):
    if services.users.get_user(user_id) is None: raise APIError("USER_NOT_FOUND", "User was not found.", 404)
    return ScanListResponse(scans=[_scan(item) for item in services.scans.list_user_scans(user_id)])
@router.get("/scans/{scan_id}", response_model=ScanResponse)
def get(scan_id: str, user_id: str, services: ServiceContainer = Depends(get_container)):
    record = services.scans.get_scan(user_id, scan_id)
    if record is None: raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
    return _scan(record)
@router.delete("/scans/{scan_id}", status_code=204)
def delete(scan_id: str, user_id: str, services: ServiceContainer = Depends(get_container)):
    if not services.scans.delete_scan(user_id, scan_id): raise APIError("SCAN_NOT_FOUND", "Scan was not found or is not owned by this user.", 404)
