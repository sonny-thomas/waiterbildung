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


# Define the Course schema
class DefaultCourse(BaseModel):
    """Default Course schema to structure the response."""
    title: str = Field(description="The title of the course.")
    description: str = Field(description="Course description in 1-2 sentences.")
    diploma: str = Field(description="The diploma of the course.")
    degree: Optional[str] = Field(
        default="", description="Degree of the course ('Master', 'Bachelor', or empty string)."
    )
    teaching_language: Optional[str] = Field(
        default="", description="Teaching language of the course."
    )
    etcs_points: Optional[int] = Field(
        default=None, description="ETCS points of the course."
    )
    place: Optional[str] = Field(
        default="", description="The location where the course is conducted."
    )
    start_date: Optional[str] = Field(
        default="", description="The start date of the course."
    )
    end_date: Optional[str] = Field(
        default="", description="The end date of the course."
    )
    studying_mode: Optional[str] = Field(
        default="", description="Studying mode ('full-time', 'part-time', 'online', 'offline')."
    )
    duration: Optional[str] = Field(
        default="", description="Duration of the course."
    )
    semester_fee: Optional[str] = Field(
        default="", description="The semester fee of the course."
    )
    abroad_available: Optional[bool] = Field(
        default=False, description="Whether studying abroad is available (True/False)."
    )
