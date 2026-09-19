from typing import Any
from pydantic import BaseModel
class ReportSectionResponse(BaseModel): title: str; status: str; items: list[dict[str, Any]]
class ReportResponse(BaseModel): sections: list[ReportSectionResponse]
