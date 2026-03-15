"""
Interactive Folium map visualisation for Finnish weather observations.

Each weather station is rendered as a circle marker with a colour-coded
temperature band and a popup showing all available measurements.
"""

from __future__ import annotations

import logging
import math
import webbrowser
from pathlib import Path
from typing import Sequence

import folium
from folium.plugins import Fullscreen, MiniMap

from .parser import WeatherObservation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour bands for temperature
# ---------------------------------------------------------------------------

_TEMP_BANDS: list[tuple[float, str, str]] = [
    (-99, "#1565C0", "Pakkas (< 0 °C)"),          # dark blue — frost
    (0,   "#42A5F5", "Viileä (0–10 °C)"),          # light blue — cold
    (10,  "#66BB6A", "Leuto (10–20 °C)"),           # green — mild
    (20,  "#FFA726", "Lämmin (20–28 °C)"),          # orange — warm
    (28,  "#E53935", "Kuuma (≥ 28 °C)"),            # red — hot
]


def _temp_colour(temp: float) -> str:
    if math.isnan(temp):
        return "#9E9E9E"  # grey — no data
    for threshold, colour, _ in reversed(_TEMP_BANDS):
        if temp >= threshold:
            return colour
    return _TEMP_BANDS[0][1]


# ---------------------------------------------------------------------------
# Popup HTML builder
# ---------------------------------------------------------------------------

_NA = "–"


def _fmt(value: float, decimals: int = 1, unit: str = "") -> str:
    if math.isnan(value):
        return _NA
    return f"{value:.{decimals}f}{' ' + unit if unit else ''}"


def _popup_html(obs: WeatherObservation) -> str:
    rows = [
        ("Lämpötila", _fmt(obs.temperature_c, 1, "°C")),
        ("Tuuli", _fmt(obs.wind_speed_ms, 1, "m/s")),
        ("Sademäärä", _fmt(obs.precipitation_mmh, 2, "mm/h")),
        ("Kosteus", _fmt(obs.humidity_pct, 0, "%")),
        ("Paine", _fmt(obs.pressure_hpa, 1, "hPa")),
    ]
    for key, val in obs.extra.items():
        rows.append((key, _fmt(val)))

    ts = obs.observed_at.strftime("%Y-%m-%d %H:%M UTC")
    row_html = "".join(
        f"<tr><td style='padding:2px 8px 2px 0;color:#888'>{k}</td>"
        f"<td style='padding:2px 0;font-weight:600'>{v}</td></tr>"
        for k, v in rows
    )
    return (
        f"<div style='font-family:sans-serif;min-width:180px'>"
        f"<b style='font-size:13px'>{obs.station_name}</b>"
        f"<table style='font-size:12px;margin-top:6px'>{row_html}</table>"
        f"<div style='font-size:10px;color:#aaa;margin-top:4px'>{ts}</div>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Map builder
# ---------------------------------------------------------------------------


class WeatherMapConfig:
    def __init__(
        self,
        *,
        center: tuple[float, float] = (65.0, 26.0),
        zoom_start: int = 5,
        radius: int = 8,
        tiles: str = "CartoDB positron",
        output_path: Path = Path("saa_map.html"),
        auto_open: bool = False,
    ) -> None:
        self.center = center
        self.zoom_start = zoom_start
        self.radius = radius
        self.tiles = tiles
        self.output_path = output_path
        self.auto_open = auto_open


class WeatherMapBuilder:
    """Build and save an interactive Folium map from weather observations."""

    def __init__(self, config: WeatherMapConfig | None = None) -> None:
        self.config = config or WeatherMapConfig()

    def build(self, observations: Sequence[WeatherObservation]) -> folium.Map:
        """Create and return a fully populated :class:`folium.Map`."""
        cfg = self.config
        m = folium.Map(location=list(cfg.center), zoom_start=cfg.zoom_start, tiles=cfg.tiles)
        Fullscreen().add_to(m)
        MiniMap(toggle_display=True).add_to(m)

        layer = folium.FeatureGroup(name="Sääasemat", show=True)
        for obs in observations:
            self._add_marker(layer, obs)
        layer.add_to(m)

        self._add_legend(m)
        folium.LayerControl().add_to(m)

        logger.info("Map built with %d stations", len(observations))
        return m

    def save(self, m: folium.Map) -> Path:
        """Save map to configured output path and optionally open in browser."""
        cfg = self.config
        cfg.output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(cfg.output_path))
        logger.info("Map saved: %s", cfg.output_path)
        if cfg.auto_open:
            webbrowser.open(cfg.output_path.resolve().as_uri())
        return cfg.output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_marker(
        self, layer: folium.FeatureGroup, obs: WeatherObservation
    ) -> None:
        colour = _temp_colour(obs.temperature_c)
        temp_label = _fmt(obs.temperature_c, 1, "°C") if not math.isnan(obs.temperature_c) else _NA
        tooltip = f"{obs.station_name}  {temp_label}"

        folium.CircleMarker(
            location=[obs.lat, obs.lon],
            radius=self.config.radius,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            weight=1.5,
            tooltip=folium.Tooltip(tooltip),
            popup=folium.Popup(_popup_html(obs), max_width=260),
        ).add_to(layer)

    @staticmethod
    def _add_legend(m: folium.Map) -> None:
        items = "".join(
            f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0'>"
            f"<span style='width:14px;height:14px;border-radius:50%;"
            f"background:{colour};display:inline-block'></span>"
            f"<span style='font-size:12px'>{label}</span></div>"
            for _, colour, label in _TEMP_BANDS
        )
        no_data = (
            "<div style='display:flex;align-items:center;gap:6px;margin:3px 0'>"
            "<span style='width:14px;height:14px;border-radius:50%;"
            "background:#9E9E9E;display:inline-block'></span>"
            "<span style='font-size:12px'>Ei tietoa</span></div>"
        )
        legend_html = (
            "<div style='position:fixed;bottom:30px;left:30px;z-index:1000;"
            "background:white;padding:10px 14px;border-radius:8px;"
            "box-shadow:0 2px 8px rgba(0,0,0,.25);font-family:sans-serif'>"
            f"<b style='font-size:13px'>Lämpötila</b>{items}{no_data}</div>"
        )
        m.get_root().html.add_child(folium.Element(legend_html))
