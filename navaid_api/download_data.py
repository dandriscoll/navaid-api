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


FILES_TO_EXTRACT = (
    ("NAV.txt", "NAV1"),
    ("FIX.txt", "FIX1"),
    ("APT.txt", "APT"),
)


def validate_extracted(path: Path, expected_prefix: str) -> None:
    """Raise RuntimeError if path is empty or its first record does not start with expected_prefix."""
    if path.stat().st_size == 0:
        raise RuntimeError(f"{path.name} validation failed: file is empty")

    with open(path, "r", encoding="latin-1") as f:
        first = f.readline()

    if not first.startswith(expected_prefix):
        raise RuntimeError(
            f"{path.name} validation failed: first record does not start with {expected_prefix!r}"
        )


def download(data_dir: Path | None = None) -> None:
    """Download and extract NASR data files atomically.

    Stages all three files into a temp dir under data_dir, validates each,
    and only then os.replace()s them into place. A failure before the rename
    block leaves the live data dir untouched.
    """
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
        # Stage under data_dir so os.replace stays on the same filesystem.
        with tempfile.TemporaryDirectory(prefix=".navaid-stage-", dir=data_dir) as stage_str:
            stage_dir = Path(stage_str)

            staged: list[tuple[Path, str]] = []
            for filename, prefix in FILES_TO_EXTRACT:
                print(f"Extracting {filename}...")
                staged_path = stage_dir / filename
                extract_file_from_zip(tmp_path, filename, staged_path)
                validate_extracted(staged_path, prefix)
                staged.append((staged_path, filename))

            print(f"Installing into {data_dir}/...")
            for staged_path, filename in staged:
                staged_path.replace(data_dir / filename)
    finally:
        tmp_path.unlink()

    nav_count = count_records(data_dir / "NAV.txt", "NAV1")
    fix_count = count_records(data_dir / "FIX.txt", "FIX1")
    apt_count = count_records(data_dir / "APT.txt", "APT")
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
