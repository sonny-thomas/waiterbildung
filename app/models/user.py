from datetime import datetime, timezone
from enum import Enum
import secrets
from typing import Any, Dict, List, Optional

from pydantic import Field, EmailStr, BaseModel as PydanticBaseModel, HttpUrl

from app.models import BaseModel
from app.core import db


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
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    bookmarked_courses: List = Field(default=[])


class UserList(PydanticBaseModel):
    users: List[User]
    total: int
    page: int
    size: int


class UserRegister(PydanticBaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(..., unique=True)
    password: Optional[str] = Field("", min_length=8)


class UserLogin(PydanticBaseModel):
    email: EmailStr = Field()
    password: str
    remember_me: Optional[bool] = Field(default=False)


class UserAuth(PydanticBaseModel):
    access_token: str
    refresh_token: str
    user: User


class Email(PydanticBaseModel):
    email: EmailStr = Field()


class Token(PydanticBaseModel):
    token: str = Field()

class Status(PydanticBaseModel):
    is_active: bool = Field(default=True)

class ResetPassword(PydanticBaseModel):
    new_password: str = Field(..., min_length=8)
    old_password: Optional[str] = Field(None)
    token: Optional[str] = Field(None)


class TokenBaseModel(BaseModel):
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    verified_at: Optional[datetime] = Field(None)

    async def save(self) -> Dict[str, Any]:
        """
        Save the current instance to the database

        :param include: Set of fields to include in the saved document
        :return: Serialized saved document
        """
        collection = db.get_collection(self.__collection_name__)

        self.token = secrets.token_urlsafe(32)
        self.updated_at = datetime.now(timezone.utc)
        doc = self.model_dump(by_alias=True, mode="json")

        await collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

        return self.__class__(**doc) if doc else None


class EmailVerification(TokenBaseModel):
    __collection_name__ = "email_verification"


class PasswordReset(TokenBaseModel):
    __collection_name__ = "password_reset"
