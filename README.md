# NAVAID API Server

A lightweight Python REST API that returns JSON coordinates (latitude/longitude) for FAA NAVAIDs (VORs, NDBs, TACANs, etc.).

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

The second format uses ICAO fix notation: `{NAVAID}{RADIAL:3}{DISTANCE:3}` (e.g., `SEA270005` = SEA radial 270, 5nm).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS (443)
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
│  │  │  │  - Loads NAV.txt on startup                   │  │  │  │
│  │  │  │  - Serves JSON via /navaids/<ID>              │  │  │  │
│  │  │  │  - TLS via Let's Encrypt certs                │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  /var/lib/navaid-api/NAV.txt   (FAA NASR data)            │  │
│  │  /etc/letsencrypt/live/<domain>/   (SSL certs)            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Source

NAVAID data comes from the FAA's 28-Day NASR Subscription:
- **URL:** https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/
- **Format:** Fixed-width text file (`NAV.txt`) with 805-character records
- **Update Cycle:** Every 28 days

### NAV.txt Record Structure (NAV1 records)

| Field        | Position | Length | Description                     |
|--------------|----------|--------|---------------------------------|
| Identifier   | 5        | 4      | NAVAID ID (e.g., "SEA")         |
| Type         | 9        | 20     | NAVAID type (e.g., "VORTAC")    |
| Name         | 43       | 30     | Facility name (e.g., "SEATTLE") |
| Latitude     | 372      | 14     | Format: DD-MM-SS.SSSH           |
| Longitude    | 397      | 14     | Format: DDD-MM-SS.SSSH          |

## Project Structure

```
navaid-api/
├── README.md
├── requirements.txt
├── download-nasr.sh             # Download latest FAA data
├── install.sh                   # Production installation
├── update-data.sh               # Data update (for cron)
├── navaid-api.service           # Example systemd unit file
├── src/
│   ├── main.py                  # FastAPI application
│   ├── parser.py                # NAV.txt parser
│   └── config.py                # Configuration
└── data/
    └── NAV.txt                  # (downloaded FAA data)
```

## Prerequisites

- Python 3.10+
- Linux server with systemd
- Domain name (for Let's Encrypt)
- Root/sudo access

## Quick Start (Development)

```bash
# 1. Clone and enter directory
cd navaid-api

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download FAA data
./download-nasr.sh

# 5. Run development server
python src/main.py
```

Server runs at `http://localhost:8000`

## Production Setup

Run `./install.sh` for a guided installation, or configure manually:

- **systemd:** Copy `systemd/navaid-api.service` to `/etc/systemd/system/` and adjust paths as needed.
- **SSL:** Set `NAVAID_SSL_CERT` and `NAVAID_SSL_KEY` in your environment or `.env` file to point to your Let's Encrypt certificates.
- **Data:** Run `./download-nasr.sh` to fetch the latest FAA NASR data.

## Configuration

Environment variables (set in systemd unit or `.env` file):

| Variable          | Default                      | Description                    |
|-------------------|------------------------------|--------------------------------|
| `NAVAID_DATA_PATH`| `/var/lib/navaid-api/NAV.txt`| Path to NAV.txt file           |
| `NAVAID_HOST`     | `0.0.0.0`                    | Listen address                 |
| `NAVAID_PORT`     | `443`                        | Listen port                    |
| `NAVAID_SSL_CERT` | (none)                       | Path to SSL certificate        |
| `NAVAID_SSL_KEY`  | (none)                       | Path to SSL private key        |

## API Endpoints

### GET /navaids/{identifier}

Returns NAVAID information by identifier.

**Response:**
```json
{
  "identifier": "SEA",
  "name": "SEATTLE",
  "type": "VORTAC",
  "latitude": 47.435278,
  "longitude": -122.309722
}
```

**Errors:**
- `404` - NAVAID not found

### GET /navaids/{identifier}/{radial}/{distance}

Returns coordinates for a point at a given radial and distance from a NAVAID. Also accepts ICAO fix notation: `/navaids/SEA270005` (3-digit radial + 3-digit distance in nm).

**Response:**
```json
{
  "navaid": "SEA",
  "radial": 270,
  "distance_nm": 5,
  "latitude": 47.435278,
  "longitude": -122.398611
}
```

**Errors:**
- `404` - NAVAID not found
- `400` - Invalid radial/distance format

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "navaid_count": 3421
}
```

## SSL & Data Updates

- **Certificate renewal:** Add a hook at `/etc/letsencrypt/renewal-hooks/post/navaid-api-restart.sh` to restart the service after certbot renews.
- **Data updates:** FAA NASR data updates every 28 days. Run `./update-data.sh` via cron to keep data current.

## Troubleshooting

Check logs with `sudo journalctl -u navaid-api -f`. Common issues:

- **NAV.txt not found:** Run `./download-nasr.sh`
- **SSL permission denied:** Ensure the service user can read `/etc/letsencrypt/live/your-domain/`
- **Port 443 in use:** Check for conflicting services

## License

MIT

## Data Attribution

NAVAID data is sourced from the FAA National Airspace System Resources (NASR) subscription. This data is public domain as a work of the U.S. federal government.
