"""MongoDB connection via Motor (async) and PyMongo (sync for Celery workers)."""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from app.core.config import settings

# Override this in tests to inject a mock database
_test_db = None

# Async client for FastAPI
_async_client: AsyncIOMotorClient | None = None


def get_async_db():
    if _test_db is not None:
        return _test_db
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.mongodb_url)
    return _async_client[settings.mongodb_db]


_sync_client: MongoClient | None = None


def get_sync_db():
    """Sync client for Celery worker processes."""
    if _test_db is not None:
        return _test_db
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.mongodb_url)
    return _sync_client[settings.mongodb_db]


async def init_db():
    """Create indexes on startup."""
    db = get_async_db()
    await db.users.create_index("email", unique=True)
    await db.reports.create_index([("user_id", 1), ("created_at", -1)])
