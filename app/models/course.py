from typing import Any, Dict, List, Optional, Union

from pydantic import ConfigDict, Field, HttpUrl

from app.core.database import db
from app.models import BaseModel
from app.models.institution import Institution


class Course(BaseModel):
    __collection_name__ = "courses"

    title: str = Field(...)
    description: str = Field(...)
    course_url: HttpUrl = Field(...)
    institution: Optional[Union[str, Institution]] = Field(None)
    content: Optional[str] = Field(None, exclude=True)

    # Allow extra fields
    model_config = ConfigDict(extra="allow", from_attributes=True)

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = {},
        sort: Optional[List[tuple]] = None,
    ) -> List[Any]:
        """
        List documents with pagination and optional filtering/sorting

        :param page: Page number for pagination
        :param limit: Number of items per page
        :param filter: Dictionary of filter conditions
        :param sort: List of tuples for sorting (field, direction)
        :return: List of serialized documents
        """
        collection = db.get_collection("courses")
        skip = (page - 1) * limit

        cursor = collection.find(filters).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        documents = await cursor.to_list(length=limit)
        for doc in documents:
            doc["institution"] = await Institution.get(str(doc["institution"]))
        return [cls(**doc) for doc in documents]
