import tldextract
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_instructor
from app.core.queue import scraper_queue
from app.models.institution import Institution
from app.models.user import User
from app.schemas import PaginatedRequest
from app.schemas.institution import (
    InstitutionResponse,
    ScrapeInstitution,
    ScraperStatus,
)

router = APIRouter(prefix="/institution", tags=["institutions"])


@router.get("s")
async def get_institutions(
    filter: PaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> list[InstitutionResponse]:
    """Get all institutions with pagination"""
    institutions = Institution.get_all(
        db,
        skip=filter.skip,
        limit=filter.limit,
        sort_by=filter.sort_by,
        descending=filter.descending,
        use_or=filter.use_or,
    )
    return [
        InstitutionResponse(**institution.model_dump()) for institution in institutions
    ]


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


@router.post("/scrape")
async def run_scraper(
    request: ScrapeInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Run the web scraper with the provided URL and selector"""
    domain = tldextract.extract(str(request.start_url)).registered_domain
    institution = Institution.get(db, domain=domain)
    if institution is None:
        institution = Institution(
            name=request.name, domain=domain, logo=str(request.logo)
        )
    elif institution.scraper_status.value in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper is currently {institution.scraper_status.value} for this institution.",
        )
    institution.scraper_status = ScraperStatus.queued
    institution.save(db)

    scraper_queue.enqueue(
        institution.scrape_courses,
        domain,
        str(request.start_url),
        request.course_selector,
        request.hero_image_selector,
        request.max_courses,
    )

    return InstitutionResponse(**institution.model_dump())
