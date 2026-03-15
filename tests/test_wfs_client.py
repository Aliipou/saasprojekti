"""Tests for saa_wfs.wfs_client — 100% branch coverage."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses as resp_lib

from saa_wfs.wfs_client import FMIWFSClient, WFSRequest, _fmt_iso


# ---------------------------------------------------------------------------
# _fmt_iso
# ---------------------------------------------------------------------------


class TestFmtIso:
    def test_format(self) -> None:
        dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        assert _fmt_iso(dt) == "2024-01-15T12:30:00Z"


# ---------------------------------------------------------------------------
# WFSRequest params
# ---------------------------------------------------------------------------


class TestWFSRequestParams:
    def test_default_fields(self) -> None:
        r = WFSRequest()
        assert r.hours_back == 1.0
        assert r.bbox is None
        assert r.place is None

    def test_custom_fields(self) -> None:
        r = WFSRequest(hours_back=3.0, bbox="20,60,30,70", place="Oulu")
        assert r.hours_back == 3.0
        assert r.bbox == "20,60,30,70"
        assert r.place == "Oulu"


# ---------------------------------------------------------------------------
# FMIWFSClient — HTTP interaction
# ---------------------------------------------------------------------------


@resp_lib.activate
class TestFMIWFSClientFetch:
    _XML = b"<wfs:FeatureCollection/>"
    _URL = "https://opendata.fmi.fi/wfs"

    def _register_ok(self, body: bytes = _XML) -> None:
        resp_lib.add(
            resp_lib.GET,
            self._URL,
            body=body,
            status=200,
            content_type="application/xml",
        )

    def test_successful_fetch_returns_xml(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            result = client.fetch(WFSRequest())
        assert "<wfs:FeatureCollection" in result.xml_text
        assert isinstance(result.fetched_at, datetime)
        assert result.fetched_at.tzinfo is not None

    def test_elapsed_ms_positive(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            result = client.fetch(WFSRequest())
        assert result.elapsed_ms >= 0

    def test_url_stored(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            result = client.fetch(WFSRequest())
        assert "opendata.fmi.fi" in result.url

    def test_bbox_added_to_params(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            result = client.fetch(WFSRequest(bbox="20,60,30,70"))
        assert "bbox=20%2C60%2C30%2C70" in result.url or "bbox=" in result.url

    def test_place_added_to_params(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            result = client.fetch(WFSRequest(place="Tampere"))
        assert "place=Tampere" in result.url

    def test_http_error_raises(self) -> None:
        resp_lib.add(resp_lib.GET, self._URL, status=500, body="Server Error")
        with FMIWFSClient() as client:
            with pytest.raises(requests.HTTPError):
                client.fetch(WFSRequest())

    def test_404_raises(self) -> None:
        resp_lib.add(resp_lib.GET, self._URL, status=404, body="Not Found")
        with FMIWFSClient() as client:
            with pytest.raises(requests.HTTPError):
                client.fetch(WFSRequest())

    def test_context_manager_closes_session(self) -> None:
        self._register_ok()
        client = FMIWFSClient()
        with client:
            client.fetch(WFSRequest())
        # After exit, calling close again should not raise
        client.close()

    def test_custom_base_url(self) -> None:
        custom = "https://example.com/wfs"
        resp_lib.add(
            resp_lib.GET, custom, body=self._XML, status=200,
            content_type="application/xml",
        )
        with FMIWFSClient(base_url=custom) as client:
            result = client.fetch(WFSRequest())
        assert "example.com" in result.url

    def test_user_agent_header_set(self) -> None:
        self._register_ok()
        with FMIWFSClient() as client:
            _ = client.fetch(WFSRequest())
        # Verify the request carried our User-Agent
        assert resp_lib.calls[0].request.headers.get("User-Agent") == "saa-wfs/1.0"
