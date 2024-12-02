from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.course import Course
from app.services.auth import is_user

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/latest")
async def get_latest_courses() -> List[Course]:
    """
    Retrieve the latest 9 courses

    - Returns list of the latest 9 serialized courses
    """
    try:
        courses = await Course.list(page=1, limit=9)
        return courses
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _=Depends(is_user),
) -> List[Course]:
    """
    List courses with optional filtering and pagination

    - Supports pagination
    - Optional filtering by name
    - Returns list of serialized courses
    """
    try:
        courses = await Course.list(page=page, limit=limit)
        return courses
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{course_id}")
async def get_course(
    course_id: str,
    _=Depends(is_user),
) -> Course:
    """
    Retrieve a specific course by ID

    - Returns 404 if course not found
    """
    course = await Course.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
