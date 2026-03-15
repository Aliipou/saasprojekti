"""Tests for saa_wfs.parser — 100% branch coverage."""

from __future__ import annotations

import math
import textwrap
from datetime import datetime, timezone

import pytest

from saa_wfs.parser import WFSParser, WeatherObservation


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_GML_HEADER = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection
        xmlns:wfs="http://www.opengis.net/wfs/2.0"
        xmlns:BsWfs="http://xml.fmi.fi/schema/wfs/2.0"
        xmlns:gml="http://www.opengis.net/gml/3.2"
        numberMatched="unknown" numberReturned="2"
        timeStamp="2024-01-15T12:00:00Z">
""")

_GML_FOOTER = "</wfs:FeatureCollection>"


def _element(
    station: str,
    lat: float,
    lon: float,
    ts: str,
    param: str,
    value: str,
    idx: int = 1,
) -> str:
    return textwrap.dedent(f"""\
    <wfs:member>
      <BsWfs:BsWfsElement gml:id="BsWfsElement.{idx}">
        <BsWfs:Location>
          <gml:Point gml:id="P.{idx}" srsName="http://www.opengis.net/def/crs/EPSG/0/4258">
            <gml:name>{station}</gml:name>
            <gml:pos>{lat} {lon}</gml:pos>
          </gml:Point>
        </BsWfs:Location>
        <BsWfs:Time>{ts}</BsWfs:Time>
        <BsWfs:ParameterName>{param}</BsWfs:ParameterName>
        <BsWfs:ParameterValue>{value}</BsWfs:ParameterValue>
      </BsWfs:BsWfsElement>
    </wfs:member>
    """)


def _doc(*elements: str) -> str:
    return _GML_HEADER + "".join(elements) + _GML_FOOTER


# ---------------------------------------------------------------------------
# Happy-path parsing
# ---------------------------------------------------------------------------


class TestWFSParserHappy:
    def _parse_single(self) -> WeatherObservation:
        xml = _doc(
            _element("Helsinki Kaisaniemi", 60.175, 24.944,
                     "2024-01-15T11:00:00Z", "t2m", "2.4", 1),
            _element("Helsinki Kaisaniemi", 60.175, 24.944,
                     "2024-01-15T11:00:00Z", "ws_10min", "3.1", 2),
            _element("Helsinki Kaisaniemi", 60.175, 24.944,
                     "2024-01-15T11:00:00Z", "ri_10min", "0.0", 3),
            _element("Helsinki Kaisaniemi", 60.175, 24.944,
                     "2024-01-15T11:00:00Z", "rh", "85.0", 4),
            _element("Helsinki Kaisaniemi", 60.175, 24.944,
                     "2024-01-15T11:00:00Z", "p_sea", "1013.2", 5),
        )
        obs = WFSParser().parse(xml)
        assert len(obs) == 1
        return obs[0]

    def test_station_name(self) -> None:
        assert self._parse_single().station_name == "Helsinki Kaisaniemi"

    def test_coordinates(self) -> None:
        o = self._parse_single()
        assert o.lat == pytest.approx(60.175)
        assert o.lon == pytest.approx(24.944)

    def test_temperature(self) -> None:
        assert self._parse_single().temperature_c == pytest.approx(2.4)

    def test_wind(self) -> None:
        assert self._parse_single().wind_speed_ms == pytest.approx(3.1)

    def test_precipitation(self) -> None:
        assert self._parse_single().precipitation_mmh == pytest.approx(0.0)

    def test_humidity(self) -> None:
        assert self._parse_single().humidity_pct == pytest.approx(85.0)

    def test_pressure(self) -> None:
        assert self._parse_single().pressure_hpa == pytest.approx(1013.2)

    def test_timestamp_utc(self) -> None:
        o = self._parse_single()
        assert o.observed_at.tzinfo is not None
        assert o.observed_at.year == 2024

    def test_has_value_true(self) -> None:
        o = self._parse_single()
        assert o.has_value("temperature_c")

    def test_multiple_stations(self) -> None:
        xml = _doc(
            _element("Oulu", 65.0, 25.5, "2024-01-15T11:00:00Z", "t2m", "-5.2", 1),
            _element("Tampere", 61.5, 23.8, "2024-01-15T11:00:00Z", "t2m", "1.0", 2),
        )
        obs = WFSParser().parse(xml)
        assert len(obs) == 2
        names = {o.station_name for o in obs}
        assert names == {"Oulu", "Tampere"}

    def test_latest_timestamp_wins(self) -> None:
        """When a station reports the same param twice, the later value wins."""
        xml = _doc(
            _element("A", 60.0, 25.0, "2024-01-15T10:00:00Z", "t2m", "1.0", 1),
            _element("A", 60.0, 25.0, "2024-01-15T11:00:00Z", "t2m", "5.0", 2),
        )
        obs = WFSParser().parse(xml)
        assert len(obs) == 1
        assert obs[0].temperature_c == pytest.approx(5.0)

    def test_nan_parameter_value(self) -> None:
        xml = _doc(
            _element("B", 60.0, 25.0, "2024-01-15T10:00:00Z", "t2m", "NaN", 1),
        )
        obs = WFSParser().parse(xml)
        assert math.isnan(obs[0].temperature_c)
        assert not obs[0].has_value("temperature_c")

    def test_empty_parameter_value(self) -> None:
        xml = _doc(
            _element("C", 60.0, 25.0, "2024-01-15T10:00:00Z", "t2m", "", 1),
        )
        obs = WFSParser().parse(xml)
        assert math.isnan(obs[0].temperature_c)

    def test_unknown_parameter_goes_to_extra(self) -> None:
        xml = _doc(
            _element("D", 60.0, 25.0, "2024-01-15T10:00:00Z", "snow_depth", "12.0", 1),
        )
        obs = WFSParser().parse(xml)
        assert obs[0].extra.get("snow_depth") == pytest.approx(12.0)

    def test_empty_feature_collection(self) -> None:
        xml = _GML_HEADER + _GML_FOOTER
        obs = WFSParser().parse(xml)
        assert obs == []


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestWFSParserErrors:
    def test_malformed_xml(self) -> None:
        import xml.etree.ElementTree as ET

        with pytest.raises(ET.ParseError):
            WFSParser().parse("<not closed")

    def test_exception_report_raises(self) -> None:
        xml = textwrap.dedent("""\
            <?xml version="1.0"?>
            <ExceptionReport xmlns="http://www.opengis.net/ows/1.1" version="2.0.0">
              <Exception exceptionCode="InvalidParameterValue">
                <ExceptionText>Unknown stored query</ExceptionText>
              </Exception>
            </ExceptionReport>
        """)
        with pytest.raises(RuntimeError, match="ExceptionReport"):
            WFSParser().parse(xml)

    def test_wrong_root_element_raises(self) -> None:
        xml = '<SomeOtherRoot xmlns="http://example.com"/>'
        with pytest.raises(ValueError, match="Unexpected root"):
            WFSParser().parse(xml)

    def test_malformed_element_skipped(self) -> None:
        """An element without gml:Point should be skipped, not crash."""
        bad_member = textwrap.dedent("""\
        <wfs:member xmlns:wfs="http://www.opengis.net/wfs/2.0"
                    xmlns:BsWfs="http://xml.fmi.fi/schema/wfs/2.0"
                    xmlns:gml="http://www.opengis.net/gml/3.2">
          <BsWfs:BsWfsElement gml:id="bad">
            <BsWfs:Location/>
            <BsWfs:Time>2024-01-15T10:00:00Z</BsWfs:Time>
            <BsWfs:ParameterName>t2m</BsWfs:ParameterName>
            <BsWfs:ParameterValue>5.0</BsWfs:ParameterValue>
          </BsWfs:BsWfsElement>
        </wfs:member>
        """)
        xml = _GML_HEADER + bad_member + _GML_FOOTER
        obs = WFSParser().parse(xml)
        assert obs == []

    def test_no_station_name_defaults_unknown(self) -> None:
        """A Point without gml:name should produce 'Unknown'."""
        member = textwrap.dedent("""\
        <wfs:member>
          <BsWfs:BsWfsElement gml:id="x1">
            <BsWfs:Location>
              <gml:Point gml:id="Px1" srsName="...">
                <gml:pos>60.0 25.0</gml:pos>
              </gml:Point>
            </BsWfs:Location>
            <BsWfs:Time>2024-01-15T10:00:00Z</BsWfs:Time>
            <BsWfs:ParameterName>t2m</BsWfs:ParameterName>
            <BsWfs:ParameterValue>3.0</BsWfs:ParameterValue>
          </BsWfs:BsWfsElement>
        </wfs:member>
        """)
        xml = _GML_HEADER + member + _GML_FOOTER
        obs = WFSParser().parse(xml)
        assert obs[0].station_name == "Unknown"
