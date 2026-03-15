"""
FastAPI backend for saa-wfs.

Endpoints
---------
GET /api/observations   Latest weather observations as GeoJSON
GET /api/timeseries     Multi-step time series for animation
GET /healthz            Health check
GET /api/cache/stats    Cache diagnostics (dev)
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .wfs_client import FMIWFSClient, WFSRequest
from .parser import WFSParser, WeatherObservation
from .cache import TTLCache, init_cache, get_cache

# ── Config ────────────────────────────────────────────────────

_CACHE_TTL   = float(os.getenv("CACHE_TTL_SECONDS", "120"))
_ORIGINS     = os.getenv("ALLOWED_ORIGINS", "*").split(",")
_LOG_LEVEL   = os.getenv("LOG_LEVEL", "info").upper()

logging.basicConfig(level=getattr(logging, _LOG_LEVEL, logging.INFO))
log = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="Sää WFS API",
    description="Finnish weather observations from FMI open WFS, served as GeoJSON.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    init_cache(ttl=_CACHE_TTL)
    log.info("saa-wfs backend started  cache_ttl=%ds  origins=%s", int(_CACHE_TTL), _ORIGINS)


# ── Routes ───────────────────────────────────────────────────


@app.get("/healthz", tags=["meta"])
async def health() -> dict:
    cache = get_cache()
    return {
        "status":      "ok",
        "time":        datetime.now(tz=timezone.utc).isoformat(),
        "cache_size":  len(cache),
    }


@app.get("/api/cache/stats", tags=["meta"])
async def cache_stats() -> dict:
    cache = get_cache()
    return {"entries": len(cache), "ttl_seconds": _CACHE_TTL}


@app.get("/api/observations", tags=["weather"])
@limiter.limit("30/minute")
async def observations(
    request:    Request,
    hours:      Annotated[float, Query(gt=0, le=48, description="Hours back from now")] = 1.0,
    place:      Annotated[str | None, Query(max_length=80)] = None,
    bbox:       Annotated[str | None, Query()] = None,
    parameters: Annotated[str, Query()] = "t2m,ws_10min,ri_10min,rh,p_sea",
) -> JSONResponse:
    cache = get_cache()
    cache_key = TTLCache.make_key("obs", str(hours), str(place), str(bbox), parameters)

    cached = cache.get(cache_key)
    if cached is not None:
        cached["meta"]["from_cache"] = True
        return JSONResponse(cached)

    req = WFSRequest(hours_back=hours, place=place, bbox=bbox, parameters=parameters)
    xml = _fetch_xml(req)
    obs = WFSParser().parse(xml)
    geojson = _to_geojson(obs)
    geojson["meta"] = {
        "station_count": len(obs),
        "fetched_at":    datetime.now(tz=timezone.utc).isoformat(),
        "hours_back":    hours,
        "from_cache":    False,
    }
    cache.set(cache_key, geojson)
    return JSONResponse(geojson)


@app.get("/api/timeseries", tags=["weather"])
@limiter.limit("10/minute")
async def timeseries(
    request: Request,
    hours: Annotated[float, Query(gt=0, le=48)] = 6.0,
    steps: Annotated[int,   Query(gt=0, le=24)] = 6,
    place: Annotated[str | None, Query(max_length=80)] = None,
    bbox:  Annotated[str | None, Query()] = None,
) -> JSONResponse:
    """Return ordered [ { timestamp, geojson } ] for animation, oldest → newest."""
    cache = get_cache()
    cache_key = TTLCache.make_key("ts", str(hours), str(steps), str(place), str(bbox))

    cached = cache.get(cache_key)
    if cached is not None:
        return JSONResponse(cached)

    step_hours = hours / steps
    frames: list[dict] = []

    for i in range(steps):
        end_h = hours - i * step_hours
        req   = WFSRequest(hours_back=end_h, place=place, bbox=bbox)
        try:
            xml  = _fetch_xml(req)
            obs  = WFSParser().parse(xml)
            frames.append({
                "timestamp": _step_timestamp(end_h),
                "geojson":   _to_geojson(obs),
            })
        except Exception as exc:
            log.warning("Timeseries step %d/%d failed: %s", i + 1, steps, exc)

    frames.reverse()   # oldest → newest
    cache.set(cache_key, frames)
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
        "type":     "FeatureCollection",
        "features": [_obs_to_feature(o) for o in observations],
    }


def _obs_to_feature(o: WeatherObservation) -> dict:
    return {
        "type":     "Feature",
        "geometry": {"type": "Point", "coordinates": [o.lon, o.lat]},
        "properties": {
            "station_name":      o.station_name,
            "temperature_c":     _safe(o.temperature_c),
            "wind_speed_ms":     _safe(o.wind_speed_ms),
            "precipitation_mmh": _safe(o.precipitation_mmh),
            "humidity_pct":      _safe(o.humidity_pct),
            "pressure_hpa":      _safe(o.pressure_hpa),
            "observed_at":       o.observed_at.isoformat(),
            "extra":             {k: _safe(v) for k, v in o.extra.items()},
        },
    }


def _safe(v: float) -> float | None:
    return None if math.isnan(v) else v


def _step_timestamp(hours_back: float) -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)
    return dt.isoformat()
