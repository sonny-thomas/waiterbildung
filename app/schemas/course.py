from typing import Optional

from pydantic import HttpUrl

from app.models.course import DegreeType, StudyMode
from app.schemas import BaseResponse


class ScrapeCourse(BaseResponse):
    # Basic Information
    title: str
    description: str

    # Academic Details
    degree_type: Optional[DegreeType]
    study_mode: Optional[StudyMode]
    ects_credits: Optional[int]
    teaching_language: Optional[str]
    diploma_awarded: Optional[str]

    # Schedule and Duration
    start_date: Optional[str]
    end_date: Optional[str]
    duration_in_semesters: Optional[int]
    application_deadline: Optional[str]

    # Location and Delivery
    campus_location: Optional[str]
    study_abroad_available: bool
    tuition_fee_per_semester: Optional[str]


class CourseResponse(ScrapeCourse):
    # Web Links
    course_url: HttpUrl
    is_featured: bool = False

    # Ratings and Reviews
    average_rating: float = 0.0
    total_reviews: int = 0
