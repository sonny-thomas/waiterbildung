
from app.api import scraper
from app.core.config import settings
from app import app


app.include_router(
    scraper.router, prefix=settings.API_PREFIX, tags=["scraper"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development,
        workers=settings.WORKERS_COUNT if settings.is_production else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )
