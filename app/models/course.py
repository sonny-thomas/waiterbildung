from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, HttpUrl


class IdentifierType(str, Enum):
    id = "id"
    class_ = "class"
    data_init = "data-init"


class Identifier(BaseModel):
    name: str
    type: IdentifierType
    value: str

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
        }


class ScrapingRequest(BaseModel):
    course_url: HttpUrl
    identifiers: List[Identifier]


class ScrapingJob(BaseModel):
    id: str
    status: str
    base_url: HttpUrl
    courses_scraped: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
