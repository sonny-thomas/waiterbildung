from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core import db
from app.models.institution import Institution
from app.models.schema import EducationalProvider, Schema, SchemaRequest
from app.services.schema import generate_schema
from app.services.utils import fetch_html
from app.services.course import generate_course

router = APIRouter(tags=["scraper"], prefix="/scraper")


@router.post("/generate-schema")
async def generate_schema_endpoint(request: SchemaRequest) -> Schema:
    """Endpoint to generate schema from URL and target fields"""
    try:
        html_content, course_url = await fetch_html(request.course_url)
        target_fields = await generate_schema(
            html_content, request.target_fields
        )
        return {
            "course_url": course_url,
            "target_fields": target_fields.get("fields"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-course")
async def generate_course_from_url(course_url: str):
    """Endpoint to generate schema from URL and target fields"""
    try:
        response = await generate_course(course_url)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape")
async def start_scraping(
    request: Schema, rerun: bool = False
) -> EducationalProvider:
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

