"""
CLI entry point for saa_wfs.

Usage
-----
    python -m saa_wfs [options]
    saa-wfs [options]           # after pip install

Run --help for full option reference.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .map_viz import WeatherMapBuilder, WeatherMapConfig
from .parser import WFSParser
from .wfs_client import FMIWFSClient, WFSRequest

_LOG_LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING}


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        level=_LOG_LEVELS.get(level.upper(), logging.INFO),
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="saa-wfs",
        description=(
            "Fetch Finnish weather observations from FMI WFS and "
            "render an interactive HTML map."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  saa-wfs
  saa-wfs --hours 2 --output ~/Desktop/saa.html --open
  saa-wfs --place Helsinki --hours 1 --log-level DEBUG
""",
    )
    p.add_argument(
        "--hours", type=float, default=1.0, metavar="N",
        help="How many hours back to fetch observations (default: 1)",
    )
    p.add_argument(
        "--place", default=None, metavar="NAME",
        help="Filter to a specific Finnish place name (e.g. Helsinki)",
    )
    p.add_argument(
        "--bbox", default=None, metavar="W,S,E,N",
        help="Bounding box filter: lon_min,lat_min,lon_max,lat_max (WGS-84)",
    )
    p.add_argument(
        "--parameters", default="t2m,ws_10min,ri_10min,rh,p_sea",
        help="Comma-separated WFS parameter names (default: t2m,ws_10min,ri_10min,rh,p_sea)",
    )
    p.add_argument(
        "--output", "-o", type=Path, default=Path("saa_map.html"),
        help="Output HTML file path (default: saa_map.html)",
    )
    p.add_argument(
        "--open", action="store_true", dest="auto_open",
        help="Open the map in the default browser after saving",
    )
    p.add_argument(
        "--zoom", type=int, default=5,
        help="Initial map zoom level (default: 5)",
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
        help="Logging verbosity (default: INFO)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.log_level)
    log = logging.getLogger(__name__)

    # --- Fetch ----------------------------------------------------------------
    req = WFSRequest(
        hours_back=args.hours,
        parameters=args.parameters,
        place=args.place,
        bbox=args.bbox,
    )

    try:
        with FMIWFSClient() as client:
            response = client.fetch(req)
    except Exception as exc:
        log.error("Failed to fetch WFS data: %s", exc)
        return 1

    # --- Parse ----------------------------------------------------------------
    try:
        observations = WFSParser().parse(response.xml_text)
    except Exception as exc:
        log.error("Failed to parse WFS response: %s", exc)
        return 1

    if not observations:
        log.warning("No observations found for the requested parameters/time window.")
        return 0

    log.info(
        "Fetched %d stations  (%.0f ms)",
        len(observations),
        response.elapsed_ms,
    )

    # --- Print summary --------------------------------------------------------
    import math
    valid_temps = [o.temperature_c for o in observations if not math.isnan(o.temperature_c)]
    if valid_temps:
        print(
            f"\nStations: {len(observations)}"
            f"  |  Temp range: {min(valid_temps):.1f} … {max(valid_temps):.1f} °C\n"
        )

    # --- Build map ------------------------------------------------------------
    map_cfg = WeatherMapConfig(
        output_path=args.output,
        zoom_start=args.zoom,
        auto_open=args.auto_open,
    )
    builder = WeatherMapBuilder(map_cfg)
    m = builder.build(observations)
    out_path = builder.save(m)
    print(f"  Map saved → {out_path.resolve()}\n")
    return 0


def _cli() -> None:
    sys.exit(main())


if __name__ == "__main__":
    _cli()
