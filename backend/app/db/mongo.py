from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.db.indexes import ensure_indexes_async

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db():
    return get_client()[settings.mongo_db]


async def ensure_indexes() -> None:
    await ensure_indexes_async(get_db())
