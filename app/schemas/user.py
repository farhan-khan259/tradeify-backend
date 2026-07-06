from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    balance: float
    referral_code: str
    created_at: datetime


class UserAdminView(UserPublic):
    referred_by_id: int | None = None
