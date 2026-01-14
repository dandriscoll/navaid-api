# NAVAID API Server

A lightweight Python REST API that returns JSON coordinates (latitude/longitude) for FAA airports, NAVAIDs (VORs, NDBs, TACANs), and fixes (intersections, waypoints).

## Examples

Get an airport:
```
GET /airports/SEA
```
```json
{
  "identifier": "SEA",
  "icao": "KSEA",
  "name": "SEATTLE-TACOMA INTL",
  "city": "SEATTLE",
  "state": "WA",
  "type": "AIRPORT",
  "latitude": 47.449,
  "longitude": -122.309
}
```

Get a NAVAID:
```
GET /navaids/SEA
```
```json
{
  "identifier": "SEA",
  "name": "SEATTLE",
  "type": "VORTAC",
  "latitude": 47.435278,
  "longitude": -122.309722
}
```

Get a waypoint/fix:
```
GET /waypoints/BANGR
```
```json
{
  "identifier": "BANGR",
  "type": "FIX",
  "state": "WA",
  "latitude": 47.462500,
  "longitude": -122.928611
}
```

Get a point 5nm west (270°) of Seattle VOR:
```
GET /navaids/SEA/270/5
GET /navaids/SEA270005
```
```json
{
  "reference": "SEA",
  "type": "navaid",
  "radial": 270,
  "distance_nm": 5,
  "latitude": 47.435278,
  "longitude": -122.398611
}
```

The second format uses ICAO fix notation: `{ID}{RADIAL:3}{DISTANCE:3}` (e.g., `SEA270005` = SEA radial 270, 5nm).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (80)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Linux Server                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    systemd                                │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              navaid-api.service                     │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │         Python (uvicorn + FastAPI)            │  │  │  │
│  │  │  │                                               │  │  │  │
│  │  │  │  - Loads APT.txt, NAV.txt, FIX.txt on startup │  │  │  │
│  │  │  │  - Serves JSON via /airports, /navaids, etc.  │  │  │  │

│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  /var/lib/navaid-api/APT.txt   (airports)                 │  │
│  │  /var/lib/navaid-api/NAV.txt   (VORs, TACANs, NDBs)       │  │
│  │  /var/lib/navaid-api/FIX.txt   (intersections, waypoints) │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Source

Data comes from the FAA's 28-Day NASR Subscription:
- **URL:** http://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/
- **Files:** `APT.txt` (~20,000 airports), `NAV.txt` (~2,600 NAVAIDs), and `FIX.txt` (~70,000 fixes)
- **Update Cycle:** Every 28 days

## Project Structure

```
navaid-api/
├── README.md
├── pyproject.toml               # Package configuration
├── download-nasr.sh             # Download latest FAA data
├── update-data.sh               # Data update (for cron)
├── navaid-api.service           # Example systemd unit file
├── navaid_api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── parser.py                # NAV.txt/FIX.txt parser
│   └── config.py                # Configuration
└── data/
    ├── APT.txt                  # (downloaded) Airports
    ├── NAV.txt                  # (downloaded) VORs, TACANs, NDBs
    └── FIX.txt                  # (downloaded) Intersections, waypoints
```

## Prerequisites

- Python 3.10+
- Linux server with systemd
- Root/sudo access

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/YOURUSER/navaid-api.git

# Or install locally for development
pip install -e .
```

## Quick Start (Development)

```bash
# 1. Clone and enter directory
cd navaid-api

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Download FAA data
./download-nasr.sh

# 5. Run the server
navaid-api
```

Server runs at `http://localhost:8000`

## Production Setup

- **systemd:** Copy `systemd/navaid-api.service` to `/etc/systemd/system/` and adjust paths as needed.

- **Data:** Run `./download-nasr.sh` to fetch the latest FAA NASR data.

## Configuration

Environment variables (set in systemd unit or `.env` file):

| Variable          | Default                  | Description                    |
|-------------------|--------------------------|--------------------------------|
| `NAVAID_DATA_DIR` | `data`                   | Directory containing APT.txt, NAV.txt, and FIX.txt |
| `NAVAID_HOST`     | `0.0.0.0`                | Listen address                 |
| `NAVAID_PORT`     | `8000`                   | Listen port                    |


## API Endpoints

### GET /health

Health check endpoint. Returns the server status and loaded data counts.

**Response:**
```json
{
  "status": "ok",
  "navaid_count": 2600,
  "fix_count": 70000,
  "airport_count": 20000
}
```

---

### GET /airports/{identifier}

Get airport by FAA LID (e.g., `SEA`) or ICAO code (e.g., `KSEA`).

**Example:** `GET /airports/SEA`
```json
{
  "identifier": "SEA",
  "icao": "KSEA",
  "name": "SEATTLE-TACOMA INTL",
  "city": "SEATTLE",
  "state": "WA",
  "type": "AIRPORT",
  "latitude": 47.449,
  "longitude": -122.309
}
```

### GET /airports/{identifier}/{radial}/{distance}

Calculate a point at a given radial (degrees) and distance (nautical miles) from an airport.

**Example:** `GET /airports/SEA/270/10`
```json
{
  "reference": "SEA",
  "type": "airport",
  "radial": 270,
  "distance_nm": 10,
  "latitude": 47.449,
  "longitude": -122.487
}
```

---

### GET /navaids/{identifier}

Get NAVAID (VOR, VORTAC, TACAN, NDB) by identifier. Also supports ICAO fix notation.

**Example:** `GET /navaids/SEA`
```json
{
  "identifier": "SEA",
  "name": "SEATTLE",
  "type": "VORTAC",
  "latitude": 47.435278,
  "longitude": -122.309722
}
```

**ICAO Fix Notation:** `GET /navaids/SEA270005`

The format is `{ID}{RADIAL:3}{DISTANCE:3}` - e.g., `SEA270005` means SEA radial 270°, 5nm.

### GET /navaids/{identifier}/{radial}/{distance}

Calculate a point at a given radial (degrees) and distance (nautical miles) from a NAVAID.

**Example:** `GET /navaids/SEA/270/5`
```json
{
  "reference": "SEA",
  "type": "navaid",
  "radial": 270,
  "distance_nm": 5,
  "latitude": 47.435278,
  "longitude": -122.398611
}
```

---

### GET /waypoints/{identifier}

Get fix/waypoint (intersection, named waypoint) by identifier.

**Example:** `GET /waypoints/BANGR`
```json
{
  "identifier": "BANGR",
  "type": "FIX",
  "state": "WA",
  "latitude": 47.4625,
  "longitude": -122.928611
}
```

### GET /waypoints/{identifier}/{radial}/{distance}

Calculate a point at a given radial (degrees) and distance (nautical miles) from a waypoint.

**Example:** `GET /waypoints/BANGR/090/10`
```json
{
  "reference": "BANGR",
  "type": "waypoint",
  "radial": 90,
  "distance_nm": 10,
  "latitude": 47.4625,
  "longitude": -122.75
}
```

---

### GET /points/{identifier}

Search across all types (airports, navaids, waypoints) by identifier. Returns the first match in order: airports → navaids → waypoints. Also supports ICAO fix notation.

**Example:** `GET /points/SEA`

### GET /points/{identifier}/{radial}/{distance}

Calculate a point at a given radial and distance from any reference point (airport, navaid, or waypoint).

**Example:** `GET /points/SEA/180/20`

---

### Error Responses

**404 Not Found:**
```json
{
  "detail": "NAVAID 'XYZ' not found"
}
```

**400 Bad Request:**
```json
{
  "detail": "Radial must be 0-360"
}
```




- **Data updates:** FAA NASR data updates every 28 days. Run `./update-data.sh` via cron to keep data current.

## Troubleshooting

Check logs with `sudo journalctl -u navaid-api -f`. Common issues:

- **Data files not found (APT.txt, NAV.txt, FIX.txt):** Run `./download-nasr.sh`



## License

MIT

## Data Attribution

NAVAID data is sourced from the FAA National Airspace System Resources (NASR) subscription. This data is public domain as a work of the U.S. federal government.
