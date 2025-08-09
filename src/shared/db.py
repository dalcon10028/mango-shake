from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from shared.settings import get_settings

engine = create_async_engine(
    url=get_settings().db_url,
    echo=True,
    poolclass=NullPool,
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    # autoflush=False,
)

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession | Any, Any]:
    async with async_session() as session:
        yield session

class Base(DeclarativeBase):
    pass



