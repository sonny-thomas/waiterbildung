import asyncio
from typing import Any, Dict

from app import celery
from app.services.scraper import scrape_university


@celery.task(name="scrape_university_courses")
def scrape_university_courses(job_id: str) -> Dict[str, Any]:
    """
    Celery task to scrape university courses.

    Args:
        job_id (str): The ID of the scraping job.

    Returns:
        Dict[str, Any]: A dictionary containing the job results.
    """
    return asyncio.run(scrape_university(job_id))
