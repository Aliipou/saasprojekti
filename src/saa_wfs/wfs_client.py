"""
FMI WFS client — fetches weather observations from the Finnish Meteorological
Institute's open WFS endpoint.

Reference: https://en.ilmatieteenlaitos.fi/open-data-manual-wfs-examples
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FMI_WFS_BASE = "https://opendata.fmi.fi/wfs"
_DEFAULT_STORED_QUERY = "fmi::observations::weather::simple"
_DEFAULT_PARAMETERS = "t2m,ws_10min,ri_10min,rh,p_sea"
_REQUEST_TIMEOUT = 30  # seconds
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 1.0


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class WFSRequest(NamedTuple):
    """Parameters for a WFS GetFeature stored-query call."""

    stored_query_id: str = _DEFAULT_STORED_QUERY
    parameters: str = _DEFAULT_PARAMETERS
    hours_back: float = 1.0
    bbox: str | None = None  # "lon_min,lat_min,lon_max,lat_max" (WGS-84)
    place: str | None = None  # e.g. "Helsinki"


class WFSResponse(NamedTuple):
    """Raw HTTP response envelope."""

    xml_text: str
    fetched_at: datetime
    url: str
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FMIWFSClient:
    """
    Thin HTTP client for the FMI WFS open-data endpoint.

    Uses an internal :class:`requests.Session` with retry/backoff so transient
    network errors are handled gracefully.
    """

    def __init__(
        self,
        base_url: str = FMI_WFS_BASE,
        timeout: int = _REQUEST_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._session = self._build_session(max_retries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, req: WFSRequest) -> WFSResponse:
        """Fetch observations and return the raw XML string.

        Raises
        ------
        requests.HTTPError
            For 4xx/5xx responses that exhaust retries.
        requests.ConnectionError / requests.Timeout
            For network-level failures.
        """
        params = self._build_params(req)
        logger.debug("GET %s  params=%s", self._base_url, params)

        t0 = time.monotonic()
        resp = self._session.get(self._base_url, params=params, timeout=self._timeout)
        elapsed = (time.monotonic() - t0) * 1000

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            logger.error(
                "WFS request failed  status=%d  body=%s",
                resp.status_code,
                resp.text[:500],
            )
            raise

        logger.info(
            "WFS response OK  status=%d  size=%d B  elapsed=%.0f ms",
            resp.status_code,
            len(resp.content),
            elapsed,
        )
        return WFSResponse(
            xml_text=resp.text,
            fetched_at=datetime.now(tz=timezone.utc),
            url=resp.url,
            elapsed_ms=elapsed,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "FMIWFSClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_params(self, req: WFSRequest) -> dict[str, str]:
        now = datetime.now(tz=timezone.utc)
        starttime = now - timedelta(hours=req.hours_back)
        params: dict[str, str] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "storedquery_id": req.stored_query_id,
            "parameters": req.parameters,
            "starttime": _fmt_iso(starttime),
            "endtime": _fmt_iso(now),
        }
        if req.bbox:
            params["bbox"] = req.bbox
        if req.place:
            params["place"] = req.place
        return params

    @staticmethod
    def _build_session(max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"Accept": "application/xml", "User-Agent": "saa-wfs/1.0"})
        return session


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _fmt_iso(dt: datetime) -> str:
    """Format datetime as ISO-8601 UTC string expected by FMI WFS."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
