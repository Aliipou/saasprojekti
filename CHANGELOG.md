# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

---

## [1.1.0] — 2026-03-16

### Added
- **In-process TTL cache** (`backend/cache.py`) — avoids hammering FMI WFS on every refresh
- **Rate limiting** via `slowapi` — 30 req/min for observations, 10 req/min for timeseries
- **Docker + docker-compose** — single `docker compose up` deploys backend + nginx frontend
- **nginx reverse proxy** — security headers, asset caching, API proxy
- **`/api/cache/stats`** endpoint for diagnostics
- **Playwright E2E tests** — map load, marker visibility, panel controls, mocked API
- **Docker build job** in CI
- `.env.example` — all config documented, no hardcoded values
- `CHANGELOG.md`, `CONTRIBUTING.md`

### Changed
- `ALLOWED_ORIGINS` now read from environment (default `*` in dev, tighten in prod)
- CI now runs backend + frontend unit tests + E2E + Docker build

---

## [1.0.0] — 2026-03-16

### Added
- FastAPI backend: `/api/observations`, `/api/timeseries`, `/healthz`
- FMI WFS client with urllib3 retry/backoff
- GML/XML parser → `WeatherObservation` dataclasses → GeoJSON
- Leaflet.js frontend: full-screen map, 5-band temperature colouring
- Layer switching: temperature / wind / precipitation
- Bounding-box draw filter, marker clustering
- Time-series animation with play/pause/stop/scrub
- Vitest (JS) + pytest (Python) test suites, 100% coverage target
