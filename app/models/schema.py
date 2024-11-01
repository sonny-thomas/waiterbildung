from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class SchemaRequest(BaseModel):
    course_url: str
    target_fields: List[str]


class Schema(BaseModel):
    course_url: str
    target_fields: list


class EducationalProvider(BaseModel):
    id: str
    status: str
    base_url: HttpUrl
    task_id: str
    courses_scraped: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    message: Optional[str] = None
    target_fields: list
