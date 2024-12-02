from enum import Enum
from typing import Optional

from pydantic import Field, EmailStr, BaseModel as PydanticBaseModel, HttpUrl

from app.models import BaseModel


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    __collection_name__ = "users"

    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(..., unique=True)
    phone: Optional[str] = Field(None, unique=False)
    avatar: Optional[HttpUrl] = Field(None)
    hashed_password: Optional[str] = Field(None, exclude=True)
    role: UserRole = Field(...)
    is_active: bool = Field(default=False)

    async def save(self):
        user = await super().save()
        # TODO: Implement email verification logic here

        return user


class UserRegister(PydanticBaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(..., unique=True)
    password: str = Field(..., min_length=8)


class UserLogin(PydanticBaseModel):
    email_or_phone: str
    password: str


class UserAuth(PydanticBaseModel):
    access_token: str
    refresh_token: str
    user: User
