# 🌤️ Sää WFS

> **Live Finnish weather observations on an interactive Leaflet map — powered by the FMI open WFS API.**

Fetches real-time weather data from the Finnish Meteorological Institute via OGC WFS 2.0, serves it through a FastAPI backend, and renders it as a full-screen interactive map with temperature-coded markers, layer switching, bounding-box filtering, and time-series animation.

---

## ✨ Features

| | |
|---|---|
| 🛰️ **Live FMI data** | WFS 2.0 GetFeature stored-query, configurable time window |
| 🗺️ **Leaflet.js map** | Full-screen interactive map, two base tile sets |
| 🌡️ **5-band colour scale** | Blue → green → orange → red by temperature |
| 💨 **Layer switching** | Temperature / wind speed / precipitation layers |
| 📦 **Marker clustering** | Optional MarkerCluster for dense station sets |
| 🔲 **Bbox filter** | Draw a rectangle on the map to filter by region |
| ⏱️ **Time animation** | Slider + play/pause/stop for the last N hours |
| ⚡ **FastAPI backend** | CORS-enabled proxy with retry/backoff to FMI WFS |
| 🧪 **100% test coverage** | Vitest (JS) + pytest (Python), all offline mocks |

---

## 🗺️ Colour scales

**Temperature**

| | Band |
|---|---|
| 🔵 Dark blue | Frost (< 0 °C) |
| 🩵 Light blue | Cold (0 – 10 °C) |
| 🟢 Green | Mild (10 – 20 °C) |
| 🟠 Orange | Warm (20 – 28 °C) |
| 🔴 Red | Hot (≥ 28 °C) |
| ⚫ Grey | No data |

---

## 🚀 Quick start

### 1 · Backend

```bash
cd saa_wfs/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 2 · Frontend

```bash
# Option A — Python
cd saa_wfs/frontend
python -m http.server 5174

# Option B — Node
cd saa_wfs
npm install && npm run dev
```

Open **http://localhost:5174** — data loads automatically.

---

## 🏗️ Architecture

```
Browser
  └── frontend/index.html
        └── src/
              ├── app.js        Orchestrator — wires all modules
              ├── wfs.js        fetch() calls to FastAPI backend
              ├── map.js        Leaflet map, markers, popups
              ├── layers.js     Colour scales, legend builder
              ├── animation.js  Time-series playback controller
              └── ui.js         Toast, loading overlay, topbar updates

FastAPI  (localhost:8000)
  └── backend/
        ├── main.py        Routes: /api/observations, /api/timeseries
        ├── wfs_client.py  requests.Session + urllib3 Retry → FMI WFS
        └── parser.py      GML/XML → WeatherObservation dataclasses
              └──→ GeoJSON FeatureCollection returned to frontend
```

---

## 🎛️ Frontend controls

| Control | Function |
|---|---|
| **Hours slider** | Time window: 1 – 24 hours back |
| **Place filter** | Finnish place name (e.g. "Helsinki") |
| **Hae säätiedot** | Fetch and render observations |
| **Layer toggles** | Switch between temp / wind / precip colouring |
| **Klusterointi** | Enable/disable marker clustering |
| **Piirrä alue** | Draw a bounding box on the map to filter |
| **▶ ⏸ ⏹** | Play / pause / stop time animation |
| **Time slider** | Manual scrub through time steps |
| **☰** | Collapse / expand the side panel |

---

## 🌐 API reference

```
GET /api/observations
  ?hours=1        # required, 0 < hours ≤ 48
  &place=Helsinki # optional
  &bbox=W,S,E,N   # optional, WGS-84
  &parameters=t2m,ws_10min,ri_10min,rh,p_sea

→ GeoJSON FeatureCollection + meta.station_count

GET /api/timeseries
  ?hours=6 &steps=6 &place=… &bbox=…

→ Array<{ timestamp: ISO, geojson: FeatureCollection }>

GET /healthz  → { status: "ok", time: ISO }
```

---

## 🏗️ Project layout

```
saa_wfs/
├── backend/
│   ├── main.py              FastAPI app + routes
│   ├── wfs_client.py        FMI WFS HTTP client (retry/backoff)
│   ├── parser.py            GML/XML parser → WeatherObservation
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── src/
│       ├── app.js / map.js / wfs.js
│       ├── layers.js / animation.js / ui.js
├── tests/
│   ├── test_layers.js       Colour-scale unit tests (100% cov)
│   ├── test_animation.js    TimeAnimator unit tests (100% cov)
│   ├── test_parser.py       Python GML parser tests
│   ├── test_wfs_client.py   Python HTTP client tests (mocked)
│   └── test_main.py         FastAPI endpoint tests
├── vitest.config.js
├── package.json
└── README.md
```

---

## 🧪 Testing

```bash
# JavaScript (Vitest)
npm install
npm test

# Python (pytest)
pip install -r backend/requirements-dev.txt
pytest tests/ -v --cov=backend
```

All network calls are mocked — the full suite runs **offline**.

---

## 🎛️ Osatehtävät (Task breakdown)

| Osatehtävä | Vaikeus | Status |
|---|---|---|
| WFS-rajapinnan peruskyselyiden tekeminen | Aloittelija | ✅ |
| GeoJSON/GML-datan tulkinta ja käsittely | Keskitaso | ✅ |
| Karttapohjan näyttäminen ja pisteiden visualisointi (Leaflet.js) | Keskitaso | ✅ |
| Käyttäjän rajausmahdollisuus ja interaktiiviset layerit | Keskitaso/Taitava | ✅ |
| Ajallinen visualisointi/animaatio (säätilan muutos) | Taitava | ✅ |
| Useamman datalähteen yhdistäminen ja UI:n hallinta | Taitava | ✅ |

---

## 🔒 Data licence

Weather data © Finnish Meteorological Institute.
Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## 📄 License

MIT
