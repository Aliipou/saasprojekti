# Contributing

## Setup

```bash
git clone <repo>
cd saa_wfs

# Backend
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# Frontend / tests
npm install
```

## Running locally

```bash
# Option A — Docker (recommended)
docker compose up

# Option B — manual
uvicorn backend.main:app --reload --port 8000   # terminal 1
npx serve frontend --port 5174                  # terminal 2
```

## Tests

```bash
pytest tests/ -v --cov=backend      # Python unit tests
npm test                             # JS unit tests (Vitest)
npx playwright install && npx playwright test   # E2E
```

## Code standards

- Python: **ruff** lint, **mypy --strict**, 100% pytest coverage
- JavaScript: **ES modules**, 100% Vitest coverage for pure-logic modules
- All secrets via environment variables — never hardcoded
- API changes must update `/docs` (FastAPI auto-generated) and `CHANGELOG.md`

## Pull requests

1. Fork → feature branch → PR to `main`
2. All CI jobs must pass (backend, frontend, E2E, Docker build)
3. Update `CHANGELOG.md` under `[Unreleased]`
