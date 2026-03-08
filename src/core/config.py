import logging
import os
from random import randint

from pydantic_settings import BaseSettings, SettingsConfigDict


class GlobalSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: int = logging.DEBUG

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_SCHEMA: str
    # specify single database url
    DB_URL: str | None = None
    POSTGRES_CONTAINER_PORT: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_PASSWORD: str
    REDIS_CACHE_EXPIRATION_SECONDS: int
    REDIS_DB: int
    REDIS_CONTAINER_PORT: int

    CACHE_DURATION: int = 2592000  # 30 days in seconds
    REQUEST_TIMEOUT: int = 30

    JWT_ACCESS_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ENCRYPTION_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: str
    NEW_ACCESS_TOKEN_EXPIRE_MINUTES: str
    REFRESH_TOKEN_EXPIRE_MINUTES: str
    SESSION_SECRET_KEY: str
    SESSION_EXPIRE_HOURS: int

    RATE_LIMIT_DEFAULT_CALLS: int = 10
    RATE_LIMIT_DEFAULT_PERIOD: int = 60
    RATE_LIMIT_API_PREFIX: str = "/v1/"
    RATE_LIMIT_EXCLUDED: str = "/docs,/openapi.json,/redoc"

    ENABLE_RATE_LIMITING: bool = True
    REDIS_ENABLED: bool = True

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Target scan async: base dir for task payloads (API writes here, worker reads)
    LEXNORM_TASK_BASE_DIR: str | None = None  # default: gettempdir()/lexnorm_tasks

    OLLAMA_URL: str
    MODEL_NAME: str
    MODEL_TEMPERATURE: float


class TestSettings(GlobalSettings):
    DB_SCHEMA: str = f"test_{randint(1, 100)}"


class DevelopmentSettings(GlobalSettings):
    ALLOWED_ORIGINS: str = "*"


class ProductionSettings(GlobalSettings):
    ALLOWED_ORIGINS: str = "127.0.0.1,localhost,"


def get_settings():
    env = os.environ.get("ENVIRONMENT", "development")

    if env == "test":
        return TestSettings()
    elif env == "development":
        return DevelopmentSettings()
    elif env == "production":
        return ProductionSettings()

    return GlobalSettings()


settings = get_settings()


LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": settings.LOG_LEVEL, "propagate": False},
        "uvicorn": {
            "handlers": ["default"],
            "level": logging.INFO,
            "propagate": False,
        },
    },
}
