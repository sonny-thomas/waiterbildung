import asyncio
from collections import deque
from typing import Set
from urllib.parse import urldefrag, urljoin

import aiohttp
import tldextract
from bs4 import BeautifulSoup

from app.core.chatbot import openai
from app.core.database import SessionLocal
from app.core.logger import logger
from app.core.utils import clean_html
from app.models.course import Course
from app.schemas.course import ScrapeCourse


class Scraper:
    def __init__(
        self,
        institution_id: str,
        domain: str,
        course_url: str,
        course_selector: str,
        hero_image_selector: str,
        max_courses: int,
    ):
        self.institution_id = institution_id
        self.domain = domain
        self.course_selector = course_selector
        self.hero_image_selector = hero_image_selector
        self.max_courses = max_courses
        self.courses_found = 0

        self.visited_urls: Set[str] = set()
        self.url_queue = deque([course_url])
        self.pending_urls: Set[str] = set()
        self.processing_semaphore = asyncio.Semaphore(10)
        self.save_semaphore = asyncio.Semaphore(5)

    def normalize_url(self, url: str) -> str:
        clean_url, _ = urldefrag(url)
        return clean_url.lower().rstrip("/")

    def should_process_url(self, url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            return False

        normalized_url = self.normalize_url(url)

        if tldextract.extract(normalized_url).registered_domain != self.domain:
            return False

        if normalized_url in self.visited_urls:
            return False

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
            return False

        return True

    def extract_hero_image(self, soup: BeautifulSoup, base_url: str) -> str | None:
        if not self.hero_image_selector:
            return None

        hero_img = soup.select_one(self.hero_image_selector)
        if not hero_img:
            return None

        # Try to get image URL from src or data-src attributes
        img_url = hero_img.get("src") or hero_img.get("data-src")
        if img_url:
            return urljoin(base_url, img_url)
        return None

    def extract_course(self, html: str) -> ScrapeCourse | None:
        completion = openai.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Extract course information from the HTML content. 
                        Focus on finding:
                        - Title
                        - Description
                        - Degree type (bachelor, master, phd, not_specified)
                        - Study mode (full_time, part_time, online, hybrid, not_specified)
                        - ECTS credits
                        - Teaching language
                        - Diploma awarded
                        - Start date
                        - End date
                        - Duration in semesters
                        - Application deadline
                        - Campus location
                        - Study abroad availability
                        - Tuition fee per semester
                        Return structured data only.""",
                },
                {"role": "user", "content": html},
            ],
            response_format=ScrapeCourse,
        )
        result = completion.choices[0].message.parsed
        return result

    async def save_course_data(self, url: str, soup: BeautifulSoup, html: str) -> None:
        async with self.save_semaphore:
            logger.info(f"Saving course data for {url}")
            try:
                db = SessionLocal()
                content = clean_html(html)
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.extract_course, content
                )

                if data is None:
                    return

                hero_image = self.extract_hero_image(soup, url)

                existing_course = Course.get(db, url=url)

                course_data = {
                    **data.model_dump(),
                    "institution_id": self.institution_id,
                    "url": url,
                    "detailed_content": content,
                    "hero_image": hero_image,
                }

                if existing_course:
                    for key, value in course_data.items():
                        setattr(existing_course, key, value)
                    course = existing_course
                else:
                    course = Course(**course_data)

                if self.courses_found < self.max_courses:
                    course.save(db)
                    self.courses_found += 1
                    logger.info(f"Saved course {course.title}")

            except Exception as e:
                logger.exception(f"Error saving course data for {url}")
            finally:
                db.close()

    async def process_url(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        if self.courses_found >= self.max_courses:
            return set()

        async with self.processing_semaphore:
            try:
                normalized_url = self.normalize_url(url)
                self.pending_urls.add(normalized_url)
                if normalized_url in self.visited_urls:
                    return set()

                async with session.get(
                    normalized_url, allow_redirects=True
                ) as response:
                    if response.status == 200:
                        final_url = str(response.url)
                        normalized_final = self.normalize_url(final_url)

                        if normalized_final in self.visited_urls:
                            return set()

                        self.visited_urls.update(
                            [normalized_final, final_url, normalized_url, url]
                        )

                        html = await response.text()

                        soup = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: BeautifulSoup(html, "html.parser")
                        )

                        if self.courses_found < self.max_courses and soup.select(
                            self.course_selector
                        ):
                            await self.save_course_data(normalized_final, soup, html)

                        if self.courses_found >= self.max_courses:
                            return set()

                        links: Set[str] = set()
                        for link in soup.find_all("a", href=True):
                            full_url = urljoin(normalized_final, link["href"])
                            if self.should_process_url(full_url):
                                links.add(full_url)

                        return links
                    else:
                        return set()
            except Exception as e:
                logger.exception(f"Error processing URL {url}")
                return set()
            finally:
                if url in self.pending_urls:
                    self.pending_urls.remove(url)
                self.visited_urls.add(url)
                self.visited_urls.add(self.normalize_url(url))

    async def worker(self, session: aiohttp.ClientSession) -> None:
        while True:
            if self.courses_found >= self.max_courses:
                break

            if not self.url_queue and not self.pending_urls:
                break
            try:
                url = self.url_queue.popleft()
            except IndexError:
                if self.pending_urls:
                    await asyncio.sleep(0.1)
                    continue

                break

            new_links = await self.process_url(session, url)
            self.url_queue.extend(new_links)

            await asyncio.sleep(0.1)

    async def crawl(self) -> None:
        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self.worker(session)) for _ in range(10)]
            await asyncio.gather(*workers)
