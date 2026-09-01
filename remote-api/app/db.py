from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.indexes import ensure_indexes as _ensure_indexes

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db():
    return get_client()[settings.mongo_db]


async def ensure_indexes() -> None:
    await _ensure_indexes(get_db())
