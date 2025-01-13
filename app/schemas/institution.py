from enum import Enum
from typing import Optional

from pydantic import HttpUrl, field_validator

from app.core.utils import validate_https, normalize_url
from app.schemas import BaseRequest, BaseResponse
from urllib.parse import urlparse

class ScraperStatus(Enum):
    not_started = "not_started"
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AddInstitution(BaseRequest):
    name: str
    logo: Optional[HttpUrl]
    domain: HttpUrl | str

    @field_validator("domain")
    def extract_domain(cls, v: HttpUrl) -> str:
        validate_https(v)
        return urlparse(str(v)).netloc


class ScrapeInstitution(BaseRequest):
    start_url: HttpUrl
    course_selectors: set[str]
    hero_image_selector: Optional[str]
    max_courses: int = 50

    @field_validator("start_url")
    def must_be_https(cls, v: HttpUrl) -> HttpUrl:
        return validate_https(v)

class ScrapeInstitutionCourses(BaseRequest):
    hero_image_selector: Optional[str]
    course_urls: set[HttpUrl]

    @field_validator("course_urls")
    def validate_course_urls(cls, urls: list[HttpUrl]) -> list[str]:
        return [normalize_url(str(validate_https(url))) for url in urls]

class ScrapeSingleCourse(BaseRequest):
    course_url: HttpUrl
    course_selectors: set[str] | None = None
    hero_image_selector: str | None = None

    @field_validator("course_url")
    def must_be_https(cls, v: HttpUrl) -> str:
        return normalize_url(str(validate_https(v)))

class InstitutionResponse(BaseResponse):
    id: str
    name: str
    domain: str
    scraper_status: ScraperStatus
    is_active: bool
    average_rating: float
