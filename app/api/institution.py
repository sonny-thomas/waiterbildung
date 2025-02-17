from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_admin, user_is_instructor
from app.models.institution import Institution
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionPaginatedRequest,
    InstitutionResponse,
    InstitutionUpdate,
)

router = APIRouter(prefix="/institution", tags=["institution"])


@router.post("")
async def create_institution(
    institution: InstitutionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Create a new institution"""
    if Institution.get(db, domain=institution.domain):
        raise HTTPException(
            status_code=400,
            detail=f"Institution with domain {institution.domain} already exists",
        )

    new_institution = Institution(**institution.model_dump())
    new_institution.save(db)
    return InstitutionResponse(**new_institution.model_dump())


@router.get("s")
async def get_all_institutions(
    pagination: InstitutionPaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> PaginatedResponse[InstitutionResponse]:
    """List all institutions with pagination"""
    filters = {}
    if pagination.status:
        filters["status"] = pagination.status
    if pagination.is_active is not None:
        filters["is_active"] = pagination.is_active
    institutions, total = Institution.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
        use_or=pagination.use_or,
        search=pagination.search,
    )
    pages = (total + pagination.size - 1) // pagination.size
    institution_data = [
        InstitutionResponse(**inst.model_dump()) for inst in institutions
    ]

    return PaginatedResponse(
        data=institution_data,
        total=total,
        page=pagination.page,
        pages=pages,
    )


@router.get("/{institution_id}")
async def get_institution_by_id(
    institution_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Get an institution by ID"""
    institution = Institution.get(db, id=institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    return InstitutionResponse(**institution.model_dump())


@router.put("/{institution_id}")
async def update_institution(
    institution_id: str,
    institution: InstitutionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Update an institution"""
    existing_institution = Institution.get(db, id=institution_id)
    if not existing_institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    updated_institution = Institution.update(
        db, institution_id, institution.model_dump()
    )
    return InstitutionResponse(**updated_institution.model_dump())


@router.delete("/{institution_id}")
async def delete_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
):
    """Delete an institution"""
    institution = Institution.get(db, id=institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    Institution.delete(db, id=institution_id)
    return {"message": "Institution deleted successfully"}
