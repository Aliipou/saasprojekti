"""
Simple in-process TTL cache for WFS responses.

Avoids hammering FMI WFS on every browser refresh.
Thread-safe for use with uvicorn's async workers.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    """Lightweight dict-backed TTL cache — no Redis required.

    Parameters
    ----------
    ttl:
        Seconds until an entry expires.
    max_size:
        Maximum number of entries before oldest are evicted.
    """

    def __init__(self, ttl: float = 120.0, max_size: int = 256) -> None:
        self._ttl      = ttl
        self._max_size = max_size
        self._store:  dict[str, _Entry] = {}
        self._lock    = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                log.debug("Cache miss (expired): %s", key[:40])
                return None
            log.debug("Cache hit: %s", key[:40])
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max_size:
                # Evict the entry with the earliest expiry
                oldest = min(self._store, key=lambda k: self._store[k].expires_at)
                del self._store[oldest]
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    @staticmethod
    def make_key(*parts: str) -> str:
        """Stable cache key from arbitrary string parts."""
        raw = ":".join(str(p) for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


# Module-level singleton — imported by main.py
_cache: TTLCache | None = None


def get_cache() -> TTLCache:
    """Return the process-wide cache instance (created lazily)."""
    global _cache
    if _cache is None:
        _cache = TTLCache()
    return _cache


def init_cache(ttl: float, max_size: int = 256) -> TTLCache:
    """Initialise (or replace) the global cache — call once at startup."""
    global _cache
    _cache = TTLCache(ttl=ttl, max_size=max_size)
    log.info("Cache initialised: TTL=%ds, max_size=%d", int(ttl), max_size)
    return _cache
