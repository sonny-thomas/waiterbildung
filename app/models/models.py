from enum import Enum
from pydantic import BaseModel, HttpUrl


class IdentifierType(str, Enum):
    id = "id"
    class_ = "class"


class Identifier(BaseModel):
    name: str
    type: IdentifierType
    value: str


class ScrapeRequest(BaseModel):
    url: HttpUrl
    identifiers: list[Identifier]