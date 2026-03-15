# 🌤️ saa-wfs

> **Real-time Finnish weather observations on an interactive map — powered by the FMI open WFS API.**

Saa-wfs fetches live weather data from the [Finnish Meteorological Institute](https://en.ilmatieteenlaitos.fi/open-data) via their OGC WFS 2.0 endpoint, parses the GML response, and renders an interactive Folium/Leaflet HTML map with temperature-coded station markers and rich popups.

No API key required. Works offline once the HTML is saved.

---

## ✨ Features

| | |
|---|---|
| 🛰️ **Live FMI data** | WFS GetFeature stored-query, last N hours |
| 🗺️ **Interactive map** | Leaflet/Folium, fullscreen, mini-map, layer control |
| 🌡️ **Temperature colour bands** | Blue → green → orange → red scale |
| 📊 **Rich popups** | Temp, wind, precipitation, humidity, pressure |
| 🔁 **Retry & backoff** | Automatic retry on 5xx / rate-limit responses |
| 🧪 **100 % test coverage** | pytest + responses mock library |
| 🐍 **Python 3.11+** | Typed, linted, mypy-clean |

---

## 🗺️ Map preview

Each station circle is colour-coded by air temperature:

| Colour | Temperature |
|---|---|
| 🔵 Dark blue | Below 0 °C (frost) |
| 🩵 Light blue | 0 – 10 °C (cold) |
| 🟢 Green | 10 – 20 °C (mild) |
| 🟠 Orange | 20 – 28 °C (warm) |
| 🔴 Red | 28 °C and above (hot) |
| ⚫ Grey | No data |

Click any marker to see a full data popup.

---

## 🚀 Quick start

```bash
# 1. Clone & install
git clone <repo-url>
cd saa_wfs
pip install -e ".[dev]"

# 2. Fetch last hour of observations (all Finland)
saa-wfs

# 3. Open the map
start saa_map.html          # Windows
open  saa_map.html          # macOS
xdg-open saa_map.html       # Linux

# 4. Auto-open in browser
saa-wfs --open

# 5. Narrow to a city or bounding box
saa-wfs --place Helsinki --hours 2
saa-wfs --bbox 20,59,32,70  --hours 1
```

**Sample console output:**

```
Stations: 187  |  Temp range: -12.4 … 8.1 °C

  Map saved → C:\projects\saa_wfs\saa_map.html
```

---

## 🏗️ Architecture

```
CLI (main.py)
     │
     ├─► FMIWFSClient          HTTP GET with retry/backoff
     │       └─► WFS API       https://opendata.fmi.fi/wfs
     │
     ├─► WFSParser             GML/XML → WeatherObservation dataclasses
     │       └─► ElementTree   stdlib XML parsing, namespace-aware
     │
     └─► WeatherMapBuilder     Folium map construction
             └─► saa_map.html  Standalone interactive HTML
```

---

## 🎛️ Full CLI reference

```
saa-wfs [options]

fetch:
  --hours N           How many hours back to fetch     [default: 1.0]
  --place NAME        Finnish place name filter        [default: all Finland]
  --bbox W,S,E,N      Bounding box WGS-84 lon/lat      [default: none]
  --parameters LIST   Comma-separated WFS params       [default: t2m,ws_10min,ri_10min,rh,p_sea]

output:
  --output / -o PATH  Output HTML file                 [default: saa_map.html]
  --open              Auto-open in browser after save
  --zoom N            Initial map zoom level           [default: 5]

verbosity:
  --log-level         DEBUG | INFO | WARNING           [default: INFO]
```

---

## 🌐 WFS parameters

| Parameter | Description | Unit |
|---|---|---|
| `t2m` | Air temperature at 2 m | °C |
| `ws_10min` | Wind speed 10-min average | m/s |
| `ri_10min` | Precipitation intensity | mm/h |
| `rh` | Relative humidity | % |
| `p_sea` | Pressure reduced to sea level | hPa |

Add any other FMI parameter to `--parameters` and it will appear in the popup under *extra*.

---

## 🏗️ Project layout

```
saa_wfs/
├── src/saa_wfs/
│   ├── __init__.py
│   ├── wfs_client.py    # HTTP fetch, retry, session management
│   ├── parser.py        # GML/XML → WeatherObservation dataclasses
│   ├── map_viz.py       # Folium map builder, legend, popups
│   └── main.py          # CLI entry point
├── tests/
│   ├── test_wfs_client.py
│   ├── test_parser.py
│   ├── test_map_viz.py
│   └── test_main.py
├── pyproject.toml
└── README.md
```

---

## 🧪 Running tests

```bash
pip install -e ".[dev]"
pytest                        # all tests + coverage report
pytest -k test_parser         # single module
pytest --cov-report=html      # open htmlcov/index.html
```

Network calls are fully mocked — the test suite runs offline.
Coverage is enforced at **100 %**.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client with retry adapter |
| `urllib3` | Retry policy primitives |
| `folium` | Leaflet.js map wrapper |

No third-party XML library — uses Python stdlib `xml.etree.ElementTree`.

---

## 🔒 Data licence

Weather data © Finnish Meteorological Institute, licensed under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
See [FMI open data terms](https://en.ilmatieteenlaitos.fi/open-data-licence).

---

## 📄 License

MIT
