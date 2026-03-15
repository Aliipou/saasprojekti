"""
FastAPI backend for saa-wfs.

Endpoints
---------
GET /api/observations   Latest weather observations as GeoJSON
GET /api/timeseries     Multi-step time series for animation
GET /healthz            Health check
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .wfs_client import FMIWFSClient, WFSRequest
from .parser import WFSParser, WeatherObservation

log = logging.getLogger(__name__)

app = FastAPI(
    title="Sää WFS API",
    description="Finnish weather observations from FMI open WFS, served as GeoJSON.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten in production
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────


@app.get("/healthz", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "time": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/api/observations", tags=["weather"])
async def observations(
    hours:      Annotated[float, Query(gt=0, le=48, description="Hours back from now")] = 1.0,
    place:      Annotated[str | None, Query(max_length=80)] = None,
    bbox:       Annotated[str | None, Query()] = None,
    parameters: Annotated[str, Query()] = "t2m,ws_10min,ri_10min,rh,p_sea",
) -> JSONResponse:
    req = WFSRequest(hours_back=hours, place=place, bbox=bbox, parameters=parameters)
    xml = _fetch_xml(req)
    obs = WFSParser().parse(xml)
    geojson = _to_geojson(obs)
    geojson["meta"] = {
        "station_count": len(obs),
        "fetched_at":    datetime.now(tz=timezone.utc).isoformat(),
        "hours_back":    hours,
    }
    return JSONResponse(geojson)


@app.get("/api/timeseries", tags=["weather"])
async def timeseries(
    hours: Annotated[float, Query(gt=0, le=48)] = 6.0,
    steps: Annotated[int,   Query(gt=0, le=24)] = 6,
    place: Annotated[str | None, Query(max_length=80)] = None,
    bbox:  Annotated[str | None, Query()] = None,
) -> JSONResponse:
    """
    Returns an ordered list of { timestamp, geojson } objects — one per time step,
    oldest → newest.  Steps are evenly distributed over *hours*.
    """
    import asyncio
    step_hours = hours / steps
    frames = []

    for i in range(steps):
        start_h = hours - (i + 1) * step_hours
        end_h   = hours - i * step_hours
        req = WFSRequest(hours_back=end_h, place=place, bbox=bbox)
        try:
            xml = _fetch_xml(req)
            obs = WFSParser().parse(xml)
            frames.append({
                "timestamp": _step_timestamp(end_h),
                "geojson":   _to_geojson(obs),
            })
        except Exception as exc:
            log.warning("Step %d/%d failed: %s", i + 1, steps, exc)

    # Return oldest→newest
    frames.reverse()
    return JSONResponse(frames)


# ── Helpers ──────────────────────────────────────────────────


def _fetch_xml(req: WFSRequest) -> str:
    try:
        with FMIWFSClient() as client:
            return client.fetch(req).xml_text
    except Exception as exc:
        log.error("WFS fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"WFS upstream error: {exc}") from exc


def _to_geojson(observations: list[WeatherObservation]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [_obs_to_feature(o) for o in observations],
    }


def _obs_to_feature(o: WeatherObservation) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [o.lon, o.lat]},
        "properties": {
            "station_name":        o.station_name,
            "temperature_c":       _safe(o.temperature_c),
            "wind_speed_ms":       _safe(o.wind_speed_ms),
            "precipitation_mmh":   _safe(o.precipitation_mmh),
            "humidity_pct":        _safe(o.humidity_pct),
            "pressure_hpa":        _safe(o.pressure_hpa),
            "observed_at":         o.observed_at.isoformat(),
            "extra":               {k: _safe(v) for k, v in o.extra.items()},
        },
    }


def _safe(v: float) -> float | None:
    import math
    return None if math.isnan(v) else v


def _step_timestamp(hours_back: float) -> str:
    from datetime import timedelta
    dt = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)
    return dt.isoformat()
