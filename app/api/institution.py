from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.models.institution import Institution, InstitutionList
from app.services.auth import is_user

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.post("", response_model_by_alias=False)
async def create_institution(
    institution_data: dict,
    _=Depends(is_user),
) -> Institution:
    """
    Create a new institution

    - Requires user authentication
    - Returns the created institution
    """
    institution = Institution(**institution_data)
    await institution.save()
    return institution


@router.get("", response_model_by_alias=False)
async def list_institutions(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("asc"),
    _=Depends(is_user),
) -> InstitutionList:
    """
    List institutions with optional filtering and pagination

    - Supports pagination
    - Optional filtering by:
      * search (partial match on name, description)
      * is_active status
    - Optional sorting by a field in ascending or descending order
    - Returns list of serialized institutions
    """
    filters = {}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        filters["$or"] = [
            {"name": search_regex},
            {"description": search_regex},
        ]
    if is_active is not None:
        filters["is_active"] = is_active

    sort_order = 1 if sort_order == "asc" else -1
    sort = [(sort_by, sort_order)]

    try:
        return await Institution.list(
            page=page, limit=size, filters=filters, sort=sort
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{institution_id}", response_model_by_alias=False)
async def update_institution(
    institution_id: str,
    institution_data: dict,
    _=Depends(is_user),
) -> Institution:
    """
    Update an institution by ID

    - Requires user authentication
    - Returns 404 if institution not found
    - Returns the updated institution
    """
    institution = await Institution.get(institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    for key, value in institution_data.items():
        setattr(institution, key, value)
    await institution.save()
    return institution


@router.get("/{institution_id}")
async def get_institution(
    institution_id: str, _=Depends(is_user)
) -> Institution:
    """
    Retrieve a specific institution by ID

    - Returns 404 if institution not found
    """
    institution = await Institution.get(institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution
