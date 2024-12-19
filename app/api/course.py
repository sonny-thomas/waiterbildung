from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.course import Course, CourseList
from app.models.user import User
from app.services.auth import is_user

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/latest", response_model_by_alias=False)
async def get_latest_courses() -> List[Course]:
    """
    Retrieve the latest 9 courses

    - Returns list of the latest 9 serialized courses
    """
    try:
        return await Course.list(page=1, limit=9)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model_by_alias=False)
async def list_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("asc"),
    _=Depends(is_user),
) -> CourseList:
    """
    List courses with optional filtering and pagination

    - Supports pagination
    - Optional filtering by name
    - Optional sorting by a field in ascending or descending order
    - Returns list of serialized courses
    """
    filters = {}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        filters["$or"] = [
            {"name": search_regex},
            {"description": search_regex},
        ]

    sort_order = 1 if sort_order == "asc" else -1
    sort = [(sort_by, sort_order)]

    try:
        return await Course.list(
            page=page, limit=limit, filters=filters, sort=sort
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{course_id}", response_model_by_alias=False)
async def update_course(
    course_id: str,
    course_data: dict,
    _=Depends(is_user),
) -> Course:
    """
    Update a specific course by ID

    - Returns the updated course
    - Returns 404 if course not found
    """
    course = await Course.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in course_data.items():
        setattr(course, key, value)
    await course.save()
    return course


@router.get("/{course_id}", response_model_by_alias=False)
async def get_course(
    course_id: str,
    _=Depends(is_user),
) -> Course:
    """
    Retrieve a specific course by ID

    - Returns 404 if course not found
    """
    course: Course = await Course.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return await course.model_dump()


@router.post("/{course_id}/bookmark")
async def bookmark_course(
    course_id: str,
    user: User = Depends(is_user),
) -> dict:
    """
    Bookmark a specific course by ID

    - Returns a success message if the course is bookmarked
    """
    try:
        course: Course = await Course.get(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        await course.bookmark(user)
        return {"message": "Course bookmarked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
