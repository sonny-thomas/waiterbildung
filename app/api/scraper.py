from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_admin, user_is_instructor
from app.core.queue import scraper_queue
from app.core.scraper import Crawler, scrape_courses
from app.core.utils import get_domain
from app.models.institution import Institution
from app.models.user import User
from app.schemas import PaginatedRequest
from app.schemas.institution import (
    AddInstitution,
    CrawlInstitution,
    InstitutionResponse,
    ScrapeInstitution,
    ScraperStatus,
    UpdateInstitution,
)

router = APIRouter(prefix="/institution", tags=["institution"])


@router.get("s")
async def list_institutions(
    filter: PaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> list[InstitutionResponse]:
    """List all institutions with pagination"""
    institutions = Institution.get_all(
        db,
        skip=filter.skip,
        limit=filter.limit,
        sort_by=filter.sort_by,
        descending=filter.descending,
        use_or=filter.use_or,
    )
    return [
        InstitutionResponse(**institution.model_dump())
        for institution in institutions
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


@router.post("")
async def add_institution(
    data: AddInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Add a new institution"""
    if Institution.get(db, domain=data.domain):
        raise HTTPException(
            status_code=400,
            detail=f"Institution with domain {data.domain} already exists",
        )

    institution = Institution(**data.model_dump())
    institution.save(db)
    return InstitutionResponse(**institution.model_dump())


@router.put("/{institution_id}")
async def update_institution(
    institution_id: str,
    data: UpdateInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    """Update an institution by ID"""
    institution = Institution.get(db, id=institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(institution, key, value)

    institution.save(db)
    return InstitutionResponse(**institution.model_dump())


@router.post("/crawl")
async def crawl_institution(
    request: CrawlInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Crawl an institution for courses"""
    institution = Institution.get(db, id=request.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.scraper_status.value in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper is currently {institution.scraper_status.value} for this institution.",
        )
    if get_domain(str(request.start_url)) != institution.domain:
        raise HTTPException(
            status_code=400,
            detail="URL domain does not match institution domain.",
        )

    scraper = Crawler(institution.id, institution.domain, request)
    scraper_queue.enqueue(scraper.crawl, job_timeout=3600)

    institution.scraper_status = ScraperStatus.queued
    institution.save(db)

    return InstitutionResponse(**institution.model_dump())


@router.post("/scrape")
async def scrape_institution_courses(
    request: ScrapeInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Scrape courses for an institution by ID"""
    institution = Institution.get(db, id=request.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.scraper_status.value in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper is currently {institution.scraper_status.value} for this institution.",
        )

    for url in request.course_urls:
        if get_domain(str(url)) != institution.domain:
            raise HTTPException(
                status_code=400,
                detail=f"URL domain {get_domain(str(url))} does not match institution domain: {institution.domain}",
            )
    scraper_queue.enqueue(
        scrape_courses,
        institution.id,
        request.course_urls,
        request.hero_image_selector,
    )

    institution.scraper_status = ScraperStatus.queued
    institution.save(db)

    return InstitutionResponse(**institution.model_dump())
