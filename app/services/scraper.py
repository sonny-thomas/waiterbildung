import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from bson import ObjectId
from dotenv import load_dotenv
from openai import OpenAI

from app.core.database import Database

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text(errors="replace")
            else:
                logger.error(
                    f"Failed to retrieve {url}: Status code {response.status}"
                )
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Error accessing {url}: {e}")
        return None


def generate_openai_prompt(course_data):
    info_str = ", \n".join(
        [f"name: {data[0]}, content: {data[1]}" for data in course_data]
    )
    prompt = f"""
    {info_str}

    Please return the formatted course information as a JSON object based
    on the schema provided.
    """
    return prompt


async def extract_course_data(course_data, course_url):
    prompt = generate_openai_prompt(course_data)
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                You are a web scraper, and your task is to extract course
                information from the following HTML content.
                The information should match the schema:

                Schema:
                {
                    "program_name": "string",
                    "degree": "string",
                    "description": "string",
                    "ects_points": "integer",
                    "duration": {
                        "value": "integer",
                        "unit": "string"
                    },
                    "mode_of_study": "string",
                    "teaching_language": "string",
                    "fees": {
                        "application_fee": {
                            "amount": "decimal",
                            "currency": "string"
                        },
                        "tuition_fee": {
                            "local_students": {
                                "amount": "decimal",
                                "currency": "string"
                            },
                            "eu_students": {
                                "amount": "decimal",
                                "currency": "string"
                            },
                            "international_students": {
                                "amount": "decimal",
                                "currency": "string"
                            }
                        }
                    },
                    "program_structure": {
                        "number_of_semesters": "integer",
                        "stay_abroad": "boolean"
                    },
                    "key_dates": {
                        "start_of_semester": "date",
                        "application_open": "date",
                        "application_close": "date"
                    },
                }
                """,
                },
                {"role": "user", "content": prompt},
            ],
        )
        course_data = response.choices[0].message.content
        if not course_data:
            logger.warning(f"Received empty response for {course_url}")
            return None
        try:
            course_data = (
                course_data.replace("```json", "").replace("```", "").strip()
            )
            course_json = json.loads(course_data)
            course_json["url"] = course_url
            return course_json
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {course_url}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error during OpenAI processing: {e}")
        return None


async def scrap_course_data(
    session, url, identifiers, checked_urls, queue, base_url
):
    html = await fetch(session, url)
    if html:
        logger.info(f"Successfully fetched {url}")
        soup = BeautifulSoup(html, "lxml")
        course_data = []
        found_identifiers = 0

        for identifier in identifiers:
            name = identifier["name"]
            type = str(identifier["type"])
            value = identifier["value"]
            if type == "id":
                content = soup.find(id=value)
            elif type == "class":
                content = soup.find(class_=value)
            elif type == "data-init":
                content = soup.find(attrs={"data-init": value})
            if content:
                found_identifiers += 1
                course_data.append((name, content.get_text()))
                logger.info(f"Found element with {type} {value} on {url}")
            else:
                logger.warning(
                    f"Element with {type} {value} not found on {url}"
                )

        len_identifiers = len(identifiers)
        if found_identifiers >= (len_identifiers / 2):
            course_json = await extract_course_data(course_data, url)
            if course_json:
                await Database.get_collection(base_url).insert_one(course_json)
                logger.info(f"Extracted and saved course data from {url}")

        for tag in soup.find_all("a"):
            href = tag.get("href")
            if href:
                full_url = urljoin(url, href.split("#")[0])
                parsed_full_url = urlparse(full_url)
                parsed_base_url = urlparse(base_url)

                if (
                    parsed_full_url.netloc == parsed_base_url.netloc
                    and full_url not in checked_urls
                ):
                    checked_urls.add(full_url)
                    queue.append((full_url, identifiers))
                    logger.info(f"Added to queue: {full_url}")


async def worker(session, queue, checked_urls, base_url):
    while queue:
        try:
            url, identifiers = queue.popleft()
            await scrap_course_data(
                session, url, identifiers, checked_urls, queue, base_url
            )
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")


async def process_url(job):
    base_url = job["base_url"]
    identifiers = job["identifiers"]

    checked_urls = {base_url}
    queue = deque([(base_url, identifiers)])
    logger.info(f"Starting processing for: {base_url}")

    # Create multiple workers to process URLs concurrently
    async with aiohttp.ClientSession(
        timeout=ClientTimeout(total=30)  # Increased timeout
    ) as session:
        num_workers = 5  # Adjust based on your needs
        workers = [
            asyncio.create_task(worker(session, queue, checked_urls, base_url))
            for _ in range(num_workers)
        ]
        await asyncio.gather(*workers)

    logger.info(
        f"Completed processing {base_url}. Total URLs: {len(checked_urls)}"
    )


async def scrape_university(job_id: str) -> Dict[str, Any]:
    await Database.connect_db()
    await Database.get_collection("scraping_jobs").update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "in_progress"}},
    )
    job = await Database.get_collection("scraping_jobs").find_one(
        {"_id": ObjectId(job_id)}
    )

    await process_url(job)

    await Database.get_collection("scraping_jobs").update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )
    return {"status": "completed"}
