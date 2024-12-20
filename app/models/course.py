from typing import Any, Dict, Optional, Union, List

from pydantic import ConfigDict, Field, HttpUrl, BaseModel as PydanticBaseModel

from app.models import BaseModel, PyObjectId
from app.models.institution import Institution
from app.models.user import User

# from app.models.review import Review  # Assuming you have a Review model


class Course(BaseModel):
    __collection_name__ = "courses"

    title: str = Field(description="The title of the course.")
    description: str = Field(
        description="Course description in 1-2 sentences."
    )
    diploma: str = Field(description="The diploma of the course.")
    degree: Optional[str] = Field(
        default="",
        description="Degree of the course ('Master', 'Bachelor', or empty string).",
    )
    teaching_language: Optional[str] = Field(
        default="", description="Teaching language of the course."
    )
    ects_points: Optional[int] = Field(
        default=None, description="ECTS points of the course."
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
        default="",
        description="Studying mode ('full-time', 'part-time', 'online', 'offline').",
    )
    duration: Optional[str] = Field(
        default="", description="Duration of the course."
    )
    semester_fee: Optional[str] = Field(
        default="", description="The semester fee of the course."
    )
    abroad_available: Optional[bool] = Field(
        default=False,
        description="Whether studying abroad is available (True/False).",
    )
    is_featured: Optional[bool] = Field(
        default=False, description="Whether the course is featured."
    )
    rating: Optional[float] = Field(
        default=0.0, description="The rating of the course."
    )
    course_url: HttpUrl = Field(...)
    institution: Optional[Union[PyObjectId, Institution]] = Field(None)
    content: Optional[str] = Field(None, exclude=True)
    # reviews: Optional[List[Review]] = Field(
    #     default=[], description="List of reviews for the course."
    # )

    model_config = ConfigDict(extra="allow", from_attributes=True)

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filters: Optional[dict] = None,
        sort: Optional[List[tuple]] = None,
    ) -> dict:
        documents, total = await super().list(page, limit, filters or {}, sort)
        courses = []
        for doc in documents:
            if doc.institution:
                institution = await Institution.get(doc.institution)
                if institution:
                    doc.institution = institution
            courses.append(doc)
        return CourseList(
            courses=courses, total=total, page=page, size=limit
        )

    async def bookmark(self, user: User) -> None:
        """
        Bookmark this course for a user

        :param user_id: ID of the user
        """
        user.bookmarked_courses.append(self.id)
        await user.save()


class CourseList(PydanticBaseModel):
    courses: List[Course] = Field(
        default=[], description="The list of courses."
    )
    total: int = Field(description="The total number of courses available.")
    page: int = Field(default=1, description="The current page number.")
    size: int = Field(
        default=10, description="The number of courses per page."
    )
