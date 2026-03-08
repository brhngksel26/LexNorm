from collections.abc import AsyncGenerator
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import Boolean, DateTime, MetaData, create_engine, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import settings

# TODO: Get DATABASE_URL from environment variables
DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)


metadata = MetaData(schema=settings.DB_SCHEMA)


class RemoveBaseFieldsMixin:
    created_date = None
    updated_date = None
    is_deleted = None


class BaseModel(DeclarativeBase):
    __abstract__ = True
    metadata = metadata

    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        return {field.name: getattr(self, field.name) for field in self.__table__.c}


def create_engine_for_sessionmaker(is_worker: bool = False):
    if is_worker:
        return create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)
    return create_async_engine(
        DATABASE_URL,
        pool_size=40,
        max_overflow=20,
        pool_recycle=3600,
        isolation_level="AUTOCOMMIT",
    )


sync_engine = create_engine(
    f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
    pool_size=40,
    max_overflow=20,
    pool_recycle=3600,
    isolation_level="AUTOCOMMIT",
)

engine = create_engine_for_sessionmaker(is_worker=False)
worker_engine = create_engine_for_sessionmaker(is_worker=True)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
worker_async_session_maker = sessionmaker(
    worker_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def create_redis_pool():
    return aioredis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
    )


redis_pool = create_redis_pool()
