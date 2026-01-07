import os
from pathlib import Path

# Data
DATA_DIR = Path(os.getenv("NAVAID_DATA_DIR", "data"))
NAV_PATH = DATA_DIR / "NAV.txt"
FIX_PATH = DATA_DIR / "FIX.txt"

# Server
HOST = os.getenv("NAVAID_HOST", "0.0.0.0")
PORT = int(os.getenv("NAVAID_PORT", "8000"))

