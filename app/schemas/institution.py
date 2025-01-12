from enum import Enum
from typing import Optional

from pydantic import HttpUrl, field_validator

from app.core.utils import validate_https
from app.schemas import BaseRequest, BaseResponse


class ScraperStatus(Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScrapeInstitution(BaseRequest):
    name: str
    logo: Optional[HttpUrl] = None
    start_url: HttpUrl
    course_selector: str
    hero_image_selector: Optional[str]
    max_courses: int = 50

    @field_validator("start_url", "logo")
    def must_be_https(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        if v is not None:
            return validate_https(v)
        return v


class InstitutionResponse(BaseResponse):
    id: str
    name: str
    domain: str
    scraper_status: ScraperStatus
    is_active: bool
    average_rating: float
