from pydantic import EmailStr

from app.models.user import UserRole
from app.schemas import BaseResponse


class UserResponse(BaseResponse):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    avatar: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
