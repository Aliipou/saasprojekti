"""
metrics.py — Lightweight in-process metrics collector.

Tracks: request counts, error counts, response times,
        cache hit/miss, WFS upstream latency.

No external dependency (Prometheus, StatsD) required.
Exposed via GET /api/metrics as JSON.
"""

from __future__ import annotations

import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Deque


@dataclass
class _Bucket:
    count:     int   = 0
    errors:    int   = 0
    durations: Deque[float] = field(default_factory=lambda: deque(maxlen=500))


class MetricsCollector:
    """
    Thread-safe metrics store.

    Metrics collected
    -----------------
    requests      total API call count per endpoint
    errors        4xx/5xx count per endpoint
    latency_ms    rolling window of response times (last 500 per endpoint)
    cache_hits    cache hit counter
    cache_misses  cache miss counter
    wfs_latency   rolling window of WFS upstream response times (ms)
    """

    def __init__(self) -> None:
        self._lock:       Lock = Lock()
        self._endpoints:  dict[str, _Bucket] = {}
        self._cache_hits: int  = 0
        self._cache_miss: int  = 0
        self._wfs_times:  Deque[float] = deque(maxlen=200)

    # ── Recording ─────────────────────────────────────────────

    def record_request(self, endpoint: str, duration_ms: float, is_error: bool = False) -> None:
        with self._lock:
            b = self._endpoints.setdefault(endpoint, _Bucket())
            b.count += 1
            if is_error:
                b.errors += 1
            b.durations.append(duration_ms)

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_miss += 1

    def record_wfs_latency(self, ms: float) -> None:
        with self._lock:
            self._wfs_times.append(ms)

    # ── Snapshot ──────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            endpoints = {}
            for name, b in self._endpoints.items():
                durs = list(b.durations)
                endpoints[name] = {
                    "requests":  b.count,
                    "errors":    b.errors,
                    "p50_ms":    _pct(durs, 50),
                    "p95_ms":    _pct(durs, 95),
                    "p99_ms":    _pct(durs, 99),
                }
            wfs = list(self._wfs_times)
            total = self._cache_hits + self._cache_miss
            return {
                "cache": {
                    "hits":       self._cache_hits,
                    "misses":     self._cache_miss,
                    "hit_rate":   round(self._cache_hits / total, 4) if total else 0.0,
                },
                "wfs_upstream": {
                    "p50_ms": _pct(wfs, 50),
                    "p95_ms": _pct(wfs, 95),
                    "samples": len(wfs),
                },
                "endpoints": endpoints,
            }

    def reset(self) -> None:
        with self._lock:
            self._endpoints   = {}
            self._cache_hits  = 0
            self._cache_miss  = 0
            self._wfs_times.clear()


# ── Module-level singleton ────────────────────────────────────

_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# ── Timing context manager ────────────────────────────────────

class _Timer:
    def __init__(self, metrics: MetricsCollector, endpoint: str) -> None:
        self._m = metrics
        self._ep = endpoint
        self._t0 = 0.0
        self._error = False

    def set_error(self) -> None:
        self._error = True

    def __enter__(self) -> "_Timer":
        self._t0 = time.monotonic()
        return self

    def __exit__(self, exc_type, *_: object) -> None:
        elapsed = (time.monotonic() - self._t0) * 1000
        self._m.record_request(self._ep, elapsed, is_error=(exc_type is not None or self._error))


def timer(endpoint: str) -> _Timer:
    """Context manager that records endpoint timing automatically."""
    return _Timer(get_metrics(), endpoint)


# ── Helpers ───────────────────────────────────────────────────

def _pct(data: list[float], p: int) -> float | None:
    if not data:
        return None
    return round(statistics.quantiles(data, n=100)[p - 1], 2)
