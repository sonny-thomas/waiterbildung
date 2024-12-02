from datetime import datetime
from typing import List, Optional

from pydantic import Field, HttpUrl

from app.models import BaseModel


class TargetField(BaseModel):
    name: str = Field(...)


class Institution(BaseModel):
    __collection_name__ = "institutions"

    name: str = Field(...)
    website: HttpUrl = Field(...)
    status: Optional[str] = Field(default=None, exclude=True)
    courses_scraped: Optional[int] = Field(default=None, exclude=True)
    completed_at: Optional[datetime] = Field(default=None, exclude=True)
    message: Optional[str] = Field(default=None, exclude=True)
    target_fields: Optional[List[TargetField]] = Field(default=None, exclude=True)
