"""
[SONNET] In-memory TTL Cache — bir xil qidiruv qayta API chaqirmaydi.
Redis kerak emas — bepul, process ichida ishlaydi.
TTL: 30 daqiqa. Max: 500 yozuv.
"""
import logging
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TTL_SECONDS: float = 1800.0   # 30 daqiqa
_MAX_SIZE: int = 500


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl: float = _TTL_SECONDS, max_size: int = _MAX_SIZE):
        self._store: dict[str, _Entry] = {}
        self.ttl = ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if monotonic() > entry.expires_at:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        logger.debug("Cache HIT: '%s' (hits=%d, misses=%d)", key[:40], self._hits, self._misses)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self.max_size:
            # FIFO eviction — eng eski yozuvni o'chir
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
        self._store[key] = _Entry(value=value, expires_at=monotonic() + self.ttl)
        logger.debug("Cache SET: '%s' (size=%d)", key[:40], len(self._store))

    def clear(self) -> None:
        self._store.clear()

    @property
    def stats(self) -> dict:
        return {
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, self._hits + self._misses),
        }


search_cache = TTLCache()
