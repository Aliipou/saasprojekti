"""Tests for saa_wfs.main — 100% branch coverage."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from saa_wfs.main import main
from saa_wfs.parser import WeatherObservation
from saa_wfs.wfs_client import WFSResponse
from datetime import datetime, timezone

_UTC = timezone.utc
_NOW = datetime(2024, 1, 15, 12, 0, tzinfo=_UTC)

_FAKE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection
        xmlns:wfs="http://www.opengis.net/wfs/2.0"
        xmlns:BsWfs="http://xml.fmi.fi/schema/wfs/2.0"
        xmlns:gml="http://www.opengis.net/gml/3.2">
      <wfs:member>
        <BsWfs:BsWfsElement gml:id="e1">
          <BsWfs:Location>
            <gml:Point gml:id="p1" srsName="...">
              <gml:name>Helsinki</gml:name>
              <gml:pos>60.17 24.94</gml:pos>
            </gml:Point>
          </BsWfs:Location>
          <BsWfs:Time>2024-01-15T11:00:00Z</BsWfs:Time>
          <BsWfs:ParameterName>t2m</BsWfs:ParameterName>
          <BsWfs:ParameterValue>3.5</BsWfs:ParameterValue>
        </BsWfs:BsWfsElement>
      </wfs:member>
    </wfs:FeatureCollection>
""")

_EMPTY_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection
        xmlns:wfs="http://www.opengis.net/wfs/2.0"
        xmlns:BsWfs="http://xml.fmi.fi/schema/wfs/2.0"
        xmlns:gml="http://www.opengis.net/gml/3.2">
    </wfs:FeatureCollection>
""")


def _fake_response(xml: str = _FAKE_XML) -> WFSResponse:
    return WFSResponse(
        xml_text=xml,
        fetched_at=_NOW,
        url="https://opendata.fmi.fi/wfs?...",
        elapsed_ms=120.0,
    )


class TestMainExitCodes:
    def test_success_returns_0(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = _fake_response()
            code = main(["--output", str(out)])
        assert code == 0
        assert out.exists()

    def test_fetch_error_returns_1(self, tmp_path: Path) -> None:
        import requests
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.side_effect = (
                requests.ConnectionError("no network")
            )
            code = main(["--output", str(out)])
        assert code == 1

    def test_parse_error_returns_1(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = (
                _fake_response("<broken xml")
            )
            code = main(["--output", str(out)])
        assert code == 1

    def test_empty_observations_returns_0(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = (
                _fake_response(_EMPTY_XML)
            )
            code = main(["--output", str(out)])
        assert code == 0

    def test_place_arg_passed(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            mock_fetch = MockClient.return_value.__enter__.return_value.fetch
            mock_fetch.return_value = _fake_response()
            main(["--place", "Helsinki", "--output", str(out)])
            call_args = mock_fetch.call_args[0][0]
            assert call_args.place == "Helsinki"

    def test_bbox_arg_passed(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            mock_fetch = MockClient.return_value.__enter__.return_value.fetch
            mock_fetch.return_value = _fake_response()
            main(["--bbox", "20,60,30,70", "--output", str(out)])
            call_args = mock_fetch.call_args[0][0]
            assert call_args.bbox == "20,60,30,70"

    def test_hours_arg(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            mock_fetch = MockClient.return_value.__enter__.return_value.fetch
            mock_fetch.return_value = _fake_response()
            main(["--hours", "3", "--output", str(out)])
            call_args = mock_fetch.call_args[0][0]
            assert call_args.hours_back == 3.0

    def test_no_valid_temps_still_returns_0(self, tmp_path: Path) -> None:
        """If all stations have NaN temperature, no temp range line printed."""
        nan_xml = _FAKE_XML.replace("3.5", "NaN")
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = (
                _fake_response(nan_xml)
            )
            code = main(["--output", str(out)])
        assert code == 0

    def test_auto_open_flag(self, tmp_path: Path) -> None:
        import webbrowser
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = _fake_response()
            with patch.object(webbrowser, "open"):
                code = main(["--output", str(out), "--open"])
        assert code == 0

    def test_debug_log_level(self, tmp_path: Path) -> None:
        out = tmp_path / "map.html"
        with patch("saa_wfs.main.FMIWFSClient") as MockClient:
            MockClient.return_value.__enter__.return_value.fetch.return_value = _fake_response()
            code = main(["--output", str(out), "--log-level", "DEBUG"])
        assert code == 0
