# Sää WFS

> **Live Finnish weather observations on a full-screen interactive map — powered by FMI open data.**

Fetches real-time weather data from the Finnish Meteorological Institute (FMI) via OGC WFS 2.0, serves it through a production-grade FastAPI backend with TTL caching, rate limiting, structured JSON logging, and in-process p50/p95/p99 metrics. Renders on a Leaflet.js map with temperature-coded markers, layer switching, bounding-box filtering, Canvas batch rendering for large datasets, and rAF-synced time-series animation.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Tests](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![Data](https://img.shields.io/badge/data-FMI%20CC--BY%204.0-orange)

---

## Features

| | |
|---|---|
| **Live FMI data** | OGC WFS 2.0 GetFeature stored-query, configurable time window up to 48 h |
| **FastAPI backend** | Async REST API with retry/backoff, CORS, Swagger UI at `/docs` |
| **TTL cache** | In-process SHA-256-keyed cache (120 s default) — no redundant WFS calls |
| **Rate limiting** | 30 req/min on observations, 10 req/min on timeseries (slowapi) |
| **Structured logging** | JSON log lines (Datadog / Loki / CloudWatch compatible) via `LOG_FORMAT=json` |
| **Metrics endpoint** | `GET /api/metrics` — p50/p95/p99 latencies, cache hit rate, WFS upstream times |
| **Leaflet.js map** | Full-screen interactive map, two base tile sets, MarkerCluster |
| **5-band colour scale** | Temperature · wind speed · precipitation — distinct colour bands with legend |
| **Bbox filter** | Draw a rectangle on the map to filter observations by region |
| **Time animation** | rAF-synced play/pause/stop — scrub through the last N hours at 1×–8× speed |
| **Canvas batch renderer** | Switches from Leaflet markers to Canvas circles above 300 stations |
| **Docker deploy** | `docker compose up` — backend + nginx frontend, optional Caddy TLS |
| **100% test coverage** | Vitest (JS) + pytest (Python) — all network calls mocked, runs fully offline |

---

## Quick start

### One-command Docker deploy

```bash
docker compose up --build
# Frontend: http://localhost:80
# API:      http://localhost:8000/docs
```

### Local development

```bash
# Backend
cd saa_wfs/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd saa_wfs
npm install && npm run dev
# open http://localhost:5174
```

---

## Architecture

```
Browser (Leaflet.js + ES modules)
  └── frontend/src/
        ├── app.js          Orchestrator — wires all modules
        ├── wfs.js          fetch() → FastAPI, APIError handling
        ├── map.js          Leaflet init, render(geojson, mode), popup builder
        ├── layers.js       Colour bands + legend builder
        ├── animation.js    rAF-synced TimeAnimator (play/pause/stop/seek)
        ├── renderer.js     Canvas batch render for > 300 stations, rafDebounce
        └── ui.js           Toast, loading overlay, topbar counters

FastAPI  (port 8000)
  └── backend/
        ├── main.py         Routes, rate limiting, metrics middleware
        ├── wfs_client.py   requests.Session + urllib3 Retry → FMI WFS
        ├── parser.py       GML/XML → WeatherObservation dataclasses → GeoJSON
        ├── cache.py        TTLCache (SHA-256 key, max_size eviction)
        ├── metrics.py      MetricsCollector — p50/p95/p99, cache hit rate
        └── logging_config.py  _JSONFormatter, setup_from_env()

Docker
  ├── backend/Dockerfile    python:3.12-slim, 2 uvicorn workers
  ├── docker-compose.yml    backend + nginx
  ├── nginx.conf            Security headers, 7-day asset cache, SPA fallback
  └── Caddyfile             Automatic TLS (optional)
```

---

## API reference

```
GET /api/observations
  ?hours=1              required  0 < hours ≤ 48
  &place=Helsinki       optional  Finnish place name
  &bbox=W,S,E,N         optional  WGS-84 bounding box
  &parameters=t2m,ws_10min,ri_10min,rh,p_sea

→ GeoJSON FeatureCollection
  { type, features[], meta: { station_count, generated_at } }

GET /api/timeseries
  ?hours=6  &steps=6  &place=…  &bbox=…

→ Array<{ timestamp: ISO8601, geojson: FeatureCollection }>

GET /api/metrics
→ { cache: { hits, misses, hit_rate },
    wfs_upstream: { p50_ms, p95_ms, samples },
    endpoints: { "/api/observations": { requests, errors, p50_ms, p95_ms, p99_ms } } }

GET /api/cache/stats
→ { size, max_size, ttl_seconds }

GET /healthz
→ { status: "ok", time: ISO8601 }
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CACHE_TTL_SECONDS` | `120` | TTL for FMI WFS response cache |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LOG_FORMAT` | `text` | `text` for dev, `json` for production |

Copy `.env.example` to `.env` and adjust before deploying.

---

## Colour scales

**Temperature**

| Colour | Range |
|---|---|
| Dark blue | Frost — below 0 °C |
| Light blue | Cold — 0 to 10 °C |
| Green | Mild — 10 to 20 °C |
| Orange | Warm — 20 to 28 °C |
| Red | Hot — 28 °C and above |
| Grey | No data |

Wind and precipitation layers use analogous 5-band scales with distinct palettes.

---

## Project layout

```
saa_wfs/
├── backend/
│   ├── main.py                FastAPI app, routes, rate limiting
│   ├── wfs_client.py          FMI WFS HTTP client (retry/backoff)
│   ├── parser.py              GML/XML parser → WeatherObservation
│   ├── cache.py               TTLCache + module-level singleton
│   ├── metrics.py             MetricsCollector + timer() context manager
│   ├── logging_config.py      Structured JSON logging
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── style.css              Glassmorphism dark theme
│   └── src/
│       ├── app.js             Orchestrator
│       ├── wfs.js             API client + APIError
│       ├── map.js             Leaflet map class
│       ├── layers.js          Colour bands + legend
│       ├── animation.js       TimeAnimator (rAF-synced)
│       ├── renderer.js        Canvas batch renderer
│       └── ui.js              Toast / loading / counters
├── tests/
│   ├── test_layers.js         Colour-scale unit tests (100% cov)
│   ├── test_animation.js      TimeAnimator tests, fake timers (100% cov)
│   ├── test_renderer.js       Canvas renderer tests (100% cov)
│   ├── test_parser.py         Python GML parser tests (100% cov)
│   ├── test_wfs_client.py     HTTP client tests, responses mock (100% cov)
│   ├── test_cache.py          TTLCache tests (100% cov)
│   ├── test_metrics.py        MetricsCollector tests (100% cov)
│   ├── test_main.py           FastAPI endpoint tests (100% cov)
│   └── e2e/
│       └── map.spec.js        Playwright E2E — map load, markers, panel
├── docker-compose.yml
├── nginx.conf
├── Caddyfile                  Optional automatic TLS
├── vitest.config.js           100% branch coverage enforced
├── playwright.config.js       E2E on Chromium + Firefox
├── package.json
└── .github/workflows/ci.yml   Backend + frontend + E2E + Docker build
```

---

## Testing

```bash
# JavaScript — Vitest (100% coverage enforced)
npm install
npm test

# Python — pytest
pip install -r backend/requirements-dev.txt
pytest tests/ -v --cov=backend --cov-report=term-missing

# End-to-end — Playwright
npm run test:e2e
```

All network calls are mocked. The full suite runs **offline**.

---

## CI / CD

```
push / PR
  │
  ├── backend-tests     pytest --cov=backend (100% required)
  ├── frontend-tests    npm test (Vitest, 100% required)
  ├── e2e-tests         Playwright on Chromium + Firefox
  └── docker-build      docker compose build (smoke test)
```

---

## Architecture decisions

| Decision | Rationale |
|---|---|
| TTL cache in-process | Eliminates repeated FMI WFS calls during burst traffic |
| slowapi rate limiting | Protects the FMI upstream from abusive clients |
| Canvas batch renderer | Leaflet DOM markers degrade above 300 stations; Canvas stays fast |
| rAF-synced animation | vsync-aligned dispatch prevents dropped frames on slow connections |
| `_JSONFormatter` | One log line per request, structured for log aggregation platforms |
| `MetricsCollector` | No Prometheus dependency — self-contained, surfaced via `/api/metrics` |

---

## Implemented

- WFS basic queries
- GeoJSON / GML parsing
- Leaflet map + marker visualisation
- Bounding-box filter + interactive layers
- Time-series animation
- Multiple data sources + UI coordination
- TTL cache + rate limiting
- Canvas batch renderer (> 300 stations)
- Structured JSON logging
- In-process metrics with percentiles
- Docker + nginx + optional TLS

---

## Data licence

Weather data © Finnish Meteorological Institute.
Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## License

MIT
