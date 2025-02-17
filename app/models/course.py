from enum import Enum
from typing import Optional

from pydantic import HttpUrl
from sqlalchemy import Boolean, Column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.models import BaseModel


class DegreeType(str, Enum):
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    not_specified = "not_specified"


class StudyMode(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    online = "online"
    hybrid = "hybrid"
    not_specified = "not_specified"


class Course(BaseModel):
    __tablename__ = "courses"

    # Basic Information
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hero_image: Mapped[Optional[HttpUrl]] = mapped_column(
        String(500), nullable=True
    )

    # Academic Details
    degree_type: Mapped[Optional[DegreeType]] = mapped_column(
        SQLEnum(DegreeType), nullable=True
    )
    study_mode: Mapped[Optional[StudyMode]] = mapped_column(
        SQLEnum(StudyMode), nullable=True
    )
    ects_credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    teaching_language: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    diploma_awarded: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Schedule and Duration
    start_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_in_semesters: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    application_deadline: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )

    # Location and Delivery
    campus_location: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    study_abroad_available: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    tuition_fee_per_semester: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )

    # Additional Content
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[HttpUrl] = mapped_column(String(500), nullable=False)
    detailed_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id"), nullable=False
    )
    institution = relationship(
        "Institution", backref=backref("courses", lazy="dynamic")
    )


course_bookmarks = Table(
    "course_bookmarks",
    BaseModel.metadata,
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("course_id", String, ForeignKey("courses.id"), primary_key=True),
)
