from typing import Generic, Optional, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseRequest(BaseModel):
    pass


class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)


class PaginatedRequest(BaseRequest):
    skip: int = 0
    limit: int = 100
    sort_by: Optional[str] = None
    descending: bool = False
    use_or: bool = True
