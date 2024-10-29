from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse

import aiohttp
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import Database
from app.models.course import ScrapingJob, ScrapingRequest

router = APIRouter(tags=["scraper"])


@router.post("/scrape", response_model=ScrapingJob)
async def start_scraping(scraping_request: ScrapingRequest, force: bool = False):
    """Start a new scraping job for a university."""
    from app.tasks.scraper_tasks import scrape_university_courses

    async with aiohttp.ClientSession() as session:
        async with session.get(
            str(scraping_request.course_url), allow_redirects=True
        ) as response:
            parsed_url = urlparse(str(response.url))
            if parsed_url.scheme != "https":
                raise HTTPException(
                    status_code=400, detail="URL must use https protocol"
                )
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    existing_job = await Database.get_collection("scraping_jobs").find_one(
        {"base_url": base_url}
    )
    if existing_job and not force:
        existing_job["id"] = str(existing_job["_id"])
        existing_job["message"] = (
            f"Job already exists with status: {existing_job['status']}"
        )
        return ScrapingJob(**existing_job)

    job = {
        "_id": ObjectId(),
        "status": "pending",
        "base_url": base_url,
        "course_url": str(scraping_request.course_url),
        "target_fields": scraping_request.target_fields,
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
        "courses_scraped": None,
        "message": None,
    }

    await Database.get_collection("scraping_jobs").insert_one(job)

    scrape_university_courses.delay(str(job["_id"]))

    return ScrapingJob(id=str(job["_id"]), **job)


@router.get("/jobs", response_model=List[ScrapingJob])
async def list_jobs():
    """List all scraping jobs."""
    jobs = await Database.get_collection("scraping_jobs").find().to_list(length=None)
    return [ScrapingJob(id=str(job["_id"]), **job) for job in jobs]


@router.get("/job", response_model=ScrapingJob)
async def get_job(job_id: str = None, url: str = None):
    """Get details of a scraping job by its ID or URL."""
    if job_id:
        job = await Database.get_collection("scraping_jobs").find_one(
            {"_id": ObjectId(job_id)}
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return ScrapingJob(id=str(job["_id"]), **job)

    if url:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        job = await Database.get_collection("scraping_jobs").find_one(
            {"base_url": base_url}
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return ScrapingJob(id=str(job["_id"]), **job)

    raise HTTPException(status_code=400, detail="Either job_id or url must be provided")


@router.get("/courses/{url}", response_model=List[dict])
async def list_courses(url: str):
    """List all courses for a university."""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    courses = []
    for collection in await Database.list_collection_names():
        if collection != "scraping_jobs":
            collection_courses = await Database.get_collection(collection).find({"base_url": base_url}).to_list(length=None)
            courses.extend(collection_courses)
    for course in courses:
        course["id"] = str(course["_id"])
    return [course for course in courses]


@router.get("/universities", response_model=List[str])
async def list_universities():
    """List all universities."""
    collections = await Database.list_collection_names()
    return [collection for collection in collections if collection != "scraping_jobs"]


@router.get("/course/{course_id}", response_model=dict)
async def get_course(course_id: str):
    """Get details of a course by its ID."""
    for collection in await Database.list_collection_names():
        if collection != "scraping_jobs":
            course = await Database.get_collection(collection).find_one(
                {"_id": ObjectId(course_id)}
            )
            if course:
                course["id"] = str(course["_id"])
                return course
    raise HTTPException(status_code=404, detail="Course not found")
