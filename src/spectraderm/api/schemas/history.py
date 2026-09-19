from spectraderm.api.schemas.scans import ScanResponse
from pydantic import BaseModel
class HistoryResponse(BaseModel): user_id: str; timeline: list[ScanResponse]
