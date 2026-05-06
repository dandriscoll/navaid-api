"""Tests for navaid_api.download_data — focus on atomic-rename behaviour."""

import zipfile
from pathlib import Path

import pytest

from navaid_api import download_data


def _build_zip(zip_path: Path, entries: dict[str, bytes]) -> None:
    """Write a ZIP at zip_path with the given {filename: bytes} entries."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def _valid_entries() -> dict[str, bytes]:
    """Realistic-shaped entries that pass download_data.validate_extracted."""
    return {
        "NAV.txt": b"NAV1" + b" " * 408 + b"\n",
        "FIX.txt": b"FIX1" + b" " * 92 + b"\n",
        "APT.txt": b"APT" + b" " * 1208 + b"\n",
    }


def _patch_url_and_zip(monkeypatch, zip_path: Path) -> None:
    """Make download.find_zip_url and urlopen yield the given local zip."""
    monkeypatch.setattr(download_data, "find_zip_url", lambda: f"file://{zip_path}")


def test_download_happy_path(tmp_path, monkeypatch):
    """All three files land in the live data dir."""
    zip_path = tmp_path / "fixture.zip"
    _build_zip(zip_path, _valid_entries())
    _patch_url_and_zip(monkeypatch, zip_path)

    data_dir = tmp_path / "data"
    download_data.download(data_dir)

    assert (data_dir / "NAV.txt").read_bytes().startswith(b"NAV1")
    assert (data_dir / "FIX.txt").read_bytes().startswith(b"FIX1")
    assert (data_dir / "APT.txt").read_bytes().startswith(b"APT")


def test_download_missing_entry_leaves_data_dir_untouched(tmp_path, monkeypatch):
    """If the ZIP is missing APT.txt, the prior cycle's files survive intact."""
    entries = _valid_entries()
    del entries["APT.txt"]
    zip_path = tmp_path / "fixture.zip"
    _build_zip(zip_path, entries)
    _patch_url_and_zip(monkeypatch, zip_path)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "NAV.txt").write_bytes(b"OLD-NAV")
    (data_dir / "FIX.txt").write_bytes(b"OLD-FIX")
    (data_dir / "APT.txt").write_bytes(b"OLD-APT")

    with pytest.raises(FileNotFoundError):
        download_data.download(data_dir)

    assert (data_dir / "NAV.txt").read_bytes() == b"OLD-NAV"
    assert (data_dir / "FIX.txt").read_bytes() == b"OLD-FIX"
    assert (data_dir / "APT.txt").read_bytes() == b"OLD-APT"
    # Stage dir cleaned up — no residue under data_dir.
    assert sorted(p.name for p in data_dir.iterdir()) == ["APT.txt", "FIX.txt", "NAV.txt"]


def test_download_validation_failure_leaves_data_dir_untouched(tmp_path, monkeypatch):
    """If APT.txt content does not start with the expected prefix, the prior cycle's files survive."""
    entries = _valid_entries()
    entries["APT.txt"] = b"GARBAGE-CONTENT-DOES-NOT-START-WITH-APT\n"
    zip_path = tmp_path / "fixture.zip"
    _build_zip(zip_path, entries)
    _patch_url_and_zip(monkeypatch, zip_path)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "NAV.txt").write_bytes(b"OLD-NAV")
    (data_dir / "FIX.txt").write_bytes(b"OLD-FIX")
    (data_dir / "APT.txt").write_bytes(b"OLD-APT")

    with pytest.raises(RuntimeError, match="APT.txt validation failed"):
        download_data.download(data_dir)

    assert (data_dir / "NAV.txt").read_bytes() == b"OLD-NAV"
    assert (data_dir / "FIX.txt").read_bytes() == b"OLD-FIX"
    assert (data_dir / "APT.txt").read_bytes() == b"OLD-APT"


def test_download_empty_file_validation_fails(tmp_path, monkeypatch):
    """Empty extracted file fails validation before the rename block."""
    entries = _valid_entries()
    entries["FIX.txt"] = b""
    zip_path = tmp_path / "fixture.zip"
    _build_zip(zip_path, entries)
    _patch_url_and_zip(monkeypatch, zip_path)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "FIX.txt").write_bytes(b"OLD-FIX")

    with pytest.raises(RuntimeError, match="FIX.txt validation failed: file is empty"):
        download_data.download(data_dir)

    assert (data_dir / "FIX.txt").read_bytes() == b"OLD-FIX"
