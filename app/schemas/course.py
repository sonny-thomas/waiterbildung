from datetime import datetime
from typing import Optional

from pydantic import Field, HttpUrl, field_validator

from app.models.course import DegreeType, StudyMode
from app.schemas import BaseRequest, BaseResponse, PaginatedRequest


class CourseBase(BaseRequest):
    title: str = Field(..., max_length=500)
    description: str
    hero_image: Optional[HttpUrl | str] = None
    degree_type: Optional[DegreeType] = None
    study_mode: Optional[StudyMode] = None
    ects_credits: Optional[int] = None
    teaching_language: Optional[str] = Field(None, max_length=200)
    diploma_awarded: Optional[str] = Field(None, max_length=500)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_in_semesters: Optional[int] = None
    application_deadline: Optional[str] = None
    campus_location: Optional[str] = Field(None, max_length=200)
    study_abroad_available: bool = False
    tuition_fee_per_semester: Optional[str] = None
    is_featured: bool = False
    url: HttpUrl | str
    detailed_content: Optional[str] = None

    @field_validator("hero_image")
    def clean_hero_image(cls, v: Optional[HttpUrl]) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("url")
    def clean_url(cls, v: HttpUrl) -> str:
        return str(v)


class CourseCreate(CourseBase):
    institution_id: str


class CourseUpdate(CourseBase):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[HttpUrl] = None


class CourseBaseResponse(BaseResponse):
    title: str
    description: str
    degree_type: Optional[DegreeType]
    study_mode: Optional[StudyMode]
    ects_credits: Optional[int]
    teaching_language: Optional[str]
    diploma_awarded: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    duration_in_semesters: Optional[int]
    application_deadline: Optional[str]
    campus_location: Optional[str]
    study_abroad_available: bool
    tuition_fee_per_semester: Optional[str]


class CourseResponse(CourseBaseResponse):
    id: str
    hero_image: Optional[str]
    is_featured: bool
    url: str
    institution_id: str
    created_at: datetime
    updated_at: datetime


class CoursePaginatedRequest(PaginatedRequest):
    institution_id: Optional[str] = None
    degree_type: Optional[DegreeType] = None
    study_mode: Optional[StudyMode] = None
    is_featured: Optional[bool] = None


class ReviewRequest(BaseRequest):
    content: str
    rating: float


class ReviewResponse(BaseResponse):
    id: str
    content: str
    rating: float
    user_id: str
    course_id: str
    created_at: datetime
    updated_at: datetime


class ReviewPaginatedRequest(PaginatedRequest):
    user_id: Optional[str] = None
    course_id: Optional[str] = None
