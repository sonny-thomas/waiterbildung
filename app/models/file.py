from pydantic import Field, HttpUrl

from app.models import BaseModel


class File(BaseModel):
    __collection_name__ = "files"

    url: HttpUrl = Field(...)
