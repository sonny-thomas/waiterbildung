import json
import aiohttp
import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from aiohttp import ClientTimeout
from collections import deque
from openai import OpenAI

global_url_count = 0
scraped_data = {}
MAX_COURSES = 1

client = OpenAI(api_key='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')

async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text(errors="replace")
            else:
                print(f"Failed to retrieve {url}: Status code {response.status}")
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Error accessing {url}: {e}")
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
        response = await asyncio.to_thread(client.chat.completions.create,
            model="o1-preview",
            messages=[
                {"role": "system", "content": """
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
                """},
                {"role": "user", "content": prompt}
            ]
        )
        course_data = response.choices[0].message.content.strip()
        if not course_data:
            print(f"Received empty response for {course_url}")
            return None
        try:
            course_json = json.loads(course_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {course_url}: {e}")
            return None
        course_json["url"] = course_url
        
        return course_json
    
    except Exception as e:
        print(f"Error during OpenAI processing: {e}")
        return None

async def scrap_course_data(session, url, identifying_id, checked_urls, queue):
    global global_url_count
    course_urls = []
    
    html = await fetch(session, url)
    if html:
        print(f"Successfully retrieved content for {url}, parsing...")
        soup = BeautifulSoup(html, "lxml")
        
        if soup.find(id=identifying_id):
            course_urls.append(url)
            print(f"Identifying element found on {url}")
            
            course_data = await extract_course_data(html, url)
            if course_data:
                course_name = course_data.get("name", f"Course {global_url_count}")
                scraped_data[course_name] = course_data
                print(f"Extracted course data for {course_name}")
                
                if len(scraped_data) >= MAX_COURSES:
                    print(f"Reached maximum number of courses ({MAX_COURSES}). Saving data and exiting...")
                    await save_scraped_data()
                    return course_urls
        
        for tag in soup.find_all("a"):
            href = tag.get("href")
            if href:
                full_url = urljoin(url, href.split("#")[0])
                base_url = urlparse(full_url).netloc
                orig_base_url = urlparse(url).netloc
                
                if base_url == orig_base_url and full_url not in checked_urls:
                    checked_urls.add(full_url)
                    global_url_count += 1
                    print(f"Found internal link: {full_url}")
                    queue.append((full_url, identifying_id))

    return course_urls

async def worker(session, queue, checked_urls, identifier):
    while queue and len(scraped_data) < MAX_COURSES:
        url, identifying_id = queue.popleft()
        await scrap_course_data(session, url, identifying_id, checked_urls, queue)

async def process_url(data, session):
    global scraped_data
    name = data["name"]
    url = data["url"]
    identifier = data["identifier"]
    checked_urls = {url}
    queue = deque([(url, identifier)])

    print(f"\nProcessing university: {name} | URL: {url} | Identifier: {identifier}")

    workers = [asyncio.create_task(worker(session, queue, checked_urls, identifier))]
    await asyncio.gather(*workers)

    print(f"Finished processing {name}. Scraped {len(checked_urls)} URLs.")

async def save_scraped_data():
    with open("scraped_data.json", "w", encoding="utf-8") as outfile:
        json.dump(scraped_data, outfile, indent=4)
    print("Scraped data has been saved to 'scraped_data.json'")

async def main():
    global global_url_count
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    async with aiohttp.ClientSession(timeout=ClientTimeout(total=300)) as session:
        tasks = [process_url(uni, session) for uni in data]
        await asyncio.gather(*tasks)

    print(f"Total individual URLs processed: {global_url_count}")
    
    await save_scraped_data()

if __name__ == "__main__":
    print("Starting scraping process...")
    asyncio.run(main())
    print("Scraping process completed.")
