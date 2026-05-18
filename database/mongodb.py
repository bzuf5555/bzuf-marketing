import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect(uri: str) -> None:
    global _client, _db
    _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    _db = _client["bzuf_marketing"]
    await _db["users"].create_index("user_id", unique=True)
    logger.info("MongoDB connected")


async def disconnect() -> None:
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _db


async def upsert_user(
    user_id: int,
    phone: str,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
) -> None:
    db = get_db()
    await db["users"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "phone": phone,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                "search_count": 0,
            },
        },
        upsert=True,
    )
    logger.info("User %d upserted", user_id)


async def user_exists(user_id: int) -> bool:
    db = get_db()
    doc = await db["users"].find_one({"user_id": user_id}, {"_id": 1})
    return doc is not None


async def increment_search_count(user_id: int) -> None:
    db = get_db()
    await db["users"].update_one(
        {"user_id": user_id},
        {"$inc": {"search_count": 1}},
    )
