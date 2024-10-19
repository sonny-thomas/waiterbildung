import json
import aiohttp
import asyncio
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from aiohttp import ClientTimeout
from collections import deque
from openai import OpenAI
from uuid import uuid4

global_url_count = 0
scraped_data = {}
MAX_COURSES = 1

client = OpenAI(api_key="")

# Configure logging
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


def generate_openai_prompt(html_content):
    prompt = f"""
    You are a web scraper and your task is to extract course information from the following HTML content.
    A course page typically contains details such as the course name, description, duration, credits, prerequisites, and fees.
    If the current page is not a course page, return an empty JSON object.

    Here is the HTML content:
    {html_content}

    Please return the extracted course information as a JSON object based on the schema provided.
    If the current page is not a course page, return an empty JSON object.
    """
    return prompt


async def extract_course_data(html_content, course_url):
    prompt = generate_openai_prompt(html_content)

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="o1-preview",
            messages=[
                {
                    "role": "system",
                    "content": """
                You are a web scraper, and your task is to extract course information from the following HTML content.
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
                    "start_date": "date",
                    "application_deadline": "date",
                    "mode_of_study": "string",
                    "teaching_language": "string",
                    "location": {
                        "city": "string",
                        "country": "string"
                    },
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
                    "credits": {
                        "total_ects": "integer",
                        "per_year": "integer"
                    },
                    "program_structure": {
                        "number_of_semesters": "integer",
                        "stay_abroad": "boolean"
                    },
                    "contact_information": {
                        "program_head": {
                            "name": "string",
                            "phone": "string",
                            "email": "string"
                        },
                        "institute": {
                            "name": "string",
                            "address": {
                                "street": "string",
                                "city": "string",
                                "postal_code": "string",
                                "country": "string"
                            },
                            "phone": "string",
                            "email": "string"
                        }
                    },
                    "admission_requirements": "string",
                    "key_dates": {
                        "start_of_semester": "date",
                        "application_open": "date",
                        "application_close": "date"
                    },
                    "url": "string"
                }

                Explanation:
                    program_name: Name of the degree program being offered.
                    degree: Type of degree awarded (e.g., MA, BSc).
                    description: Brief overview of the program's objectives or focus.
                    ects_points: Total credits (if applicable).
                    duration: How long the program lasts, with both a value and unit (e.g., 4 semesters, 2 years).
                    start_date: The start date of the program.
                    application_deadline: Final date for applications to be submitted.
                    mode_of_study: Describes the type of study (e.g., full-time, online).
                    teaching_language: Primary language in which the course is taught.
                    location: The city and country where the course takes place.
                    fees: Application and tuition fees categorized for local, EU, and international students.
                    credits: Total number of credits awarded upon completion and per year (if applicable).
                    program_structure: Number of semesters and whether a study abroad option is available.
                    contact_information: Contact details, including the program head and institute contact info.
                    admission_requirements: Requirements for entry into the program (if available).
                    key_dates: Relevant dates for the start of the semester and application window.
                    url: Direct URL to the program’s official webpage.
                """,
                },
                {"role": "user", "content": prompt},
            ],
        )
        course_data = response.choices[0].message.content.strip()
        if not course_data:
            logger.warning(f"Received empty response for {course_url}")
            return None
        try:
            course_json = json.loads(course_data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {course_url}: {e}")
            return None
        course_json["url"] = course_url

        return course_json

    except Exception as e:
        logger.error(f"Error during OpenAI processing: {e}")
        return None


async def scrap_course_data(session, url, identifiers, checked_urls, queue):
    course_url = None

    html = await fetch(session, url)
    if html:
        logger.info(f"Succesfully fetched {url}")
        soup = BeautifulSoup(html, "lxml")

        found_identifiers = 0
        for identifier in identifiers:
            if identifier.get("id"):
                if soup.find(id=identifier["id"]):
                    found_identifiers += 1
                    logger.info(f"Found element with id {identifier['id']} on {url}")
                else:
                    logger.error(
                        f"Element with id {identifier['id']} not found on {url}"
                    )
            elif identifier.get("class"):
                if soup.find(class_=identifier["class"]):
                    found_identifiers += 1
                    logger.info(f"Found element with class {identifier['class']} on {url}")
                else:
                    logger.error(
                        f"Element with class {identifier['class']} not found on {url}"
                    )

        len_identifiers = len(identifiers)
        logger.info(
            f"Found {found_identifiers} out of {len_identifiers} identifiers on {url}"
        )

        if found_identifiers >= (len_identifiers / 2):
            logger.info(f"Identifying element found on {url}")
            scraped_data[str(uuid4())] = {"url": url}
            await save_scraped_data()
            return
            logger.info(f"Identifying element found on {url}")
            course_data = await extract_course_data(html, url)
            if course_data:
                scraped_data[str(uuid4())] = course_data
                logger.info(f"Extracted course data from {url}")

                if len(scraped_data) >= MAX_COURSES:
                    logger.info(
                        f"Reached maximum number of courses ({MAX_COURSES}). Saving data and exiting..."
                    )
                    await save_scraped_data()
                    return

        for tag in soup.find_all("a"):
            href = tag.get("href")
            if href:
                full_url = urljoin(url, href.split("#")[0])
                base_url = urlparse(full_url).netloc
                orig_base_url = urlparse(url).netloc

                if base_url == orig_base_url and full_url not in checked_urls:
                    checked_urls.add(full_url)
                    logger.info(f"Found internal link: {full_url}")
                    queue.append((full_url, identifiers))

    return


async def worker(session, queue, checked_urls):
    while queue and len(scraped_data) < MAX_COURSES:
        url, identifiers = queue.popleft()
        await scrap_course_data(session, url, identifiers, checked_urls, queue)


async def process_url(data, session):
    global scraped_data
    url = data["url"]
    identifiers = data["identifiers"]
    checked_urls = {url}
    queue = deque([(url, identifiers)])

    logger.info(f"Processing: {url}\n")

    workers = [asyncio.create_task(worker(session, queue, checked_urls))]
    await asyncio.gather(*workers)


async def save_scraped_data():
    with open("scraped_data.json", "w", encoding="utf-8") as outfile:
        json.dump(scraped_data, outfile, indent=4)


async def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    async with aiohttp.ClientSession(
        timeout=ClientTimeout(total=60)
    ) as session:
        tasks = [process_url(uni, session) for uni in data]
        await asyncio.gather(*tasks)

    await save_scraped_data()


if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Scraping process completed.")
