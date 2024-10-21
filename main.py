from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from enum import Enum
from scraper import process_url
from celery_config import celery_app as celery


app = FastAPI()


class IdentifierType(str, Enum):
    id = "id"
    class_ = "class"


class Identifier(BaseModel):
    name: str
    type: IdentifierType
    value: str


class ScrapeRequest(BaseModel):
    url: HttpUrl
    identifiers: list[Identifier]


@app.post("/scrape")
async def scrape(target: ScrapeRequest):
    target = target.model_dump()
    target["url"] = str(target["url"])
    scrape_url.delay(target)
    return {"message": "processed"}


@celery.task(name="Scrape URL")
def scrape_url(target: dict):
    process_url(target)
