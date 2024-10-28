import asyncio
import json
import logging
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from bson import ObjectId
from dotenv import load_dotenv
from openai import OpenAI

from app.core.database import Database
from app.core.config import settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractionRule:
    selector: str
    selector_type: str
    field_name: str
    data_type: str
    nested_fields: Optional[List["ExtractionRule"]] = None


async def generate_schema(html_content: str, target_fields: List[str]) -> Dict:
    """Generate extraction schema using OpenAI's file search capabilities"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    temp_filename = "temp_page.html"
    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        with open(temp_filename, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")

        vector_store = client.beta.vector_stores.create(
            name="Schema Analysis", file_ids=[file.id]
        )

        assistant = client.beta.assistants.create(
            name="Schema Generator",
            instructions=f"""You are an expert web scraping analyst. Analyze the HTML structure and generate precise CSS selectors for the target fields: {target_fields}.
            The schema should follow this structure:
            {{
                "fields": [
                    {{
                        "name": "field_name",
                        "primary_selector": "CSS selector",
                        "fallback_selectors": ["alternative1", "alternative2"],
                        "data_type": "type",
                        "nested_fields": [{{...}}]
                    }}
                ]
            }}""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )

        thread = client.beta.threads.create()

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Generate a schema for extracting the following fields: {target_fields}",
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=assistant.id
        )

        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run failed with status: {run_status.status}")
            await asyncio.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=thread.id)

        for message in messages.data:
            if message.role == "assistant":
                content = message.content[0].text.value
                try:
                    schema = json.loads(content)
                    return schema
                except json.JSONDecodeError:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        return json.loads(json_match.group())
                    raise Exception("Could not parse schema from response")

    except Exception as e:
        logger.error(f"Error in generate_schema: {e}")
        raise
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        try:
            client.files.delete(file.id)
            client.beta.vector_stores.delete(vector_store.id)
            client.beta.assistants.delete(assistant.id)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class DataExtractor:
    def __init__(self, schema: Dict):
        self.schema = schema
        self.extraction_rules = self._create_extraction_rules()

    def _create_extraction_rules(self) -> List[ExtractionRule]:
        """Convert schema into extraction rules"""
        rules = []
        for field in self.schema["fields"]:
            rule = ExtractionRule(
                selector=field["primary_selector"],
                selector_type="css",
                field_name=field["name"],
                data_type=field["data_type"],
                nested_fields=self._process_nested_fields(
                    field.get("nested_fields", [])
                ),
            )
            rules.append(rule)
        return rules

    def _process_nested_fields(
        self, nested_fields: List
    ) -> Optional[List[ExtractionRule]]:
        if not nested_fields:
            return None
        return [
            ExtractionRule(
                selector=field["primary_selector"],
                selector_type="css",
                field_name=field["name"],
                data_type=field["data_type"],
            )
            for field in nested_fields
        ]

    def extract_data(self, html_content: str) -> Dict[str, Any]:
        """Extract data using the schema"""
        soup = BeautifulSoup(html_content, "lxml")
        data = {}
        found_fields = 0
        total_fields = len(self.extraction_rules)

        for rule in self.extraction_rules:
            value = self._extract_field(soup, rule)
            if value is not None:
                data[rule.field_name] = value
                found_fields += 1
                logger.info(f"Found {rule.field_name}: {value}")
            else:
                logger.warning(f"Could not find {rule.field_name}")

        if found_fields >= (total_fields / 2):
            return data
        return None

    def _extract_field(self, soup: BeautifulSoup, rule: ExtractionRule) -> Any:
        """Extract a single field using the rule"""
        element = soup.select_one(rule.selector)
        if not element:
            return None

        value = element.get_text(strip=True)

        if rule.data_type == "integer":
            try:
                return int("".join(filter(str.isdigit, value)))
            except ValueError:
                return None
        elif rule.data_type == "float":
            try:
                return float("".join(filter(lambda x: x.isdigit() or x == ".", value)))
            except ValueError:
                return None
        elif rule.data_type == "object" and rule.nested_fields:
            nested_data = {}
            for nested_rule in rule.nested_fields:
                nested_value = self._extract_field(element, nested_rule)
                if nested_value is not None:
                    nested_data[nested_rule.field_name] = nested_value
            return nested_data

        return value


async def fetch(session, url):
    """Fetch URL content with error handling"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text(errors="replace")
            else:
                logger.error(f"Failed to retrieve {url}: Status code {response.status}")
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Error accessing {url}: {e}")
        return None


async def scrap_course_data(
    session, url, data_extractor, checked_urls, queue, base_url
):
    """Process individual course pages"""
    html = await fetch(session, url)
    if html:
        logger.info(f"Successfully fetched {url}")

        course_data = data_extractor.extract_data(html)
        if course_data:
            course_data["url"] = url
            await Database.get_collection(base_url).insert_one(course_data)
            logger.info(f"Extracted and saved course data from {url}")

        soup = BeautifulSoup(html, "lxml")
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
                    queue.append(full_url)
                    logger.info(f"Added to queue: {full_url}")


async def worker(session, queue, checked_urls, data_extractor, base_url):
    """Process URLs from the queue"""
    while queue:
        try:
            url = queue.popleft()
            await scrap_course_data(
                session, url, data_extractor, checked_urls, queue, base_url
            )
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")


async def process_url(job):
    """Process URLs with the generated schema"""
    base_url = job["base_url"]
    course_url = job["course_url"]
    target_fields = job["target_fields"]

    async with aiohttp.ClientSession(timeout=ClientTimeout(total=30)) as session:
        initial_html = await fetch(session, course_url)
        if not initial_html:
            logger.error(f"Could not fetch initial page: {course_url}")
            return

        schema = await generate_schema(initial_html, target_fields)
        data_extractor = DataExtractor(schema)

        checked_urls = {course_url}
        queue = deque([course_url])

        num_workers = 1000
        workers = [
            asyncio.create_task(
                worker(session, queue, checked_urls, data_extractor, base_url)
            )
            for _ in range(num_workers)
        ]
        await asyncio.gather(*workers)

    logger.info(f"Completed processing {course_url}. Total URLs: {len(checked_urls)}")


async def scrape_university(job_id: str) -> Dict[str, Any]:
    """Main entry point for scraping job"""
    await Database.connect_db()
    job = await Database.get_collection("scraping_jobs").find_one_and_update(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "in_progress"}},
        return_document=True,
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
