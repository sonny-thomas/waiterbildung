from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.file import router as file_router
from app.api.course import router as course_router
from app.api.institution import router as institution_router
from app.api.chat import router as chat_router
from app.api.scraper import router as scraper_router
from app.core import settings
from app.core import db
from app.services.agent import client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI application.
    """
    try:
        await client.initialize()
        yield
    finally:
        await db.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend application for Waiterbildung",
    lifespan=lifespan,
    debug=settings.DEBUG,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(user_router, prefix=settings.API_PREFIX)
app.include_router(file_router, prefix=settings.API_PREFIX)
app.include_router(course_router, prefix=settings.API_PREFIX)
app.include_router(institution_router, prefix=settings.API_PREFIX)
app.include_router(scraper_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
