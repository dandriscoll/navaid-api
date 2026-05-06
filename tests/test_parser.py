import pytest
from navaid_api import parser
from pathlib import Path

def test_load_navaids():
    nav_path = Path("data/NAV.txt")
    if nav_path.exists():
        navaids = parser.load_navaids(nav_path)
        assert isinstance(navaids, dict)
        assert all(isinstance(k, str) for k in navaids.keys())
        assert all(isinstance(v, parser.Navaid) for v in navaids.values())
        assert len(navaids) > 1000
    else:
        pytest.skip("NAV.txt not found")

def test_load_fixes():
    fix_path = Path("data/FIX.txt")
    if fix_path.exists():
        fixes = parser.load_fixes(fix_path)
        assert isinstance(fixes, dict)
        assert all(isinstance(k, str) for k in fixes.keys())
        assert all(isinstance(v, parser.Fix) for v in fixes.values())
        assert len(fixes) > 30000
    else:
        pytest.skip("FIX.txt not found")


def test_load_airports():
    apt_path = Path("data/APT.txt")
    if apt_path.exists():
        airports = parser.load_airports(apt_path)
        assert isinstance(airports, dict)
        assert all(isinstance(k, str) for k in airports.keys())
        assert all(isinstance(v, parser.Airport) for v in airports.values())
        assert len(airports) > 10000
    else:
        pytest.skip("APT.txt not found")


import re


def test_load_effective_date_from_real_data():
    apt_path = Path("data/APT.txt")
    if apt_path.exists():
        date = parser.load_effective_date(apt_path)
        assert date is not None
        assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", date)
    else:
        pytest.skip("APT.txt not found")


def test_load_effective_date_malformed_first_line(tmp_path):
    apt_path = tmp_path / "APT.txt"
    apt_path.write_text("GARBAGE LINE WITHOUT VALID PREFIX OR DATE\n", encoding="latin-1")
    assert parser.load_effective_date(apt_path) is None


def test_load_effective_date_short_first_line(tmp_path):
    apt_path = tmp_path / "APT.txt"
    apt_path.write_text("APT\n", encoding="latin-1")
    assert parser.load_effective_date(apt_path) is None


def test_load_effective_date_valid_synthetic(tmp_path):
    apt_path = tmp_path / "APT.txt"
    # Build a 41+ char first line where columns 31-41 are a valid MM/DD/YYYY.
    line = "APT" + ("X" * 28) + "07/04/2031" + " trailing garbage\n"
    apt_path.write_text(line, encoding="latin-1")
    assert parser.load_effective_date(apt_path) == "07/04/2031"
