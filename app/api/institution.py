from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_admin, user_is_instructor
from app.core.queue import scraper_queue
from app.core.scraper import Crawler, scrape_courses, scrape_course
from app.models.institution import Institution
from app.models.user import User
from app.schemas import PaginatedRequest
from app.schemas.institution import (
    InstitutionResponse,
    ScrapeInstitution,
    ScraperStatus,
    AddInstitution,
    ScrapeInstitutionCourses,
)
from app.schemas.course import CourseResponse, ScrapeCourse
from app.core.utils import get_domain

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


@router.post("")
async def add_institution(
    data: AddInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> InstitutionResponse:
    institution = Institution(**data.model_dump())
    institution.save(db)
    return InstitutionResponse(**institution.model_dump())


@router.post("/{institution_id}/scrape")
async def scrape_institution(
    institution_id: str,
    request: ScrapeInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Scrape an institution by ID"""
    institution = Institution.get(db, id=institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.scraper_status.value in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper is currently {institution.scraper_status.value} for this institution.",
        )
    if get_domain(str(request.start_url)) != institution.domain:
        raise HTTPException(
            status_code=400, detail="URL domain does not match institution domain."
        )

    scraper = Crawler(institution.id, institution.domain, request)
    scraper_queue.enqueue(scraper.crawl, timeout=3600)

    institution.scraper_status = ScraperStatus.queued
    institution.save(db)

    return InstitutionResponse(**institution.model_dump())


@router.post("/{institution_id}/courses")
async def scrape_institution_courses(
    institution_id: str,
    request: ScrapeInstitutionCourses,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_instructor),
) -> InstitutionResponse:
    """Scrape courses for an institution by ID"""
    institution = Institution.get(db, id=institution_id)
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
        scrape_courses, institution.id, request.course_urls, request.hero_image_selector
    )

    institution.scraper_status = ScraperStatus.queued
    institution.save(db)

    return InstitutionResponse(**institution.model_dump())


@router.post("/scrape_single_course")
async def scrape_single_course(
    course_url: str,
    course_selector: str | None = None,
    hero_image_selector: str | None = None,
    _: User = Depends(user_is_instructor),
) -> ScrapeCourse:
    """Scrape a single course from a URL"""
    course = await scrape_course(course_url, course_selector, hero_image_selector)
    if not course:
        raise HTTPException(status_code=404, detail="Could not parse course from URL")
    return ScrapeCourse(**course.model_dump())
