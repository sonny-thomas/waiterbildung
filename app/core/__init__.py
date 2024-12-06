import asyncio
import logging

from celery import Celery

from app.core.config import Settings
from app.core.database import Database
from app.core.cloudinary import Cloudinary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()
cloudinary = Cloudinary()
db = Database()
asyncio.run(db.connect())

celery = Celery(
    "scraper_worker",
    imports=["app.tasks.scraper_tasks"],
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
