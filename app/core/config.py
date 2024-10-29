import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "poc-scraper")
    MONGO_INITDB_ROOT_USERNAME: Optional[str] = os.getenv(
        "MONGO_INITDB_ROOT_USERNAME"
    )
    MONGO_INITDB_ROOT_PASSWORD: Optional[str] = os.getenv(
        "MONGO_INITDB_ROOT_PASSWORD"
    )

    # Redis Settings
    REDIS_USER: Optional[str] = os.getenv("REDIS_USER")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")

    # Celery Settings
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", "redis://redis:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
    )

    # Monitoring Settings
    FLOWER_PORT: int = int(os.getenv("FLOWER_PORT", "5555"))
    FLOWER_UNAUTHENTICATED_API: bool = (
        os.getenv("FLOWER_UNAUTHENTICATED_API", "false").lower() == "true"
    )

    # Apxplication Settings
    APP_NAME: str = os.getenv("APP_NAME", "poc-scraper")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "0") == "1"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in allowed_levels:
            return "INFO"
        return upper_v

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(",")]
        return ["*"]

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def api_url(self) -> str:
        protocol = "https" if self.SSL_ENABLED else "http"
        return f"{protocol}://{self.API_HOST}:{self.API_PORT}"


settings = Settings()
