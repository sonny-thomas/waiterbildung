import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from bson import ObjectId

from app.core.config import logger
from app.core.database import Database
from app.services.extraction import DataExtractor
from app.services.utils import fetch_html


async def save_course(course_data: Dict[str, Any], provider_id: ObjectId) -> None:
    """Save course data with reference to provider"""
    course_data["provider_id"] = provider_id
    course_data["created_at"] = datetime.now(timezone.utc)
    course_data["updated_at"] = datetime.now(timezone.utc)

    existing_course = await Database.get_collection("courses").find_one(
        {"course_url": course_data["course_url"], "provider_id": provider_id}
    )

    if existing_course:
        await Database.get_collection("courses").update_one(
            {"_id": existing_course["_id"]},
            {"$set": {**course_data, "updated_at": datetime.now(timezone.utc)}},
        )
        logger.info(f"Updated existing course: {course_data['course_url']}")
    else:
        await Database.get_collection("courses").insert_one(course_data)
        logger.info(f"Inserted new course: {course_data['course_url']}")


@dataclass
class ScrapingContext:
    """Context for scraping operations with thread-safe collections"""

    base_url: str
    provider_id: ObjectId
    checked_urls: Set[str]
    queue: deque
    data_extractor: DataExtractor
    lock: asyncio.Lock


async def scrap_course_data(
    session: aiohttp.ClientSession, url: str, context: ScrapingContext
) -> None:
    """Process individual course pages with proper locking"""
    try:
        html_content, course_url = await fetch_html(url, session)
        if not html_content:
            return
        async with context.lock:
            context.checked_urls.add(url)
        logger.info(f"Successfully fetched {url}")

        course_data = context.data_extractor.extract_data(html_content)
        if course_data:
            course_data["course_url"] = course_url
            course_data["content"] = BeautifulSoup(html_content, "lxml").get_text()
            await save_course(course_data, context.provider_id)

        soup = BeautifulSoup(html_content, "lxml")
        parsed_base_url = urlparse(context.base_url)
        new_urls = []

        for tag in soup.find_all("a"):
            href = tag.get("href")
            if href:
                full_url = urljoin(url, href.split("#")[0])
                parsed_url = urlparse(full_url)

                if parsed_url.netloc == parsed_base_url.netloc:
                    new_urls.append(full_url)

        async with context.lock:
            for full_url in new_urls:
                if full_url not in context.checked_urls:
                    context.checked_urls.add(full_url)
                    context.queue.append(full_url)

    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")


async def worker(
    session: aiohttp.ClientSession,
    context: ScrapingContext,
    worker_id: int,
    shutdown_event: asyncio.Event,
) -> None:
    """Worker with improved queue handling and shutdown mechanism"""
    logger.info(f"Starting worker {worker_id}")
    while not shutdown_event.is_set():
        try:
            url = None
            async with context.lock:
                if context.queue:
                    url = context.queue.popleft()

            if url:
                logger.info(f"Worker {worker_id} processing: {url}")
                logger.info(f"Worker {worker_id} queue size: {len(context.queue)}")
                logger.info(f"Worker {worker_id} total URLs: {len(context.checked_urls)}")
                await scrap_course_data(session, url, context)
            else:
                await asyncio.sleep(3)

                async with context.lock:
                    if not context.queue:
                        await asyncio.sleep(3)
                        if not context.queue:
                            logger.info(f"Worker {worker_id} shutting down")
                            shutdown_event.set()
                            break

        except Exception as e:
            logger.error(f"Worker {worker_id} error: {str(e)}")


async def process_url(university: Dict[str, Any]) -> None:
    """Process URLs with improved worker management"""
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(limit=100)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        data_extractor = DataExtractor(university["target_fields"])

        context = ScrapingContext(
            base_url=university["base_url"],
            provider_id=university["_id"],
            checked_urls=set([university["base_url"]]),
            queue=deque([university["base_url"]]),
            data_extractor=data_extractor,
            lock=asyncio.Lock(),
        )

        num_workers = 16
        workers = [
            asyncio.create_task(worker(session, context, worker_id, asyncio.Event()))
            for worker_id in range(num_workers)
        ]

        await asyncio.gather(*workers)

        logger.info(
            f"Completed processing {university['base_url']}. "
            f"Total URLs processed: {len(context.checked_urls)}"
        )


async def scrape_university(university_id: str) -> Dict[str, Any]:
    """Main entry point for scraping job"""
    await Database.connect_db()

    university = await Database.get_collection("universities").find_one_and_update(
        {"_id": ObjectId(university_id)},
        {"$set": {"status": "in_progress"}},
        return_document=True,
    )

    await process_url(university)

    return await Database.get_collection("scraping_jobs").find_one_and_update(
        {"_id": ObjectId(university_id)},
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "message": "Scraping job completed successfully",
            }
        },
        return_document=True,
    )
