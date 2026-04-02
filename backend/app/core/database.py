"""MongoDB connection via Motor (async) and PyMongo (sync for Celery workers)."""

import os

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "perception")

# Override this in tests to inject a mock database
_test_db = None

# Async client for FastAPI
_async_client: AsyncIOMotorClient | None = None


def get_async_db():
    if _test_db is not None:
        return _test_db
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(MONGODB_URL)
    return _async_client[DB_NAME]


def get_sync_db():
    """Sync client for Celery worker processes."""
    if _test_db is not None:
        return _test_db
    client = MongoClient(MONGODB_URL)
    return client[DB_NAME]


async def init_db():
    """Create indexes on startup."""
    db = get_async_db()
    await db.users.create_index("email", unique=True)
    await db.reports.create_index("user_id")
    await db.reports.create_index("created_at")
