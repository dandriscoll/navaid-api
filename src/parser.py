"""Parser for FAA NASR NAV.txt and FIX.txt fixed-width files."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Navaid:
    identifier: str
    name: str
    type: str
    latitude: float
    longitude: float


@dataclass
class Fix:
    identifier: str
    state: str
    latitude: float
    longitude: float


def parse_dms(dms_str: str) -> float:
    """Parse DD-MM-SS.SSSH format to decimal degrees."""
    match = re.match(r"(\d+)-(\d+)-([\d.]+)([NSEW])", dms_str.strip())
    if not match:
        raise ValueError(f"Invalid DMS format: {dms_str}")

    degrees = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    hemisphere = match.group(4)

    decimal = degrees + minutes / 60 + seconds / 3600

    if hemisphere in ("S", "W"):
        decimal = -decimal

    return round(decimal, 6)


def load_navaids(path: Path) -> dict[str, Navaid]:
    """Load NAV.txt and return dict of identifier -> Navaid."""
    navaids: dict[str, Navaid] = {}

    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            if len(line) < 411:
                continue

            # Only process NAV1 records
            record_type = line[0:4].strip()
            if record_type != "NAV1":
                continue

            # Extract fields (1-indexed positions from spec, convert to 0-indexed)
            identifier = line[4:8].strip()
            nav_type = line[8:28].strip()
            name = line[42:72].strip()
            lat_str = line[371:385].strip()
            lon_str = line[396:410].strip()

            if not identifier or not lat_str or not lon_str:
                continue

            try:
                navaid = Navaid(
                    identifier=identifier,
                    name=name,
                    type=nav_type,
                    latitude=parse_dms(lat_str),
                    longitude=parse_dms(lon_str),
                )
                navaids[identifier] = navaid
            except ValueError:
                continue

    return navaids


def load_fixes(path: Path) -> dict[str, Fix]:
    """Load FIX.txt and return dict of identifier -> Fix."""
    fixes: dict[str, Fix] = {}

    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            if len(line) < 95:
                continue

            # Only process FIX1 records
            record_type = line[0:4].strip()
            if record_type != "FIX1":
                continue

            # Extract fields (1-indexed positions from spec, convert to 0-indexed)
            # Fix ID: pos 5-34 (30 chars)
            # State: pos 35-36 (2 chars)
            # Lat: pos 67-80 (14 chars)
            # Lon: pos 81-94 (14 chars)
            identifier = line[4:34].strip()
            state = line[34:36].strip()
            lat_str = line[66:80].strip()
            lon_str = line[80:94].strip()

            if not identifier or not lat_str or not lon_str:
                continue

            try:
                fix = Fix(
                    identifier=identifier,
                    state=state,
                    latitude=parse_dms(lat_str),
                    longitude=parse_dms(lon_str),
                )
                fixes[identifier] = fix
            except ValueError:
                continue

    return fixes
