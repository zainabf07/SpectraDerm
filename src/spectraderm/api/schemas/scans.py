from datetime import datetime
from pydantic import BaseModel, Field
class CreateScanRequest(BaseModel):
    image_reference: str = Field(min_length=1); feature_reference: str | None = None; analysis_reference: str | None = None; change_reference: str | None = None; timestamp: datetime | None = None
class ScanResponse(BaseModel):
    scan_id: str; user_id: str; timestamp: datetime; feature_reference: str | None; analysis_reference: str | None; change_reference: str | None; created_at: datetime
    change_score: float | None = None; change_percent: float | None = None; status_label: str | None = None; trend: str | None = None; scan_number: int | None = None
class ScanListResponse(BaseModel): scans: list[ScanResponse]
class ImageArtifactResponse(BaseModel): image_reference: str
