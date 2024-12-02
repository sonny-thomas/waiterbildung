from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List

from app.models.institution import Institution
from app.services.auth import is_user

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("")
async def list_institutions(
    page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100), _=Depends(is_user)
) -> List[Institution]:
    """
    List institutions with optional filtering and pagination

    - Supports pagination
    - Optional filtering by name
    - Returns list of serialized institutions
    """
    try:
        institutions = await Institution.list(page=page, limit=limit)
        return institutions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{institution_id}")
async def get_institution(institution_id: str, _=Depends(is_user)) -> Institution:
    """
    Retrieve a specific institution by ID

    - Returns 404 if institution not found
    """
    institution = await Institution.get(institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution
