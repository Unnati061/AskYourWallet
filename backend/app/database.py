from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _engine_kwargs(url: str) -> dict:
    """Dialect-specific engine options (sqlite needs no pool pre-ping/size)."""
    if url.startswith("sqlite"):
        return {}
    # Postgres on a free tier (Supabase/Neon) drops idle connections, so verify
    # a connection is still alive before handing it out, and recycle hourly.
    return {"pool_pre_ping": True, "pool_recycle": 3600}


engine = create_async_engine(settings.DATABASE_URL, echo=False, **_engine_kwargs(settings.DATABASE_URL))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db():
    """Yield an async DB session, auto-closing on exit."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
