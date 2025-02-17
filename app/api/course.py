from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.middleware import user_is_admin, user_is_instructor
from app.models.course import Course
from app.models.user import User
from app.schemas import PaginatedResponse

from app.schemas.course import (
    CourseCreate,
    CoursePaginatedRequest,
    CourseResponse,
    CourseUpdate,
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
    _: User = Depends(user_is_instructor),
) -> PaginatedResponse[CourseResponse]:
    """List all courses with pagination"""
    filters = {}
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
    _: User = Depends(user_is_instructor),
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
