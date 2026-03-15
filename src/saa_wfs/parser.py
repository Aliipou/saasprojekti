"""
GML/XML parser for FMI WFS BsWfsElement responses.

The FMI `fmi::observations::weather::simple` stored-query returns a
``wfs:FeatureCollection`` of ``BsWfs:BsWfsElement`` nodes.  This module
parses those nodes into :class:`StationObservation` dataclasses that are
easy to work with downstream.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# XML namespace map
# ---------------------------------------------------------------------------

NS: dict[str, str] = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "BsWfs": "http://xml.fmi.fi/schema/wfs/2.0",
    "gml": "http://www.opengis.net/gml/3.2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Register all so ElementTree's find/findall use short prefixes
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

_MISSING = float("nan")


@dataclass
class WeatherObservation:
    """
    Latest weather parameters for a single station.

    All numeric fields are ``float('nan')`` when not reported.
    """

    station_name: str
    lat: float
    lon: float
    observed_at: datetime  # UTC
    temperature_c: float = _MISSING  # t2m
    wind_speed_ms: float = _MISSING  # ws_10min
    precipitation_mmh: float = _MISSING  # ri_10min
    humidity_pct: float = _MISSING  # rh
    pressure_hpa: float = _MISSING  # p_sea

    # extra raw parameters that weren't mapped above
    extra: dict[str, float] = field(default_factory=dict, repr=False)

    def has_value(self, attr: str) -> bool:
        """Return True if *attr* is a real (non-NaN) number."""
        return not math.isnan(getattr(self, attr))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_PARAM_MAP: dict[str, str] = {
    "t2m": "temperature_c",
    "ws_10min": "wind_speed_ms",
    "ri_10min": "precipitation_mmh",
    "rh": "humidity_pct",
    "p_sea": "pressure_hpa",
}


class WFSParser:
    """Parse raw FMI WFS XML into :class:`WeatherObservation` objects.

    The parser aggregates all ``BsWfsElement`` records by station name,
    keeping only the **most recent** observation per station.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, xml_text: str) -> list[WeatherObservation]:
        """Parse *xml_text* (WFS GetFeature response) and return one
        observation per station (latest timestamp wins).

        Raises
        ------
        ET.ParseError
            If the XML is malformed.
        ValueError
            If no ``wfs:FeatureCollection`` root element is found.
        """
        root = ET.fromstring(xml_text)
        self._check_root(root)

        # station_name → {param_name → (timestamp, value)}
        raw: dict[str, dict[str, tuple[datetime, float]]] = {}
        # station_name → (lat, lon)
        coords: dict[str, tuple[float, float]] = {}

        for element in self._iter_elements(root):
            name, lat, lon, ts, param, value = element
            if name not in coords:
                coords[name] = (lat, lon)
            station_data = raw.setdefault(name, {})
            existing = station_data.get(param)
            if existing is None or ts > existing[0]:
                station_data[param] = (ts, value)

        observations = [
            self._build_observation(name, coords[name], raw[name])
            for name in raw
        ]
        logger.info("Parsed %d stations from WFS response", len(observations))
        return observations

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _check_root(root: ET.Element) -> None:
        tag = root.tag
        if "FeatureCollection" not in tag and "ExceptionReport" not in tag:
            raise ValueError(f"Unexpected root element: {tag}")
        if "ExceptionReport" in tag:
            text = ET.tostring(root, encoding="unicode")
            raise RuntimeError(f"WFS returned ExceptionReport:\n{text[:800]}")

    def _iter_elements(
        self, root: ET.Element
    ) -> Iterator[tuple[str, float, float, datetime, str, float]]:
        """Yield (station_name, lat, lon, timestamp, param_name, value)."""
        for member in root.iter(f"{{{NS['BsWfs']}}}BsWfsElement"):
            try:
                name, lat, lon = self._parse_location(member)
                ts = self._parse_time(member)
                param = self._parse_text(member, "BsWfs:ParameterName")
                raw_val = self._parse_text(member, "BsWfs:ParameterValue")
                value = float(raw_val) if raw_val not in ("NaN", "", None) else _MISSING
            except Exception as exc:
                logger.debug("Skipping malformed BsWfsElement: %s", exc)
                continue
            yield name, lat, lon, ts, param, value

    @staticmethod
    def _parse_location(elem: ET.Element) -> tuple[str, float, float]:
        point = elem.find("BsWfs:Location/gml:Point", NS)
        if point is None:
            raise ValueError("Missing gml:Point")
        name_el = point.find("gml:name", NS)
        station_name = name_el.text.strip() if name_el is not None and name_el.text else "Unknown"
        pos_el = point.find("gml:pos", NS)
        if pos_el is None or not pos_el.text:
            raise ValueError("Missing gml:pos")
        lat_s, lon_s = pos_el.text.strip().split()
        return station_name, float(lat_s), float(lon_s)

    @staticmethod
    def _parse_time(elem: ET.Element) -> datetime:
        text = elem.findtext("BsWfs:Time", namespaces=NS)
        if not text:
            raise ValueError("Missing BsWfs:Time")
        return datetime.fromisoformat(text.replace("Z", "+00:00"))

    @staticmethod
    def _parse_text(elem: ET.Element, path: str) -> str | None:
        node = elem.find(path, NS)
        return node.text.strip() if node is not None and node.text else None

    @staticmethod
    def _build_observation(
        name: str,
        coords: tuple[float, float],
        data: dict[str, tuple[datetime, float]],
    ) -> WeatherObservation:
        lat, lon = coords
        # Latest timestamp overall
        ts = max((v[0] for v in data.values()), default=datetime.now(tz=timezone.utc))
        kwargs: dict[str, object] = {
            "station_name": name,
            "lat": lat,
            "lon": lon,
            "observed_at": ts,
        }
        extra: dict[str, float] = {}
        for param, (_, value) in data.items():
            attr = _PARAM_MAP.get(param)
            if attr:
                kwargs[attr] = value
            else:
                extra[param] = value
        kwargs["extra"] = extra
        return WeatherObservation(**kwargs)  # type: ignore[arg-type]
