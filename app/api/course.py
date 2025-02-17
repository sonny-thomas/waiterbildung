from app.models.review import Review
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.middleware import user_is_admin, user_is_active
from app.models.course import Course
from app.models.user import User
from app.schemas import PaginatedRequest, PaginatedResponse

from app.schemas.course import (
    CourseCreate,
    CoursePaginatedRequest,
    CourseResponse,
    CourseUpdate,
    ReviewRequest,
    ReviewResponse,
)

router = APIRouter(prefix="/course", tags=["course"])


@router.post("")
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> CourseResponse:
    """Create a new course"""
    new_course = Course(**course.model_dump())
    new_course.save(db)
    return CourseResponse(**new_course.model_dump())


@router.get("s")
async def get_all_courses(
    pagination: CoursePaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_active),
) -> PaginatedResponse[CourseResponse]:
    """List all courses with pagination"""
    filters = {}
    if pagination.institution_id:
        filters["institution_id"] = pagination.institution_id
    if pagination.degree_type:
        filters["degree_type"] = pagination.degree_type
    if pagination.study_mode:
        filters["study_mode"] = pagination.study_mode
    if pagination.is_featured is not None:
        filters["is_featured"] = pagination.is_featured

    courses, total = Course.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
        use_or=pagination.use_or,
        search=pagination.search,
        **filters
    )
    pages = (total + pagination.size - 1) // pagination.size
    course_data = [CourseResponse(**course.model_dump()) for course in courses]

    return PaginatedResponse(
        data=course_data,
        total=total,
        page=pagination.page,
        pages=pages,
    )


@router.get("/{course_id}")
async def get_course_by_id(
    course_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_active),
) -> CourseResponse:
    """Get a course by ID"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseResponse(**course.model_dump())


@router.put("/{course_id}")
async def update_course(
    course_id: str,
    course: CourseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> CourseResponse:
    """Update a course"""
    existing_course = Course.get(db, id=course_id)
    if not existing_course:
        raise HTTPException(status_code=404, detail="Course not found")

    update_data = {
        k: v for k, v in course.model_dump().items() if v is not None
    }
    updated_course = Course.update(db, course_id, update_data)
    return CourseResponse(**updated_course.model_dump())


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
):
    """Delete a course"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    Course.delete(db, id=course_id)
    return {"message": "Course deleted successfully"}


@router.post("/{course_id}/review")
async def create_review(
    course_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
) -> ReviewResponse:
    """Create a review for a course"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_review = Review(
        **review.model_dump(), user_id=current_user.id, course_id=course_id
    )
    new_review.save(db)
    return ReviewResponse(**new_review.model_dump())


@router.get("/{course_id}/reviews")
async def get_course_reviews(
    course_id: str,
    pagination: PaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_active),
) -> PaginatedResponse[ReviewResponse]:
    """Get all reviews for a course"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    reviews, total = Review.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
        course_id=course_id,
    )
    pages = (total + pagination.size - 1) // pagination.size
    review_data = [ReviewResponse(**review.model_dump()) for review in reviews]

    return PaginatedResponse(
        data=review_data,
        total=total,
        page=pagination.page,
        pages=pages,
    )


@router.post("/{course_id}/bookmark")
async def bookmark_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
) -> dict:
    """Bookmark a course for the current user"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course in current_user.bookmarked_courses:
        raise HTTPException(
            status_code=400, detail="Course already bookmarked"
        )

    current_user.bookmarked_courses.append(course)
    db.commit()
    return {"message": "Course bookmarked successfully"}


@router.delete("/{course_id}/bookmark")
async def remove_bookmark(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
) -> dict:
    """Remove a course bookmark for the current user"""
    course = Course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course not in current_user.bookmarked_courses:
        raise HTTPException(status_code=400, detail="Course not bookmarked")

    current_user.bookmarked_courses.remove(course)
    db.commit()
    return {"message": "Bookmark removed successfully"}
