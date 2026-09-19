from typing import Any
from pydantic import BaseModel, Field
class AnalysisRequest(BaseModel): input: dict[str, Any] = Field(default_factory=dict)
class AnalysisResponse(BaseModel): status: str; result: dict[str, Any]; safety: dict[str, Any] | None = None; next_action: str | None = None
