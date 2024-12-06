from typing import Any, Dict, Optional, Union

from pydantic import ConfigDict, Field, HttpUrl

from app.models import BaseModel, PyObjectId
from app.models.institution import Institution
from app.models.user import User


class Course(BaseModel):
    __collection_name__ = "courses"

    title: str = Field(...)
    description: str = Field(...)
    course_url: HttpUrl = Field(...)
    institution: Optional[Union[PyObjectId, Institution]] = Field(None)
    content: Optional[str] = Field(None, exclude=True)

    # Allow extra fields
    model_config = ConfigDict(extra="allow", from_attributes=True)

    async def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        if self.institution:
            institution: Institution = await Institution.get(self.institution)
            data["institution"] = institution.model_dump()
        return data

    async def bookmark(self, user: User) -> None:
        """
        Bookmark this course for a user

        :param user_id: ID of the user
        """
        user.bookmarked_courses.append(self.id)
        await user.save()
