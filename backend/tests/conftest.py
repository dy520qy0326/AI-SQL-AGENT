import pytest_asyncio
from app.db.engine import async_session as _async_session_factory, Base, engine, init_db


@pytest_asyncio.fixture
async def async_session():
    """Provides an async DB session (for store/detector tests)."""
    await init_db()
    async with _async_session_factory() as session:
        yield session
        await session.rollback()
