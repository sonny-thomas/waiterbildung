import asyncio
from collections import deque
from typing import List, Optional, Set
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from pydantic import HttpUrl
from sqlalchemy.orm import Session

from app.core.chatbot import openai
from app.core.database import SessionLocal
from app.core.logger import logger
from app.core.utils import (
    clean_html,
    get_domain,
    normalize_url,
)
from app.models.course import Course
from app.models.institution import Institution
from app.schemas.course import CourseBaseResponse
from app.schemas.scraper import ScrapeInstitution, ScraperStatus


async def extract_course(
    db: Optional[Session],
    institution_id: str,
    url: str,
    html: str,
    hero_image_selector: Optional[str] = None,
    worker_id: int = 0,
) -> Optional[Course]:
    """Extract course data from HTML and optionally save to database."""
    logger.info(f"Worker {worker_id}: Extracting course from URL {url}")
    try:
        content = clean_html(html)
        completion = openai.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Extract course information from the HTML content...""",
                },
                {"role": "user", "content": content},
            ],
            response_format=CourseBaseResponse,
        )

        data = completion.choices[0].message.parsed
        if not data:
            logger.info(f"Worker {worker_id}: No data extracted from {url}")
            return None

        hero_image = None
        if hero_image_selector:
            soup = BeautifulSoup(html, "html.parser")
            hero_img = soup.select_one(hero_image_selector)
            if hero_img:
                hero_image = urljoin(
                    url, hero_img.get("src") or hero_img.get("data-src")
                )

        course_data = {
            **data.model_dump(),
            "url": url,
            "detailed_content": content,
            "hero_image": hero_image,
        }

        if db:
            existing_course = Course.get(db, url=url)
            if existing_course:
                for key, value in course_data.items():
                    setattr(existing_course, key, value)
                course = existing_course
            else:
                course = Course(institution_id=institution_id, **course_data)

            course.save(db)
            logger.info(f"Worker {worker_id}: Saved course {course.title}")
            return course

        return Course(**course_data)

    except asyncio.TimeoutError:
        logger.error(
            f"Worker {worker_id}: Timeout extracting course from URL {url}"
        )
        return None
    except Exception as e:
        logger.exception(
            f"Worker {worker_id}: Error extracting course from URL {url}: {str(e)}"
        )
        return None


class Crawler:
    def __init__(
        self, institution_id: str, domain: str, req: ScrapeInstitution
    ):
        self.institution_id = institution_id
        self.domain = domain
        self.start_url = normalize_url(str(req.start_url))
        self.course_selectors = req.course_selectors
        self.hero_image_selector = req.hero_image_selector
        self.max_courses = req.max_courses
        self.courses_found = 0

        self.visited_urls: Set[str] = set()
        self.url_queue = deque([self.start_url])
        self.pending_urls: Set[str] = {self.start_url}
        self.semaphore = asyncio.Semaphore(20)

    def should_process_url(self, url: str) -> str | None:
        """Check if URL should be processed."""
        if not url.startswith(("http://", "https://")):
            return None

        normalized_url = normalize_url(url)
        if normalized_url in self.visited_urls:
            return None

        if get_domain(normalized_url) != self.domain:
            return None

        if any(
            ext in normalized_url
            for ext in [
                ".pdf",
                ".doc",
                ".docx",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".zip",
                ".rar",
                ".csv",
                ".xlsx",
                ".ppt",
                ".pptx",
            ]
        ):
            return None

        return normalized_url

    async def process_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        worker_id: int,
        db: Session,
    ) -> None:
        """Process a single URL, extract course data if found, and find new URLs."""
        if self.courses_found >= self.max_courses:
            return

        async with self.semaphore:
            self.pending_urls.add(url)
            logger.info(f"Worker {worker_id}: Processing URL {url}")
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(
                    url, allow_redirects=True, timeout=timeout
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Worker {worker_id}: Status {response.status} for URL {url}"
                        )
                        return

                    final_url = str(response.url)
                    normalized_url = normalize_url(final_url)
                    self.visited_urls.update({url, final_url, normalized_url})

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    matches = False
                    for selector in self.course_selectors:
                        if soup.select(selector):
                            matches = True
                            break
                    if matches and self.courses_found < self.max_courses:
                        await extract_course(
                            db,
                            self.institution_id,
                            normalized_url,
                            html,
                            self.hero_image_selector,
                            worker_id,
                        )
                        self.courses_found += 1

                    for link in soup.find_all("a", href=True):
                        full_url = urljoin(url, link["href"])
                        normalized = self.should_process_url(full_url)
                        if normalized:
                            self.url_queue.append(normalized)

            except asyncio.TimeoutError:
                logger.error(
                    f"Worker {worker_id}: Timeout processing URL {url}"
                )
            except Exception as e:
                logger.exception(
                    f"Worker {worker_id}: Error processing URL {url}: {str(e)}"
                )
            finally:
                if url in self.pending_urls:
                    self.pending_urls.remove(url)
                self.visited_urls.add(url)

    async def worker(self, worker_id: int, db: Session) -> None:
        """Individual worker that processes URLs independently."""
        conn = aiohttp.TCPConnector()
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(
            connector=conn, timeout=timeout
        ) as session:
            while True:
                if self.courses_found >= self.max_courses:
                    break

                try:
                    url = self.url_queue.popleft()
                except IndexError:
                    if self.pending_urls:
                        await asyncio.sleep(0.1)
                        continue
                    break

                await self.process_url(session, url, worker_id, db)

    async def crawl(self) -> None:
        """Crawl website using multiple independent workers."""
        db = SessionLocal()
        try:
            institution = Institution.get(db, id=self.institution_id)
            if institution:
                institution.scraping_status = ScraperStatus.in_progress
                institution.save(db)
            print(f"Scraping {self.domain} with {self.max_courses} courses")

            workers = [
                asyncio.create_task(self.worker(i, db)) for i in range(20)
            ]
            await asyncio.gather(*workers)

            if institution:
                institution.scraping_status = ScraperStatus.completed
                institution.save(db)

        except Exception as e:
            logger.exception(f"Error crawling institution: {str(e)}")
            if institution:
                institution.scraping_status = ScraperStatus.failed
                institution.save(db)
        finally:
            db.close()


async def scrape_course(
    course_url: HttpUrl,
    course_selectors: Optional[set[str]] = None,
    hero_image_selector: Optional[str] = None,
) -> Optional[Course]:
    """Scrape a single course URL and return the Course object."""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        conn = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(
            connector=conn, timeout=timeout
        ) as session:
            async with session.get(
                str(course_url), allow_redirects=True
            ) as response:
                if response.status == 200:
                    html = await response.text()

                    if course_selectors:
                        soup = BeautifulSoup(html, "html.parser")
                        matches = False
                        for selector in course_selectors:
                            if soup.select(selector):
                                matches = True
                                break
                        if not matches:
                            logger.warning(
                                f"URL {course_url} does not match any course selectors"
                            )
                            return None

                    course = await extract_course(
                        None,
                        "institution_id",
                        str(response.url),
                        html,
                        hero_image_selector,
                    )
                    return course
                return None
    except Exception:
        logger.exception(f"Error scraping course from URL {course_url}")
        return None


async def scrape_courses(
    institution_id: str,
    course_urls: List[str],
    hero_image_selector: Optional[str] = None,
) -> None:
    """Scrape a list of known course URLs with controlled concurrency."""
    semaphore = asyncio.Semaphore(20)
    pending_urls: Set[str] = set()

    try:
        db = SessionLocal()
        institution = Institution.get(db, id=institution_id)
        if institution:
            institution.scraping_status = ScraperStatus.in_progress
            institution.save(db)

        async def process_single_url(url: str, worker_id: int) -> None:
            async with semaphore:
                logger.info(f"Processing URL {url}")
                pending_urls.add(url)
                try:
                    timeout = aiohttp.ClientTimeout(total=30)
                    conn = aiohttp.TCPConnector(limit=100)
                    async with aiohttp.ClientSession(
                        connector=conn, timeout=timeout
                    ) as session:
                        async with session.get(
                            url, allow_redirects=True
                        ) as response:
                            if response.status == 200:
                                html = await response.text()
                                await extract_course(
                                    db,
                                    institution_id,
                                    str(url),
                                    html,
                                    hero_image_selector,
                                    worker_id,
                                )
                except Exception as e:
                    logger.exception(
                        f"Worker {worker_id}: Error processing course URL {url}: {str(e)}"
                    )
                finally:
                    if url in pending_urls:
                        pending_urls.remove(url)

        tasks = [
            asyncio.create_task(process_single_url(url, i))
            for i, url in enumerate(course_urls)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        if institution:
            institution.scraping_status = ScraperStatus.completed
            institution.save(db)
    except Exception as e:
        logger.exception(f"Error scraping courses: {str(e)}")
        if institution:
            institution.scraping_status = ScraperStatus.failed
            institution.save(db)
    finally:
        db.close()
