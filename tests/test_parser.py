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
    else:
        pytest.skip("NAV.txt not found")

def test_load_fixes():
    fix_path = Path("data/FIX.txt")
    if fix_path.exists():
        fixes = parser.load_fixes(fix_path)
        assert isinstance(fixes, dict)
        assert all(isinstance(k, str) for k in fixes.keys())
        assert all(isinstance(v, parser.Fix) for v in fixes.values())
    else:
        pytest.skip("FIX.txt not found")
