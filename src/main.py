import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.router import routers
from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application started.")

    # Redis'i sadece enabled ise başlat
    if settings.REDIS_ENABLED:
        try:
            import redis.asyncio as aioredis
            from fastapi_limiter import FastAPILimiter

            from src.core.database import redis_pool

            if redis_pool:
                redis = aioredis.Redis(connection_pool=redis_pool)
                await FastAPILimiter.init(redis)
                logger.info("Redis initialized.")
            else:
                logger.warning("Redis enabled but redis_pool is None")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
    else:
        logger.info("Redis disabled. Skipping initialization.")

    yield

    # Shutdown
    if settings.REDIS_ENABLED:
        try:
            from fastapi_limiter import FastAPILimiter

            await FastAPILimiter.close()
            logger.info("Redis closed.")
        except Exception:
            pass

    logger.info("Application closed.")


app = FastAPI(
    title="LexNorm OCR Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LexNorm OCR Service",
        version="1.0.0",
        description="LexNorm OCR Service",
        routes=app.routes,
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi

for router in routers:
    app.include_router(router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
