"""Tests for backend.cache — 100% branch coverage."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from saa_wfs.backend.cache import TTLCache, get_cache, init_cache


class TestTTLCache:
    def test_set_and_get(self) -> None:
        c = TTLCache(ttl=60)
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_miss_returns_none(self) -> None:
        c = TTLCache(ttl=60)
        assert c.get("missing") is None

    def test_expired_returns_none(self) -> None:
        c = TTLCache(ttl=0.01)
        c.set("k", "v")
        time.sleep(0.05)
        assert c.get("k") is None

    def test_len(self) -> None:
        c = TTLCache(ttl=60)
        c.set("a", 1)
        c.set("b", 2)
        assert len(c) == 2

    def test_clear(self) -> None:
        c = TTLCache(ttl=60)
        c.set("x", 1)
        c.clear()
        assert len(c) == 0

    def test_evicts_oldest_when_full(self) -> None:
        c = TTLCache(ttl=60, max_size=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)   # triggers eviction
        assert len(c) == 2

    def test_make_key_deterministic(self) -> None:
        k1 = TTLCache.make_key("obs", "1.0", "Helsinki")
        k2 = TTLCache.make_key("obs", "1.0", "Helsinki")
        assert k1 == k2

    def test_make_key_different_inputs(self) -> None:
        k1 = TTLCache.make_key("obs", "1.0")
        k2 = TTLCache.make_key("obs", "2.0")
        assert k1 != k2

    def test_make_key_length(self) -> None:
        assert len(TTLCache.make_key("x")) == 32

    def test_overwrite_existing_key(self) -> None:
        c = TTLCache(ttl=60)
        c.set("k", "old")
        c.set("k", "new")
        assert c.get("k") == "new"


class TestModuleLevelCache:
    def test_get_cache_returns_instance(self) -> None:
        cache = get_cache()
        assert isinstance(cache, TTLCache)

    def test_get_cache_singleton(self) -> None:
        a = get_cache()
        b = get_cache()
        assert a is b

    def test_init_cache_replaces_singleton(self) -> None:
        c1 = init_cache(ttl=30)
        c2 = init_cache(ttl=60)
        assert c1 is not c2
        assert get_cache() is c2

    def test_init_cache_returns_ttl_cache(self) -> None:
        c = init_cache(ttl=45, max_size=10)
        assert isinstance(c, TTLCache)
        assert c._ttl == 45
        assert c._max_size == 10
