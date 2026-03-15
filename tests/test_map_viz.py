"""Tests for saa_wfs.map_viz — 100% branch coverage."""

from __future__ import annotations

import math
import webbrowser
from pathlib import Path
from unittest.mock import patch

import folium
import pytest

from saa_wfs.map_viz import (
    WeatherMapBuilder,
    WeatherMapConfig,
    _fmt,
    _temp_colour,
)
from saa_wfs.parser import WeatherObservation
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UTC = timezone.utc
_NOW = datetime(2024, 1, 15, 12, 0, tzinfo=_UTC)


def _obs(
    name: str = "Helsinki",
    lat: float = 60.17,
    lon: float = 24.94,
    temp: float = 5.0,
    wind: float = 3.0,
    precip: float = 0.0,
    humidity: float = 80.0,
    pressure: float = 1013.0,
    extra: dict | None = None,
) -> WeatherObservation:
    return WeatherObservation(
        station_name=name,
        lat=lat,
        lon=lon,
        observed_at=_NOW,
        temperature_c=temp,
        wind_speed_ms=wind,
        precipitation_mmh=precip,
        humidity_pct=humidity,
        pressure_hpa=pressure,
        extra=extra or {},
    )


# ---------------------------------------------------------------------------
# _temp_colour
# ---------------------------------------------------------------------------


class TestTempColour:
    def test_nan_is_grey(self) -> None:
        assert _temp_colour(float("nan")) == "#9E9E9E"

    def test_frost(self) -> None:
        c = _temp_colour(-10.0)
        assert c == "#1565C0"

    def test_cold(self) -> None:
        c = _temp_colour(5.0)
        assert c == "#42A5F5"

    def test_mild(self) -> None:
        c = _temp_colour(15.0)
        assert c == "#66BB6A"

    def test_warm(self) -> None:
        c = _temp_colour(22.0)
        assert c == "#FFA726"

    def test_hot(self) -> None:
        c = _temp_colour(30.0)
        assert c == "#E53935"

    def test_exactly_zero(self) -> None:
        assert _temp_colour(0.0) == "#42A5F5"

    def test_exactly_ten(self) -> None:
        assert _temp_colour(10.0) == "#66BB6A"

    def test_exactly_twenty(self) -> None:
        assert _temp_colour(20.0) == "#FFA726"

    def test_exactly_28(self) -> None:
        assert _temp_colour(28.0) == "#E53935"


# ---------------------------------------------------------------------------
# _fmt
# ---------------------------------------------------------------------------


class TestFmt:
    def test_normal_value(self) -> None:
        assert _fmt(5.123, 1, "°C") == "5.1 °C"

    def test_no_unit(self) -> None:
        assert _fmt(3.14, 2) == "3.14"

    def test_nan_returns_dash(self) -> None:
        assert _fmt(float("nan")) == "–"

    def test_zero_decimals(self) -> None:
        assert _fmt(85.0, 0, "%") == "85 %"


# ---------------------------------------------------------------------------
# WeatherMapConfig
# ---------------------------------------------------------------------------


class TestWeatherMapConfig:
    def test_defaults(self) -> None:
        cfg = WeatherMapConfig()
        assert cfg.center == (65.0, 26.0)
        assert cfg.zoom_start == 5
        assert not cfg.auto_open
        assert cfg.output_path == Path("saa_map.html")


# ---------------------------------------------------------------------------
# WeatherMapBuilder
# ---------------------------------------------------------------------------


class TestWeatherMapBuilder:
    def test_build_returns_folium_map(self) -> None:
        m = WeatherMapBuilder().build([_obs()])
        assert isinstance(m, folium.Map)

    def test_build_empty_observations(self) -> None:
        m = WeatherMapBuilder().build([])
        assert isinstance(m, folium.Map)

    def test_nan_temperature_handled(self) -> None:
        o = _obs(temp=float("nan"))
        m = WeatherMapBuilder().build([o])
        assert isinstance(m, folium.Map)

    def test_extra_params_in_popup(self) -> None:
        o = _obs(extra={"snow_depth": 15.0})
        m = WeatherMapBuilder().build([o])
        html = m.get_root().render()
        assert "snow_depth" in html

    def test_save_creates_file(self, tmp_path: Path) -> None:
        cfg = WeatherMapConfig(output_path=tmp_path / "out.html")
        builder = WeatherMapBuilder(cfg)
        m = builder.build([_obs()])
        out = builder.save(m)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "folium" in content.lower() or "leaflet" in content.lower()

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        cfg = WeatherMapConfig(output_path=tmp_path / "deep" / "map.html")
        builder = WeatherMapBuilder(cfg)
        m = builder.build([])
        out = builder.save(m)
        assert out.exists()

    def test_save_auto_open(self, tmp_path: Path) -> None:
        cfg = WeatherMapConfig(
            output_path=tmp_path / "map.html", auto_open=True
        )
        builder = WeatherMapBuilder(cfg)
        m = builder.build([_obs()])
        with patch.object(webbrowser, "open") as mock_open:
            builder.save(m)
            mock_open.assert_called_once()

    def test_save_no_auto_open(self, tmp_path: Path) -> None:
        cfg = WeatherMapConfig(output_path=tmp_path / "map.html", auto_open=False)
        builder = WeatherMapBuilder(cfg)
        m = builder.build([])
        with patch.object(webbrowser, "open") as mock_open:
            builder.save(m)
            mock_open.assert_not_called()

    def test_multiple_stations(self) -> None:
        observations = [
            _obs("A", temp=-5.0),
            _obs("B", lat=65.0, lon=25.0, temp=12.0),
            _obs("C", lat=62.0, lon=27.0, temp=25.0),
        ]
        m = WeatherMapBuilder().build(observations)
        assert isinstance(m, folium.Map)

    def test_all_temperature_bands_rendered(self, tmp_path: Path) -> None:
        """Ensure all 5 colour bands appear in map HTML."""
        observations = [
            _obs("frost", temp=-10.0),
            _obs("cold", lat=61.0, temp=5.0),
            _obs("mild", lat=62.0, temp=15.0),
            _obs("warm", lat=63.0, temp=22.0),
            _obs("hot", lat=64.0, temp=30.0),
            _obs("nodata", lat=65.0, temp=float("nan")),
        ]
        cfg = WeatherMapConfig(output_path=tmp_path / "all_bands.html")
        builder = WeatherMapBuilder(cfg)
        m = builder.build(observations)
        builder.save(m)
        html = (tmp_path / "all_bands.html").read_text(encoding="utf-8")
        for colour in ("#1565C0", "#42A5F5", "#66BB6A", "#FFA726", "#E53935", "#9E9E9E"):
            assert colour in html
