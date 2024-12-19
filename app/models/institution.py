from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, HttpUrl

from app.models import BaseModel, PyObjectId
from app.models.user import User


class TargetField(BaseModel):
    name: str = Field(...)


class Institution(BaseModel):
    __collection_name__ = "institutions"

    name: str = Field(...)
    rep: Optional[Union[PyObjectId, User]] = Field(None)
    website: HttpUrl = Field(...)
    status: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=True)
    courses_scraped: Optional[int] = Field(default=0)
    avg_rating: Optional[float] = Field(default=0)
    completed_at: Optional[datetime] = Field(default=None, exclude=True)
    message: Optional[str] = Field(default=None, exclude=True)
    target_fields: Optional[List[TargetField]] = Field(
        default=None, exclude=True
    )

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filters: Optional[dict] = None,
        sort: Optional[List[tuple]] = None,
    ) -> dict:
        documents, total = await super().list(page, limit, filters or {}, sort)
        institutions = []
        for doc in documents:
            if doc.rep:
                user = await User.get(doc.rep)
                if user:
                    doc.rep = user
            institutions.append(doc)
        return InstitutionList(
            institutions=institutions, total=total, page=page, size=limit
        )


class InstitutionList(PydanticBaseModel):
    institutions: List[Institution]
    total: int
    page: int
    size: int
