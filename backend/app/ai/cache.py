import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository

logger = logging.getLogger(__name__)


def make_cache_key(schema_hash: str, prompt_hash: str) -> str:
    raw = f"{schema_hash}:{prompt_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(db: AsyncSession, cache_key: str) -> dict | None:
    repo = Repository(db)
    return await repo.get_cached(cache_key)


async def set_cache(
    db: AsyncSession,
    cache_key: str,
    prompt_hash: str,
    schema_hash: str,
    response: dict,
    ttl_hours: int = 24,
) -> None:
    repo = Repository(db)
    await repo.set_cache(cache_key, prompt_hash, schema_hash, response, ttl_hours)


async def clear_all_cache(db: AsyncSession) -> int:
    repo = Repository(db)
    return await repo.clear_all_cache()


async def delete_expired_cache(db: AsyncSession) -> int:
    repo = Repository(db)
    return await repo.delete_expired_cache()
