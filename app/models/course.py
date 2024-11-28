from typing import Any, Optional, Union

from pydantic import ConfigDict, Field, HttpUrl

from app.models import BaseModel
from app.models.institution import Institution


class Course(BaseModel):
    _collection_name = "courses"

    title: str = Field(...)
    description: str = Field(...)
    course_url: HttpUrl = Field(...)
    institution: Optional[Union[str, Institution]] = Field(None)
    content: Optional[str] = Field(None, exclude=True)

    # Allow extra fields
    model_config = ConfigDict(extra="allow", from_attributes=True)

    @classmethod
    async def serialize(cls, courses: Any) -> Any:
        courses = await super().serialize(courses)
        if isinstance(courses, dict):
            if isinstance(courses.get("institution"), str):
                courses["institution"] = await Institution.get(courses["institution"])
        elif isinstance(courses, list):
            for course in courses:
                if isinstance(course.get("institution"), str):
                    course["institution"] = await Institution.get(course["institution"])
        return courses
