from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_admin
from app.core.queue import scraper_queue
from app.core.scraper import Crawler, scrape_courses
from app.core.utils import get_domain
from app.models.institution import Institution
from app.models.user import User
from app.schemas.scraper import (
    CrawlInstitution,
    ScrapeInstitution,
    ScraperStatus,
)

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/crawl")
async def crawl_institution(
    request: CrawlInstitution,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_admin),
) -> str:
    """Crawl an institution for courses"""
    institution = Institution.get(db, id=request.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.status.value in ["queued", "in_progress"]:
        raise HTTPException(
            status_code=400,
            detail=f"Scraper is currently {institution.status.value} for this institution.",
        )
    if get_domain(str(request.start_url)) != institution.domain:
        raise HTTPException(
            status_code=400,
            detail="URL domain does not match institution domain.",
        )

    scraper = Crawler(institution.id, institution.domain, request)
    scraper_queue.enqueue(scraper.crawl, job_timeout=3600)

    institution.status = ScraperStatus.queued
    institution.save(db)

    return f"Crawler queued for institution {institution.id}"


# @router.post("/scrape")
# async def scrape_institution_courses(
#     request: ScrapeInstitution,
#     db: Session = Depends(get_db),
#     _: User = Depends(user_is_admin),
# ) -> InstitutionResponse:
#     """Scrape courses for an institution by ID"""
#     institution = Institution.get(db, id=request.institution_id)
#     if not institution:
#         raise HTTPException(status_code=404, detail="Institution not found")
#     if institution.status.value in ["queued", "in_progress"]:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Scraper is currently {institution.status.value} for this institution.",
#         )

#     for url in request.course_urls:
#         if get_domain(str(url)) != institution.domain:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"URL domain {get_domain(str(url))} does not match institution domain: {institution.domain}",
#             )
#     scraper_queue.enqueue(
#         scrape_courses,
#         institution.id,
#         request.course_urls,
#         request.hero_image_selector,
#     )

#     institution.status = ScraperStatus.queued
#     institution.save(db)

#     return InstitutionResponse(**institution.model_dump())
