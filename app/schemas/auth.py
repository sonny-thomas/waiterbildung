from pydantic import EmailStr, field_validator

from app.core.security.password import validate_password
from app.schemas import BaseRequest, BaseResponse
from app.schemas.user import UserResponse


class UserRegister(BaseRequest):
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    avatar: str | None = None
    password: str | None = "w6^6wR4sDVY("

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_password(v)


class UserLogin(BaseRequest):
    email: EmailStr
    password: str = "w6^6wR4sDVY("


class Auth(BaseResponse):
    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int


class AuthResponse(Auth):
    user: UserResponse


class RefreshToken(BaseRequest):
    refresh_token: str


class ForgotPassword(BaseRequest):
    email: EmailStr


class ResetPassword(BaseRequest):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password(v)


class ChangePassword(BaseRequest):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password(v)
