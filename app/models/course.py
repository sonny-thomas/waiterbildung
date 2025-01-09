from typing import Optional, Union, List

from pydantic import Field, HttpUrl, BaseModel as PydanticBaseModel

from app.models import BaseModel, PyObjectId
from app.models.institution import Institution
from app.models.user import User


class Review(BaseModel):
    user: User = Field(...)
    comment: str = Field(...)
    rating: float = Field(...)


class AddReview(PydanticBaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default=None)


class Course(BaseModel):
    __collection_name__ = "courses"

    title: str = Field(description="The title of the course.")
    description: str = Field(
        description="Course description in 1-2 sentences."
    )
    diploma: str = Field(description="The diploma of the course.")
    degree: Optional[str] = Field(
        default="",
        description="Degree of the course ('Master', 'Bachelor', 'PhD' or 'Other').",
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
        default=False,
        description="Whether the course is featured or not. Default is False.",
    )
    reviews: Optional[List[Union[Review]]] = Field(
        default=[], description="List of reviews for the course."
    )
    rating: Optional[float] = Field(
        default=0.0, description="The rating of the course. Default is 0.0."
    )
    course_url: HttpUrl = Field(..., description="The URL of the course.")
    institution: Optional[Union[PyObjectId, Institution]] = Field(None)
    content: Optional[str] = Field(None, exclude=True)

    async def bookmark(self, user: User) -> None:
        """
        Bookmark this course for a user

        :param user: The user who wants to bookmark the course
        """
        user.bookmarked_courses.append(self.id)
        await user.save()

    async def review(self, user: User, rating: float, comment: str) -> None:
        """
        Review this course for a user. Only one review per user is allowed.

        :param user_id: ID of the user
        :param rating: Rating of the course
        :param comment: comment of the review
        """
        existing_review = next(
            (r for r in self.reviews if r.user.id == user.id), None
        )

        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
        else:
            review = Review(
            user=user,
            rating=rating,
            comment=comment,
            )
            self.reviews.append(review)

        self.rating = sum(r.rating for r in self.reviews) / len(self.reviews)
        await self.save()


class CourseList(PydanticBaseModel):
    courses: List[Course] = Field(
        default=[], description="The list of courses."
    )
    total: int = Field(description="The total number of courses available.")
    page: int = Field(default=1, description="The current page number.")
    size: int = Field(
        default=10, description="The number of courses per page."
    )
