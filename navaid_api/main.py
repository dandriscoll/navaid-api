"""NAVAID API Server - Returns JSON coordinates for FAA airports, NAVAIDs, and waypoints."""

import math
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import NAV_PATH, FIX_PATH, APT_PATH, HOST, PORT
from .parser import Navaid, Fix, Airport, load_navaids, load_fixes, load_airports

# Global databases
NAVAIDS: dict[str, Navaid] = {}
FIXES: dict[str, Fix] = {}
AIRPORTS: dict[str, Airport] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global NAVAIDS, FIXES, AIRPORTS

    if NAV_PATH.exists():
        NAVAIDS = load_navaids(NAV_PATH)
        print(f"Loaded {len(NAVAIDS)} NAVAIDs from {NAV_PATH}")
    else:
        print(f"Warning: {NAV_PATH} not found. Run navaid-download first.")

    if FIX_PATH.exists():
        FIXES = load_fixes(FIX_PATH)
        print(f"Loaded {len(FIXES)} fixes from {FIX_PATH}")
    else:
        print(f"Warning: {FIX_PATH} not found. Run navaid-download first.")

    if APT_PATH.exists():
        AIRPORTS = load_airports(APT_PATH)
        print(f"Loaded {len(AIRPORTS)} airports from {APT_PATH}")
    else:
        print(f"Warning: {APT_PATH} not found. Run navaid-download first.")

    yield


app = FastAPI(title="NAVAID API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "navaid_count": len(NAVAIDS),
        "fix_count": len(FIXES),
        "airport_count": len(AIRPORTS),
    }


@app.get("/airports/{identifier}")
def get_airport(identifier: str):
    """Get airport by FAA LID (e.g., SEA) or ICAO code (e.g., KSEA)."""
    identifier = identifier.upper()

    airport = AIRPORTS.get(identifier)
    if airport:
        return {
            "identifier": airport.identifier,
            "icao": airport.icao,
            "name": airport.name,
            "city": airport.city,
            "state": airport.state,
            "type": airport.type,
            "latitude": airport.latitude,
            "longitude": airport.longitude,
        }

    raise HTTPException(status_code=404, detail=f"Airport '{identifier}' not found")


@app.get("/waypoints/{identifier}")
def get_waypoint(identifier: str):
    """Get fix/waypoint by identifier."""
    identifier = identifier.upper()

    fix = FIXES.get(identifier)
    if fix:
        return {
            "identifier": fix.identifier,
            "type": "FIX",
            "state": fix.state,
            "latitude": fix.latitude,
            "longitude": fix.longitude,
        }

    raise HTTPException(status_code=404, detail=f"Waypoint '{identifier}' not found")


@app.get("/navaids/{identifier}")
def get_navaid(identifier: str):
    """Get NAVAID (VOR, TACAN, NDB) by identifier."""
    identifier = identifier.upper()

    # Check for ICAO fix notation: SEA270005 (3-4 char ID + 3 digit radial + 3 digit distance)
    match = re.match(r"^([A-Z]{2,5})(\d{3})(\d{3})$", identifier)
    if match:
        nav_id = match.group(1)
        radial = int(match.group(2))
        distance = int(match.group(3))
        return get_radial_distance(nav_id, radial, distance)

    navaid = NAVAIDS.get(identifier)
    if navaid:
        return {
            "identifier": navaid.identifier,
            "name": navaid.name,
            "type": navaid.type,
            "latitude": navaid.latitude,
            "longitude": navaid.longitude,
        }

    raise HTTPException(status_code=404, detail=f"NAVAID '{identifier}' not found")


@app.get("/points/{identifier}")
def get_point(identifier: str):
    """Search all types (airports, navaids, waypoints) by identifier."""
    identifier = identifier.upper()

    # Check for ICAO fix notation: SEA270005
    match = re.match(r"^([A-Z]{2,5})(\d{3})(\d{3})$", identifier)
    if match:
        nav_id = match.group(1)
        radial = int(match.group(2))
        distance = int(match.group(3))
        return get_radial_distance(nav_id, radial, distance)

    # Check airports first
    airport = AIRPORTS.get(identifier)
    if airport:
        return {
            "identifier": airport.identifier,
            "icao": airport.icao,
            "name": airport.name,
            "city": airport.city,
            "state": airport.state,
            "type": airport.type,
            "latitude": airport.latitude,
            "longitude": airport.longitude,
        }

    # Check NAVAIDs (VORs, TACANs, NDBs)
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

    raise HTTPException(status_code=404, detail=f"'{identifier}' not found")


@app.get("/airports/{identifier}/{radial}/{distance}")
def get_airport_radial(identifier: str, radial: int, distance: float):
    """Calculate point at radial/distance from an airport."""
    identifier = identifier.upper()
    return get_radial_distance(identifier, radial, distance, airports_only=True)


@app.get("/waypoints/{identifier}/{radial}/{distance}")
def get_waypoint_radial(identifier: str, radial: int, distance: float):
    """Calculate point at radial/distance from a waypoint."""
    identifier = identifier.upper()
    return get_radial_distance(identifier, radial, distance, waypoints_only=True)


@app.get("/navaids/{identifier}/{radial}/{distance}")
def get_navaid_radial(identifier: str, radial: int, distance: float):
    """Calculate point at radial/distance from a NAVAID."""
    identifier = identifier.upper()
    return get_radial_distance(identifier, radial, distance, navaids_only=True)


@app.get("/points/{identifier}/{radial}/{distance}")
def get_point_radial(identifier: str, radial: int, distance: float):
    """Calculate point at radial/distance from any reference point."""
    identifier = identifier.upper()
    return get_radial_distance(identifier, radial, distance)


def get_radial_distance(
    identifier: str,
    radial: int,
    distance: float,
    airports_only: bool = False,
    navaids_only: bool = False,
    waypoints_only: bool = False,
) -> dict:
    """Calculate point at radial/distance from a reference point."""
    ref = None
    ref_type = None

    if airports_only:
        ref = AIRPORTS.get(identifier)
        ref_type = "airport"
    elif navaids_only:
        ref = NAVAIDS.get(identifier)
        ref_type = "navaid"
    elif waypoints_only:
        ref = FIXES.get(identifier)
        ref_type = "waypoint"
    else:
        # Search all types: airports, navaids, fixes
        ref = AIRPORTS.get(identifier)
        if ref:
            ref_type = "airport"
        if not ref:
            ref = NAVAIDS.get(identifier)
            if ref:
                ref_type = "navaid"
        if not ref:
            ref = FIXES.get(identifier)
            if ref:
                ref_type = "waypoint"

    if not ref:
        if airports_only:
            raise HTTPException(status_code=404, detail=f"Airport '{identifier}' not found")
        elif navaids_only:
            raise HTTPException(status_code=404, detail=f"NAVAID '{identifier}' not found")
        elif waypoints_only:
            raise HTTPException(status_code=404, detail=f"Waypoint '{identifier}' not found")
        else:
            raise HTTPException(status_code=404, detail=f"'{identifier}' not found")

    if not 0 <= radial <= 360:
        raise HTTPException(status_code=400, detail="Radial must be 0-360")
    if distance < 0:
        raise HTTPException(status_code=400, detail="Distance must be positive")

    lat, lon = calculate_destination(ref.latitude, ref.longitude, radial, distance)

    return {
        "reference": ref.identifier,
        "type": ref_type,
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
