"""NAVAID API Server - Returns JSON coordinates for FAA NAVAIDs and fixes."""

import math
import re

from fastapi import FastAPI, HTTPException

from .config import NAV_PATH, FIX_PATH, HOST, PORT
from .parser import Navaid, Fix, load_navaids, load_fixes

app = FastAPI(title="NAVAID API", version="1.0.0")

# Global databases
NAVAIDS: dict[str, Navaid] = {}
FIXES: dict[str, Fix] = {}


@app.on_event("startup")
def startup():
    global NAVAIDS, FIXES

    if NAV_PATH.exists():
        NAVAIDS = load_navaids(NAV_PATH)
        print(f"Loaded {len(NAVAIDS)} NAVAIDs from {NAV_PATH}")
    else:
        print(f"Warning: {NAV_PATH} not found. Run download-nasr.sh first.")

    if FIX_PATH.exists():
        FIXES = load_fixes(FIX_PATH)
        print(f"Loaded {len(FIXES)} fixes from {FIX_PATH}")
    else:
        print(f"Warning: {FIX_PATH} not found. Run download-nasr.sh first.")


@app.get("/health")
def health():
    return {"status": "ok", "navaid_count": len(NAVAIDS), "fix_count": len(FIXES)}


@app.get("/navaids/{identifier}")
def get_navaid(identifier: str):
    identifier = identifier.upper()

    # Check for ICAO fix notation: SEA270005 (3-4 char ID + 3 digit radial + 3 digit distance)
    match = re.match(r"^([A-Z]{2,5})(\d{3})(\d{3})$", identifier)
    if match:
        nav_id = match.group(1)
        radial = int(match.group(2))
        distance = int(match.group(3))
        return get_radial_distance(nav_id, radial, distance)

    # Check NAVAIDs first (VORs, TACANs, NDBs)
    navaid = NAVAIDS.get(identifier)
    if navaid:
        return {
            "identifier": navaid.identifier,
            "name": navaid.name,
            "type": navaid.type,
            "latitude": navaid.latitude,
            "longitude": navaid.longitude,
        }

    # Check fixes (intersections, waypoints)
    fix = FIXES.get(identifier)
    if fix:
        return {
            "identifier": fix.identifier,
            "type": "FIX",
            "state": fix.state,
            "latitude": fix.latitude,
            "longitude": fix.longitude,
        }

    raise HTTPException(status_code=404, detail=f"NAVAID/fix '{identifier}' not found")


@app.get("/navaids/{identifier}/{radial}/{distance}")
def get_navaid_radial(identifier: str, radial: int, distance: float):
    identifier = identifier.upper()
    return get_radial_distance(identifier, radial, distance)


def get_radial_distance(identifier: str, radial: int, distance: float) -> dict:
    """Calculate point at radial/distance from a NAVAID or fix."""
    # Find the reference point
    navaid = NAVAIDS.get(identifier)
    fix = FIXES.get(identifier) if not navaid else None

    if not navaid and not fix:
        raise HTTPException(status_code=404, detail=f"NAVAID/fix '{identifier}' not found")

    if not 0 <= radial <= 360:
        raise HTTPException(status_code=400, detail="Radial must be 0-360")
    if distance < 0:
        raise HTTPException(status_code=400, detail="Distance must be positive")

    ref = navaid or fix
    lat, lon = calculate_destination(ref.latitude, ref.longitude, radial, distance)

    return {
        "navaid": ref.identifier,
        "radial": radial,
        "distance_nm": distance,
        "latitude": lat,
        "longitude": lon,
    }


def calculate_destination(
    lat: float, lon: float, bearing: float, distance_nm: float
) -> tuple[float, float]:
    """Calculate destination point given start, bearing, and distance.

    Uses spherical Earth model with mean radius.
    """
    EARTH_RADIUS_NM = 3440.065  # Earth radius in nautical miles

    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)

    # Angular distance
    angular_dist = distance_nm / EARTH_RADIUS_NM

    # Calculate destination
    dest_lat = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist)
        + math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad)
    )

    dest_lon = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
        math.cos(angular_dist) - math.sin(lat_rad) * math.sin(dest_lat),
    )

    return round(math.degrees(dest_lat), 6), round(math.degrees(dest_lon), 6)


def run():
    """CLI entry point for running the server."""
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    run()
