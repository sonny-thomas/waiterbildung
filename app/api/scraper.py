from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import db
from app.models.institution import Institution
from app.models.schema import EducationalProvider, Schema, SchemaRequest
from app.services.extraction import extract_data_from_html
from app.services.schema import generate_schema
from app.services.utils import fetch_html

router = APIRouter(tags=["scraper"], prefix="/scraper")


@router.post("/generate-schema")
async def generate_schema_endpoint(request: SchemaRequest) -> Schema:
    """Endpoint to generate schema from URL and target fields"""
    try:
        html_content, course_url = await fetch_html(request.course_url)
        target_fields = await generate_schema(html_content, request.target_fields)
        return {"course_url": course_url, "target_fields": target_fields.get("fields")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape-page")
async def scrape_course_page(request: Schema) -> dict:
    """Endpoint to scrape a single course page using a schema"""
    try:
        html_content, _ = await fetch_html(request.course_url)
        data = await extract_data_from_html(html_content, request.target_fields)
        if data:
            return data
        raise HTTPException(status_code=400, detail="Failed to extract data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape")
async def start_scraping(request: Schema, rerun: bool = False) -> EducationalProvider:
    """Start a new scraping job for a university."""
    from app.tasks.scraper_tasks import scrape_university_courses

    async with aiohttp.ClientSession() as session:
        async with session.get(
            str(request.course_url), allow_redirects=True
        ) as response:
            parsed_url = urlparse(str(response.url))
            if parsed_url.scheme != "https":
                raise HTTPException(
                    status_code=400, detail="URL must use https protocol"
                )
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    institutions = db.get_collection("institutions")

    institution = await institutions.find_one({"base_url": base_url})

    if institution and not rerun:
        institution["id"] = str(institution["_id"])
        institution["message"] = (
            f"Job already exists with status: {institution['status']}"
        )
        return Institution(**institution)

    if institution and rerun:
        # cancel_task(university["task_id"])
        pass

    data = {
        "$setOnInsert": {"_id": ObjectId()},
        "$set": {
            "status": "pending",
            "base_url": base_url,
            "target_fields": request.target_fields,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
            "courses_scraped": None,
        },
    }

    university = await institutions.find_one_and_update(
        {"base_url": base_url}, data, upsert=True, return_document=True
    )

    task = scrape_university_courses.delay(str(university["_id"]))

    await institutions.update_one(
        {"_id": university["_id"]}, {"$set": {"task_id": task.id}}
    )

    university["id"] = str(university["_id"])
    university["task_id"] = task.id
    university["message"] = "Scraping job started successfully."

    return EducationalProvider(**university)


# @router.get("/jobs", response_model=List[ScrapingJob])
# async def list_jobs():
#     """List all scraping jobs."""
#     jobs = await Database.get_collection("scraping_jobs").find().to_list(length=None)
#     return [ScrapingJob(id=str(job["_id"]), **job) for job in jobs]


# @router.get("/job", response_model=ScrapingJob)
# async def get_job(job_id: str = None, url: str = None):
#     """Get details of a scraping job by its ID or URL."""
#     if job_id:
#         job = await Database.get_collection("scraping_jobs").find_one(
#             {"_id": ObjectId(job_id)}
#         )
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
#         return ScrapingJob(id=str(job["_id"]), **job)

#     if url:
#         parsed_url = urlparse(url)
#         base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
#         job = await Database.get_collection("scraping_jobs").find_one(
#             {"base_url": base_url}
#         )
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
#         return ScrapingJob(id=str(job["_id"]), **job)

#     raise HTTPException(status_code=400, detail="Either job_id or url must be provided")


# @router.get("/courses/{url}", response_model=List[dict])
# async def list_courses(url: str):
#     """List all courses for a university."""
#     parsed_url = urlparse(url)
#     base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
#     courses = []
#     for collection in await Database.list_collection_names():
#         if collection != "scraping_jobs":
#             collection_courses = (
#                 await Database.get_collection(collection)
#                 .find({"base_url": base_url})
#                 .to_list(length=None)
#             )
#             courses.extend(collection_courses)
#     for course in courses:
#         course["id"] = str(course["_id"])
#     return [course for course in courses]


# @router.get("/universities", response_model=List[str])
# async def list_universities():
#     """List all universities."""
#     collections = await Database.list_collection_names()
#     return [collection for collection in collections if collection != "scraping_jobs"]


# @router.get("/course/{course_id}", response_model=dict)
# async def get_course(course_id: str):
#     """Get details of a course by its ID."""
#     for collection in await Database.list_collection_names():
#         if collection != "scraping_jobs":
#             course = await Database.get_collection(collection).find_one(
#                 {"_id": ObjectId(course_id)}
#             )
#             if course:
#                 course["id"] = str(course["_id"])
#                 return course
#     raise HTTPException(status_code=404, detail="Course not found")
