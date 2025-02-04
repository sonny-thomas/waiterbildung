from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import HttpUrl, field_validator

from app.core.utils import normalize_url, validate_https
from app.schemas import BaseRequest, BaseResponse


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


class UpdateInstitution(BaseRequest):
    name: Optional[str]
    logo: Optional[HttpUrl]
    domain: Optional[HttpUrl | str]

    @field_validator("domain")
    def extract_domain(cls, v: Optional[HttpUrl]) -> Optional[str]:
        if v is None:
            return None
        validate_https(v)
        return urlparse(str(v)).netloc

class CrawlInstitution(BaseRequest):
    institution_id: str
    start_url: HttpUrl
    course_selectors: set[str]
    hero_image_selector: Optional[str]
    max_courses: int = 50

    @field_validator("start_url")
    def must_be_https(cls, v: HttpUrl) -> HttpUrl:
        return validate_https(v)


class ScrapeInstitution(BaseRequest):
    institution_id: str
    hero_image_selector: Optional[str]
    course_urls: set[HttpUrl]

    @field_validator("course_urls")
    def validate_course_urls(cls, urls: list[HttpUrl]) -> list[str]:
        return [normalize_url(str(validate_https(url))) for url in urls]


class InstitutionResponse(BaseResponse):
    id: str
    name: str
    logo: Optional[str]
    domain: str
    scraper_status: ScraperStatus
    is_active: bool
    average_rating: float
