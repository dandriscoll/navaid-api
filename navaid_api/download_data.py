"""Download FAA NASR subscription data (NAV.txt, FIX.txt, and APT.txt)."""

import argparse
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

from navaid_api.config import DATA_DIR

NASR_URL = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"
ZIP_PATTERN = re.compile(
    r"https://nfdc\.faa\.gov/webContent/28DaySub/28DaySubscription_Effective_[\d-]+\.zip"
)


def find_zip_url() -> str:
    """Fetch NASR subscription page and extract the ZIP download URL."""
    print("Fetching latest NASR subscription ZIP download URL...")
    with urlopen(NASR_URL) as response:
        html = response.read().decode("utf-8")

    match = ZIP_PATTERN.search(html)
    if not match:
        raise RuntimeError("Could not find NASR subscription ZIP download link")

    return match.group(0)


def extract_file_from_zip(zip_path: Path, filename: str, output_path: Path) -> None:
    """Extract a file from ZIP, trying both root and subdirectory paths."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Try direct path first
        if filename in zf.namelist():
            output_path.write_bytes(zf.read(filename))
            return

        # Try finding in subdirectories
        for name in zf.namelist():
            if name.endswith(f"/{filename}") or name == filename:
                output_path.write_bytes(zf.read(name))
                return

        raise FileNotFoundError(f"{filename} not found in ZIP archive")


def count_records(file_path: Path, prefix: str) -> int:
    """Count lines starting with the given prefix."""
    count = 0
    with open(file_path, "r", encoding="latin-1") as f:
        for line in f:
            if line.startswith(prefix):
                count += 1
    return count


def download(data_dir: Path | None = None) -> None:
    """Download and extract NASR data files."""
    if data_dir is None:
        data_dir = DATA_DIR

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    zip_url = find_zip_url()
    print(f"Downloading: {zip_url}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        with urlopen(zip_url) as response:
            tmp.write(response.read())

    try:
        print("Extracting NAV.txt...")
        nav_path = data_dir / "NAV.txt"
        extract_file_from_zip(tmp_path, "NAV.txt", nav_path)

        print("Extracting FIX.txt...")
        fix_path = data_dir / "FIX.txt"
        extract_file_from_zip(tmp_path, "FIX.txt", fix_path)

        print("Extracting APT.txt...")
        apt_path = data_dir / "APT.txt"
        extract_file_from_zip(tmp_path, "APT.txt", apt_path)
    finally:
        tmp_path.unlink()

    nav_count = count_records(nav_path, "NAV1")
    fix_count = count_records(fix_path, "FIX1")
    apt_count = count_records(apt_path, "APT")
    print(f"Done. Extracted {nav_count} NAVAIDs, {fix_count} fixes, and {apt_count} airports to {data_dir}/")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Download FAA NASR subscription data (NAV.txt, FIX.txt, and APT.txt)"
    )
    parser.add_argument(
        "data_dir",
        nargs="?",
        type=Path,
        default=None,
        help=f"Output directory for data files (default: {DATA_DIR})",
    )
    args = parser.parse_args()

    try:
        download(args.data_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
