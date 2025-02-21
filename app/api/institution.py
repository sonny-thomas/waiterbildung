from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_admin
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
    try:
        if Institution.get(db, domain=institution.domain):
            raise HTTPException(
                status_code=400,
                detail=f"Institution with domain {institution.domain} already exists",
            )

        new_institution = Institution(**institution.model_dump())
        new_institution.save(db)
        return InstitutionResponse(**new_institution.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("s")
async def get_all_institutions(
    pagination: InstitutionPaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> PaginatedResponse[InstitutionResponse]:
    """List all institutions with pagination"""
    try:
        filters = {}
        if pagination.scraping_status:
            filters["scraping_status"] = pagination.scraping_status
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{institution_id}")
async def get_institution_by_id(
    institution_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Get an institution by ID"""
    try:
        institution = Institution.get(db, id=institution_id)
        if not institution:
            raise HTTPException(
                status_code=404, detail="Institution not found"
            )

        return InstitutionResponse(**institution.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{institution_id}")
async def update_institution(
    institution_id: str,
    institution: InstitutionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Update an institution"""
    try:
        existing_institution = Institution.get(db, id=institution_id)
        if not existing_institution:
            raise HTTPException(
                status_code=404, detail="Institution not found"
            )
        institution_data = institution.model_dump(exclude_unset=True)
        for key, value in institution_data.items():
            setattr(existing_institution, key, value)
        existing_institution.save(db)
        return InstitutionResponse(**existing_institution.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{institution_id}")
async def delete_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
):
    """Delete an institution"""
    try:
        institution = Institution.get(db, id=institution_id)
        if not institution:
            raise HTTPException(
                status_code=404, detail="Institution not found"
            )

        institution.delete(db)
        return {"message": "Institution deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
