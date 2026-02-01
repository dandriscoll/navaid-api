"""NAVAID API Server - Returns JSON coordinates for FAA airports, NAVAIDs, and waypoints."""

import math
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NAVAID API</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         color: #1a1a2e; background: #f0f2f5; line-height: 1.6; }
  .hero { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
          color: #fff; padding: 3.5rem 1.5rem 2.5rem; text-align: center; }
  .hero h1 { font-size: 2.4rem; font-weight: 700; letter-spacing: -0.5px; }
  .hero p  { margin-top: .5rem; font-size: 1.1rem; opacity: .85; max-width: 600px;
             margin-left: auto; margin-right: auto; }
  .container { max-width: 820px; margin: -1.5rem auto 3rem; padding: 0 1.25rem; }
  .card { background: #fff; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,.08);
          padding: 2rem; margin-bottom: 1.25rem; }
  .card h2 { font-size: 1.15rem; margin-bottom: .75rem; color: #203a43; }
  .card p, .card li { font-size: .95rem; color: #444; }
  .card ul { padding-left: 1.25rem; }
  .card li { margin-bottom: .35rem; }
  code { background: #eef1f5; padding: .15em .4em; border-radius: 4px; font-size: .88em; }
  a { color: #2c7be5; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .links { display: flex; gap: .75rem; flex-wrap: wrap; }
  .links a { display: inline-block; padding: .55rem 1.2rem; border-radius: 6px;
             background: #2c5364; color: #fff; font-weight: 500; font-size: .9rem; }
  .links a:hover { background: #203a43; text-decoration: none; }
  .endpoint { font-family: monospace; background: #eef1f5; padding: .3rem .6rem;
              border-radius: 4px; display: inline-block; margin: .15rem 0; }
</style>
</head>
<body>
<div class="hero">
  <h1>NAVAID API</h1>
  <p>A lightweight REST API serving FAA airport, NAVAID, and waypoint coordinate data with radial/distance calculations.</p>
</div>
<div class="container">

  <div class="card">
    <h2>Overview</h2>
    <p>Query U.S. aviation navigation reference points by identifier and optionally compute
       a destination along a radial and distance (in nautical miles). Data is sourced from
       the FAA 28-Day NASR Subscription.</p>
    <ul>
      <li><span class="endpoint">GET /airports/{id}</span> &mdash; Airport lookup by FAA LID or ICAO code</li>
      <li><span class="endpoint">GET /navaids/{id}</span> &mdash; VOR / NDB / TACAN lookup (supports ICAO fix notation)</li>
      <li><span class="endpoint">GET /waypoints/{id}</span> &mdash; Named fix / intersection lookup</li>
      <li><span class="endpoint">GET /points/{id}</span> &mdash; Unified search across all types</li>
      <li>Append <code>/{radial}/{distance}</code> to any endpoint above to compute a point along a bearing.</li>
    </ul>
  </div>

  <div class="card">
    <h2>Agent Instructions</h2>
    <p>If you are an AI agent or tool consuming this API:</p>
    <ul>
      <li>All responses are JSON. Coordinates are returned as <code>latitude</code> / <code>longitude</code> in decimal degrees.</li>
      <li>Identifiers are case-insensitive (e.g. <code>ksea</code> and <code>KSEA</code> are equivalent).</li>
      <li>Use the <code>/points/{id}</code> endpoint when you don't know the reference type.</li>
      <li>Radial is a magnetic bearing in degrees (0-360). Distance is in nautical miles.</li>
      <li>ICAO fix notation is supported on the navaids endpoint, e.g. <code>/navaids/SEA270005</code> = SEA radial 270&deg; at 5 NM.</li>
      <li>Check <code>/health</code> to verify the service is up and see loaded record counts.</li>
      <li>Refer to the OpenAPI schema below for full request/response schemas.</li>
    </ul>
  </div>

  <div class="card">
    <h2>Links</h2>
    <div class="links">
      <a href="/docs">Swagger UI</a>
      <a href="/openapi.json">OpenAPI Schema</a>
      <a href="/redoc">ReDoc</a>
      <a href="https://github.com/dandriscoll/navaid-api">GitHub</a>
    </div>
  </div>

</div>
</body>
</html>"""


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
