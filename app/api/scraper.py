from fastapi import APIRouter, HTTPException
from typing import List
from app.models.course import Course, ScrapingJob
from app.core.database import Database
from app.tasks.scraper_tasks import scrape_university_courses
from bson import ObjectId
from datetime import datetime

router = APIRouter()


@router.post("/scrape", response_model=ScrapingJob)
async def start_scraping(university_url: str):
    """Start a new scraping job for a university."""
    job_id = str(ObjectId())

    # Create a new job record
    job = {
        "_id": ObjectId(job_id),
        "status": "pending",
        "university": university_url,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "total_courses": None,
        "error_message": None,
    }

    await Database.get_collection("scraping_jobs").insert_one(job)

    # Start Celery task
    scrape_university_courses.delay(job_id, university_url)

    return ScrapingJob(
        id=job_id,
        status="pending",
        university=university_url,
        created_at=job["created_at"],
        completed_at=None,
        total_courses=None,
        error_message=None,
    )


@router.get("/jobs/{job_id}", response_model=ScrapingJob)
async def get_job_status(job_id: str):
    """Get the status of a scraping job."""
    job = await Database.get_collection("scraping_jobs").find_one(
        {"_id": ObjectId(job_id)}
    )
    if not job:
        raise HTTPException(status_code=404, message="Job not found")

    return ScrapingJob(
        id=str(job["_id"]),
        status=job["status"],
        university=job["university"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        total_courses=job["total_courses"],
        error_message=job["error_message"],
    )


@router.get("/courses", response_model=List[Course])
async def get_courses(university: str = None, skip: int = 0, limit: int = 100):
    """Get list of scraped courses with optional university filter."""
    query = {"university": university} if university else {}

    courses = (
        await Database.get_collection("courses")
        .find(query)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    return [Course(**course) for course in courses]
