from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import HttpUrl, field_validator

from app.schemas import BaseRequest, BaseResponse, PaginatedRequest
from app.schemas.scraper import ScraperStatus


class InstitutionResponse(BaseResponse):
    id: str
    name: str
    logo: Optional[str]
    domain: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InstitutionCreate(BaseRequest):
    name: str
    logo: Optional[HttpUrl]
    domain: HttpUrl | str

    @field_validator("logo")
    def clean_logo(cls, v: Optional[HttpUrl]) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("domain")
    def extract_domain(cls, v: HttpUrl) -> str:
        return urlparse(str(v)).netloc


class InstitutionUpdate(InstitutionCreate):
    domain: Optional[HttpUrl | str] = None

    @field_validator("domain")
    def extract_domain(cls, v: Optional[HttpUrl]) -> Optional[str]:
        if v is None:
            return None
        return super().extract_domain(v)


class InstitutionPaginatedRequest(PaginatedRequest):
    status: Optional[ScraperStatus]
    is_active: Optional[bool] = None
