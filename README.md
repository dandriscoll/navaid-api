# NAVAID API Server

A lightweight Python REST API that returns JSON coordinates (latitude/longitude) for FAA NAVAIDs (VORs, NDBs, TACANs) and fixes (intersections, waypoints).

## Examples

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

```
GET /navaids/BANGR
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
  "navaid": "SEA",
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
│  │  │  │  - Loads NAV.txt + FIX.txt on startup         │  │  │  │
│  │  │  │  - Serves JSON via /navaids/<ID>              │  │  │  │

│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  /var/lib/navaid-api/NAV.txt   (VORs, TACANs, NDBs)       │  │
│  │  /var/lib/navaid-api/FIX.txt   (intersections, waypoints) │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Source

Data comes from the FAA's 28-Day NASR Subscription:
- **URL:** http://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/
- **Files:** `NAV.txt` (~2,600 NAVAIDs) and `FIX.txt` (~70,000 fixes)
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
| `NAVAID_DATA_DIR` | `data`                   | Directory containing NAV.txt and FIX.txt |
| `NAVAID_HOST`     | `0.0.0.0`                | Listen address                 |
| `NAVAID_PORT`     | `8000`                   | Listen port                    |


## API Endpoints

### GET /navaids/{identifier}

Returns NAVAID or fix information by identifier. NAVAIDs are checked first.

### GET /navaids/{identifier}/{radial}/{distance}

Returns coordinates for a point at a given radial and distance from a NAVAID or fix. Also accepts ICAO fix notation: `/navaids/SEA270005` (3-digit radial + 3-digit distance in nm).

### GET /health

Returns `{"status": "ok", "navaid_count": N, "fix_count": N}`




- **Data updates:** FAA NASR data updates every 28 days. Run `./update-data.sh` via cron to keep data current.

## Troubleshooting

Check logs with `sudo journalctl -u navaid-api -f`. Common issues:

- **NAV.txt not found:** Run `./download-nasr.sh`



## License

MIT

## Data Attribution

NAVAID data is sourced from the FAA National Airspace System Resources (NASR) subscription. This data is public domain as a work of the U.S. federal government.
