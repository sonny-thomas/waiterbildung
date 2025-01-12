from redis import Redis
from rq import Queue

from app.core.config import settings

redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
)

email_queue = Queue("email", connection=redis_conn)
scraper_queue = Queue("scraper", connection=redis_conn)

QUEUE = {
    "email": email_queue,
    "scraper": scraper_queue,
}
