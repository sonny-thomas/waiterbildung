from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class ScrapingRequest(BaseModel):
    course_url: HttpUrl
    target_fields: List[str]


class ScrapingJob(BaseModel):
    id: str
    status: str
    base_url: HttpUrl
    course_url: HttpUrl
    target_fields: List[str]
    courses_scraped: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    message: Optional[str]
