import pytest
from fastapi.testclient import TestClient
from navaid_api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "navaid_count" in data
    assert "fix_count" in data

def test_navaid_not_found():
    response = client.get("/navaids/INVALID")
    assert response.status_code == 404

def test_fix_not_found():
    response = client.get("/fixes/INVALID")
    assert response.status_code == 404
