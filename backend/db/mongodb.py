"""
db/mongodb.py — Async Motor client singleton for ConstitutionAI.
Provides a shared MongoDB client and database accessor.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from config import config
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the shared Motor client (lazy init)."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            config.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_db():
    """Return the application database."""
    return get_client()[config.DB_NAME]


async def check_connection() -> bool:
    """Ping MongoDB to verify connectivity. Returns True if healthy."""
    try:
        client = get_client()
        await client.admin.command("ping")
        logger.info("MongoDB connection OK at %s", config.MONGODB_URI)
        return True
    except ServerSelectionTimeoutError as exc:
        logger.error("MongoDB unreachable: %s", exc)
        return False


async def close_connection() -> None:
    """Gracefully close the Motor client."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


# Collection accessors -------------------------------------------------------

def sessions_col():
    return get_db()["sessions"]


def article_progress_col():
    return get_db()["article_progress"]


def test_results_col():
    return get_db()["test_results"]
