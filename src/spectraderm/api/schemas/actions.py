from typing import Any
from pydantic import BaseModel
class LocationRequest(BaseModel): city: str | None = None; latitude: float | None = None; longitude: float | None = None; radius_km: float = 25.0
class ActionResponse(BaseModel): status: str; items: list[dict[str, Any]]
