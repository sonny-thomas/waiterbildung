import enum
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.core.email import send_reset_password, send_verification_email
from app.models import BaseModel
from app.models.course import course_bookmarks


class UserRole(enum.Enum):
    user = "user"
    instructor = "instructor"
    admin = "admin"


class User(BaseModel):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(30), nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), unique=False, nullable=True
    )
    password: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), nullable=False, default=UserRole.user
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    password_reset_token_expires_at: Mapped[Optional[datetime]] = (
        mapped_column(DateTime, nullable=True)
    )
    institution_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    institution = relationship(
        "Institution", backref=backref("instructors", lazy="dynamic")
    )

    bookmarked_courses = relationship(
        "Course",
        secondary=course_bookmarks,
        backref=backref("bookmarked_by", lazy="dynamic"),
    )

    SEARCH_FIELDS = ["email", "first_name", "last_name"]

    def send_verification_token(self) -> str:
        """Generate verification token and set expiration"""
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires_at = datetime.now(
            timezone.utc
        ) + timedelta(hours=24)
        send_verification_email(
            self.email, self.first_name, self.verification_token
        )
        return self.verification_token

    def send_password_reset_token(self) -> str:
        """Generate password reset token and set expiration

        Returns:
            str: The generated reset token
        """
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_token_expires_at = datetime.now(
            timezone.utc
        ) + timedelta(hours=24)

        send_reset_password(
            self.email, self.first_name, self.password_reset_token
        )
        return self.password_reset_token
