from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import HttpUrl, field_validator

from app.core.utils import normalize_url, validate_https
from app.schemas import BaseRequest


class ScraperStatus(Enum):
    not_started = "not_started"
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


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
