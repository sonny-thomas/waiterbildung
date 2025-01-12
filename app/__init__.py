from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rq_dashboard_fast import RedisQueueDashboard

from app.api import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    except Exception:
        yield


app = FastAPI(
    title="Waiterbildung API",
    version="1.0",
    description="API for Waiterbildung",
    lifespan=lifespan,
    debug=settings.DEBUG,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rq_dashboard = RedisQueueDashboard(settings.REDIS_URI, url_prefix="/rq")

app.mount("/rq", rq_dashboard)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint to verify API status"""
    return {
        "message": "Waiterbildung API is running",
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


app.include_router(api_router, prefix=settings.API_PREFIX)
