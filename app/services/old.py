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
import os
from dotenv import load_dotenv

global_url_count = 0
scraped_courses = 0
scraped_data = {}
MAX_COURSES = 1

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

    Please return the formatted course information as a JSON object based on the schema provided.
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

                Explanation:
                    program_name: Name of the degree program being offered.
                    degree: Type of degree awarded (e.g., MA, BSc).
                    description: Brief overview of the program's objectives or focus.
                    ects_points: Total credits (if applicable).
                    duration: How long the program lasts, with both a value and unit (e.g., 4 semesters, 2 years).
                    mode_of_study: Describes the type of study (e.g., full-time, online).
                    teaching_language: Primary language in which the course is taught.
                    fees: Application and tuition fees categorized for local, EU, and international students.
                    program_structure: Number of semesters and whether a study abroad option is available.
                    key_dates: Relevant dates for the start of the semester and application window.
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
    session, url, identifiers, checked_urls, queue, uni_name
):
    course_url = None

    html = await fetch(session, url)
    if html:
        logger.info(f"Succesfully fetched {url}")
        soup = BeautifulSoup(html, "lxml")

        course_data = []
        found_identifiers = 0
        for identifier in identifiers:
            name = identifier.name
            type = str(identifier.type)
            value = identifier.value

            if type == "id":
                content = soup.find(id=value)
            else:
                content = soup.find(class_=value)

            if content:
                found_identifiers += 1
                course_data.append((name, content.get_text()))
                logger.info(f"Found element with {type} {value} on {url}")
            else:
                logger.error(f"Element with {type} {value} not found on {url}")

        len_identifiers = len(identifiers)
        logger.info(
            f"Found {found_identifiers} out of {len_identifiers} identifiers on {url}"
        )

        if found_identifiers >= (len_identifiers / 2):
            course_url = url
            course_json = await extract_course_data(course_data, course_url)
            if course_json:
                global scraped_courses
                scraped_data[uni_name][str(uuid4())] = course_json
                scraped_courses += 1
                logger.info(f"Extracted course data from {url}")

                if scraped_courses >= MAX_COURSES:
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


async def worker(session, queue, checked_urls, uni_name):
    while queue and scraped_courses < MAX_COURSES:
        url, identifiers = queue.popleft()
        await scrap_course_data(
            session, url, identifiers, checked_urls, queue, uni_name
        )


def process_url(data):
    global scraped_data
    uni_name = "dfdslkfj"
    url = data.get("url")
    identifiers = data.get("identifiers")
    checked_urls = {url}
    scraped_data[uni_name] = {}
    import time
    time.sleep(10)
    
    raise Exception("fsfsd")

    queue = deque([(url, identifiers)])

    # logger.info(f"Processing: {url}\n")

    # async with aiohttp.ClientSession(
    #     timeout=ClientTimeout(total=60)
    # ) as session:
    #     workers = [
    #         asyncio.create_task(worker(session, queue, checked_urls, uni_name))
    #     ]
    #     await asyncio.gather(*workers)


async def save_scraped_data():
    with open("scraped_data.json", "w", encoding="utf-8") as outfile:
        json.dump(scraped_data, outfile, indent=4)


async def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    tasks = [process_url(uni) for uni in data]
    await asyncio.gather(*tasks)

    await save_scraped_data()
    sendemail()


if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Scraping process completed.")
