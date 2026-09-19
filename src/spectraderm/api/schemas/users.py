from datetime import datetime
from pydantic import BaseModel, StrictBool
class CreateUserRequest(BaseModel): general_consent: StrictBool = False; location_consent: StrictBool = False
class ConsentUpdateRequest(BaseModel): general_consent: StrictBool | None = None; location_consent: StrictBool | None = None
class UserResponse(BaseModel): user_id: str; scan_ids: list[str]; created_at: datetime; updated_at: datetime; general_consent: bool; location_consent: bool
