"""
[HAIKU] Rate Limiter — foydalanuvchi so'rovlarini cheklaydi.
Bir foydalanuvchi MIN_INTERVAL soniyada 1 ta so'rov yuborishi mumkin.
"""
import asyncio
import logging
from collections import defaultdict
from time import monotonic

logger = logging.getLogger(__name__)

MIN_INTERVAL: float = 15.0  # soniya: qidiruv orasidagi minimum vaqt


class RateLimiter:
    def __init__(self, min_interval: float = MIN_INTERVAL):
        self._last_request: dict[int, float] = defaultdict(float)
        self._lock = asyncio.Lock()
        self.min_interval = min_interval

    async def check(self, user_id: int) -> float:
        """
        Returns 0.0 agar so'rov ruxsat etilgan bo'lsa.
        Returns > 0.0 — kutish kerak bo'lgan soniyalar soni.
        """
        async with self._lock:
            now = monotonic()
            elapsed = now - self._last_request[user_id]
            if elapsed < self.min_interval:
                wait = self.min_interval - elapsed
                logger.debug("Rate limit: user=%d, wait=%.1fs", user_id, wait)
                return wait
            self._last_request[user_id] = now
            return 0.0

    def reset(self, user_id: int) -> None:
        self._last_request[user_id] = 0.0


rate_limiter = RateLimiter()
