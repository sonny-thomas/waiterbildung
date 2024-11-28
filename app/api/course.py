from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models.course import Course

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/")
async def list_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> List[Course]:
    """
    List courses with optional filtering and pagination

    - Supports pagination
    - Optional filtering by name
    - Returns list of serialized courses
    """
    # Prepare filter
    filter_params = {}

    try:
        courses = await Course.list(page=page, limit=limit, filter=filter_params)
        return courses
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{course_id}")
async def get_course(course_id: str) -> Course:
    """
    Retrieve a specific course by ID

    - Returns 404 if course not found
    """
    course = await Course.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
