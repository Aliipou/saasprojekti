"""Tests for backend.metrics — 100% branch coverage."""

from __future__ import annotations

import time

import pytest

from saa_wfs.backend.metrics import (
    MetricsCollector,
    get_metrics,
    timer,
    _pct,
)


class TestMetricsCollector:
    def setup_method(self) -> None:
        self.m = MetricsCollector()

    def test_initial_snapshot_is_empty(self) -> None:
        s = self.m.snapshot()
        assert s["cache"]["hits"] == 0
        assert s["cache"]["misses"] == 0
        assert s["endpoints"] == {}

    def test_record_request(self) -> None:
        self.m.record_request("/api/observations", 120.0)
        s = self.m.snapshot()
        assert s["endpoints"]["/api/observations"]["requests"] == 1
        assert s["endpoints"]["/api/observations"]["errors"] == 0

    def test_record_error(self) -> None:
        self.m.record_request("/api/observations", 50.0, is_error=True)
        s = self.m.snapshot()
        assert s["endpoints"]["/api/observations"]["errors"] == 1

    def test_cache_hit_miss(self) -> None:
        self.m.record_cache_hit()
        self.m.record_cache_hit()
        self.m.record_cache_miss()
        s = self.m.snapshot()
        assert s["cache"]["hits"] == 2
        assert s["cache"]["misses"] == 1
        assert s["cache"]["hit_rate"] == pytest.approx(2 / 3, rel=1e-3)

    def test_hit_rate_zero_when_no_requests(self) -> None:
        s = self.m.snapshot()
        assert s["cache"]["hit_rate"] == 0.0

    def test_wfs_latency(self) -> None:
        for ms in [10.0, 20.0, 30.0]:
            self.m.record_wfs_latency(ms)
        s = self.m.snapshot()
        assert s["wfs_upstream"]["samples"] == 3
        assert s["wfs_upstream"]["p50_ms"] is not None

    def test_percentiles_none_when_empty(self) -> None:
        s = self.m.snapshot()
        assert s["wfs_upstream"]["p50_ms"] is None

    def test_multiple_endpoints(self) -> None:
        self.m.record_request("/api/observations", 100.0)
        self.m.record_request("/api/timeseries", 200.0)
        s = self.m.snapshot()
        assert len(s["endpoints"]) == 2

    def test_reset(self) -> None:
        self.m.record_request("/api/observations", 100.0)
        self.m.record_cache_hit()
        self.m.reset()
        s = self.m.snapshot()
        assert s["endpoints"] == {}
        assert s["cache"]["hits"] == 0

    def test_p50_p95_p99_computed(self) -> None:
        for i in range(1, 101):
            self.m.record_request("/ep", float(i))
        s = self.m.snapshot()
        ep = s["endpoints"]["/ep"]
        assert ep["p50_ms"] is not None
        assert ep["p95_ms"] is not None
        assert ep["p99_ms"] is not None
        assert ep["p50_ms"] <= ep["p95_ms"] <= ep["p99_ms"]


class TestTimerContext:
    def test_records_timing_on_success(self) -> None:
        m = MetricsCollector()

        class _FakeMetrics:
            calls: list = []
            def record_request(self, ep, dur, is_error=False):
                self.calls.append((ep, dur, is_error))

        import saa_wfs.backend.metrics as mod
        orig = mod.get_metrics
        fm = _FakeMetrics()
        mod.get_metrics = lambda: fm
        try:
            with timer("/ep"):
                pass
            assert len(fm.calls) == 1
            assert fm.calls[0][0] == "/ep"
            assert fm.calls[0][2] is False
        finally:
            mod.get_metrics = orig

    def test_records_error_on_exception(self) -> None:
        import saa_wfs.backend.metrics as mod
        calls = []

        class _FM:
            def record_request(self, ep, dur, is_error=False):
                calls.append(is_error)

        orig = mod.get_metrics
        mod.get_metrics = lambda: _FM()
        try:
            try:
                with timer("/ep"):
                    raise ValueError("oops")
            except ValueError:
                pass
            assert calls == [True]
        finally:
            mod.get_metrics = orig


class TestPct:
    def test_returns_none_for_empty(self) -> None:
        assert _pct([], 50) is None

    def test_single_value(self) -> None:
        result = _pct([42.0], 50)
        assert result == pytest.approx(42.0)

    def test_p50_midpoint(self) -> None:
        result = _pct(list(range(1, 101, 1)), 50)
        assert result is not None


class TestGetMetrics:
    def test_returns_instance(self) -> None:
        assert isinstance(get_metrics(), MetricsCollector)

    def test_singleton(self) -> None:
        assert get_metrics() is get_metrics()
