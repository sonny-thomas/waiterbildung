from fastapi import logger
from app import celery
from app.services.scraper import UniversityScraperService
from app.core.database import Database
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any
import traceback


@celery.task(name="scrape_university_courses")
def scrape_university_courses(
    self, job_id: str, university_url: str
) -> Dict[str, Any]:
    """
    Celery task to scrape university courses.

    Args:
        job_id (str): The ID of the scraping job
        university_url (str): The URL of the university to scrape

    Returns:
        Dict containing the job results
    """
    logger.info(f"Starting scraping job {job_id} for {university_url}")

    try:
        # Update job status to in-progress
        _update_job_status(job_id, "in_progress")

        # Initialize scraper service
        scraper = UniversityScraperService()

        # Start scraping
        courses = scraper.scrape_courses(university_url)

        # Process and store the results
        total_courses = _process_scraping_results(courses, university_url)

        # Update job as completed
        _update_job_status(
            job_id,
            "completed",
            total_courses=total_courses,
            completed_at=datetime.utcnow(),
        )

        logger.info(
            f"Completed scraping job {job_id} with {total_courses} courses"
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "total_courses": total_courses,
            "university": university_url,
        }

    except Exception as exc:
        error_msg = (
            f"Error in scraping job: {str(exc)}\n{traceback.format_exc()}"
        )
        logger.error(error_msg)

        # Handle different types of errors
        if "Connection refused" in str(exc):
            retry_delay = (
                self.request.retries * 60
            )  # Progressive delay: 60s, 120s, 180s
            try:
                raise self.retry(countdown=retry_delay, exc=exc)
            except self.MaxRetriesExceededError:
                _update_job_status(
                    job_id,
                    "failed",
                    error_message="Maximum retry attempts exceeded",
                )
        else:
            _update_job_status(job_id, "failed", error_message=str(exc))

        raise


async def _update_job_status(
    job_id: str,
    status: str,
    total_courses: Optional[int] = None,
    completed_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Update the status of a scraping job in the database.
    """
    update_data = {"status": status}

    if total_courses is not None:
        update_data["total_courses"] = total_courses
    if completed_at is not None:
        update_data["completed_at"] = completed_at
    if error_message is not None:
        update_data["error_message"] = error_message

    try:
        await Database.get_collection("scraping_jobs").update_one(
            {"_id": ObjectId(job_id)}, {"$set": update_data}
        )
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        raise


async def _process_scraping_results(courses: list, university_url: str) -> int:
    """
    Process and store scraped courses in the database.

    Args:
        courses (list): List of scraped courses
        university_url (str): URL of the university

    Returns:
        int: Number of courses processed
    """
    if not courses:
        return 0

    try:
        # Prepare courses for insertion
        for course in courses:
            course["university"] = university_url
            course["created_at"] = datetime.utcnow()

        # Insert courses in bulk
        result = await Database.get_collection("courses").insert_many(courses)
        return len(result.inserted_ids)

    except Exception as e:
        logger.error(f"Error processing scraping results: {e}")
        raise
