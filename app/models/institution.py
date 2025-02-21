from typing import Optional

from pydantic import HttpUrl
from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel
from app.schemas.scraper import ScraperStatus


class Institution(BaseModel):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    logo: Mapped[Optional[HttpUrl]] = mapped_column(String(500), nullable=True)
    scraping_status: Mapped[ScraperStatus] = mapped_column(
        SQLEnum(ScraperStatus),
        nullable=False,
        default=ScraperStatus.not_started,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    SEARCH_FIELDS = ["name", "domain"]
