from typing import Optional

from pydantic import HttpUrl
from sqlalchemy import Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import SessionLocal
from app.core.logger import logger
from app.core.scraper import Scraper
from app.models import BaseModel
from app.schemas.institution import ScraperStatus


class Institution(BaseModel):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    logo: Mapped[Optional[HttpUrl]] = mapped_column(String(500), nullable=True)
    scraper_status: Mapped[ScraperStatus] = mapped_column(
        SQLEnum(ScraperStatus), nullable=False, default=ScraperStatus.queued
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    average_rating: Mapped[float] = mapped_column(Float, default=0.0)

    async def scrape_courses(
        self,
        domain: str,
        url: str,
        selector: str,
        hero_image_selector: str,
        max_courses: int,
    ) -> None:
        """Scrape courses from the institution's website"""
        db = SessionLocal()
        try:
            scraper = Scraper(
                self.id, domain, url, selector, hero_image_selector, max_courses
            )
            self.scraper_status = ScraperStatus.in_progress
            db.add(self)
            db.commit()

            await scraper.crawl()
            self.scraper_status = ScraperStatus.completed
            db.add(self)
        except Exception:
            logger.exception(
                f"Failed to scrape courses for {self.name} ({self.domain})"
            )
            self.scraper_status = ScraperStatus.failed
            db.add(self)
        finally:
            db.commit()
            db.close()
