import pytest
from fastapi.testclient import TestClient

from navaid_api import main
from navaid_api.parser import Airport, Navaid, Fix


@pytest.fixture(autouse=True)
def setup_test_data():
    """Set up test data before each test."""
    main.AIRPORTS = {
        "SEA": Airport(
            identifier="SEA",
            icao="KSEA",
            name="SEATTLE-TACOMA INTL",
            city="SEATTLE",
            state="WA",
            type="AIRPORT",
            latitude=47.449,
            longitude=-122.309,
        ),
        "KSEA": Airport(
            identifier="SEA",
            icao="KSEA",
            name="SEATTLE-TACOMA INTL",
            city="SEATTLE",
            state="WA",
            type="AIRPORT",
            latitude=47.449,
            longitude=-122.309,
        ),
        "PDX": Airport(
            identifier="PDX",
            icao="KPDX",
            name="PORTLAND INTL",
            city="PORTLAND",
            state="OR",
            type="AIRPORT",
            latitude=45.588,
            longitude=-122.598,
        ),
    }

    main.NAVAIDS = {
        "SEA": Navaid(
            identifier="SEA",
            name="SEATTLE",
            type="VORTAC",
            latitude=47.435278,
            longitude=-122.309722,
        ),
        "BTG": Navaid(
            identifier="BTG",
            name="BATTLEGROUND",
            type="VOR/DME",
            latitude=45.815,
            longitude=-122.563,
        ),
    }

    main.FIXES = {
        "BANGR": Fix(
            identifier="BANGR",
            state="WA",
            latitude=47.4625,
            longitude=-122.928611,
        ),
        "WAVEY": Fix(
            identifier="WAVEY",
            state="WA",
            latitude=47.5,
            longitude=-122.5,
        ),
    }

    yield

    # Clean up
    main.AIRPORTS = {}
    main.NAVAIDS = {}
    main.FIXES = {}


client = TestClient(main.app)


# =============================================================================
# Health endpoint
# =============================================================================

class TestHealth:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_counts(self):
        response = client.get("/health")
        data = response.json()
        assert data["navaid_count"] == 2
        assert data["fix_count"] == 2
        assert data["airport_count"] == 3  # SEA, KSEA, PDX


# =============================================================================
# Airport endpoints
# =============================================================================

class TestAirports:
    def test_get_airport_by_faa_lid(self):
        response = client.get("/airports/SEA")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SEA"
        assert data["icao"] == "KSEA"
        assert data["name"] == "SEATTLE-TACOMA INTL"
        assert data["city"] == "SEATTLE"
        assert data["state"] == "WA"
        assert data["type"] == "AIRPORT"
        assert data["latitude"] == 47.449
        assert data["longitude"] == -122.309

    def test_get_airport_by_icao(self):
        response = client.get("/airports/KSEA")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SEA"
        assert data["icao"] == "KSEA"

    def test_get_airport_case_insensitive(self):
        response = client.get("/airports/sea")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SEA"

    def test_get_airport_not_found(self):
        response = client.get("/airports/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_airport_radial_distance(self):
        response = client.get("/airports/SEA/90/10")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "SEA"
        assert data["type"] == "airport"
        assert data["radial"] == 90
        assert data["distance_nm"] == 10
        assert "latitude" in data
        assert "longitude" in data

    def test_get_airport_radial_distance_not_found(self):
        response = client.get("/airports/INVALID/90/10")
        assert response.status_code == 404

    def test_get_airport_radial_zero_distance(self):
        response = client.get("/airports/SEA/0/0")
        assert response.status_code == 200
        data = response.json()
        assert data["distance_nm"] == 0

    def test_get_airport_radial_360(self):
        response = client.get("/airports/SEA/360/5")
        assert response.status_code == 200


# =============================================================================
# NAVAID endpoints
# =============================================================================

class TestNavaids:
    def test_get_navaid(self):
        response = client.get("/navaids/SEA")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SEA"
        assert data["name"] == "SEATTLE"
        assert data["type"] == "VORTAC"
        assert data["latitude"] == 47.435278
        assert data["longitude"] == -122.309722

    def test_get_navaid_case_insensitive(self):
        response = client.get("/navaids/sea")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SEA"

    def test_get_navaid_not_found(self):
        response = client.get("/navaids/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_navaid_radial_distance(self):
        response = client.get("/navaids/SEA/270/5")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "SEA"
        assert data["type"] == "navaid"
        assert data["radial"] == 270
        assert data["distance_nm"] == 5
        assert "latitude" in data
        assert "longitude" in data

    def test_get_navaid_radial_distance_not_found(self):
        response = client.get("/navaids/INVALID/270/5")
        assert response.status_code == 404

    def test_get_navaid_icao_fix_notation(self):
        """Test ICAO fix notation: SEA270005 = SEA radial 270, 5nm."""
        response = client.get("/navaids/SEA270005")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "SEA"
        assert data["radial"] == 270
        assert data["distance_nm"] == 5

    def test_get_navaid_icao_fix_notation_leading_zeros(self):
        """Test ICAO notation with leading zeros: SEA090010 = radial 090, 10nm."""
        response = client.get("/navaids/SEA090010")
        assert response.status_code == 200
        data = response.json()
        assert data["radial"] == 90
        assert data["distance_nm"] == 10

    def test_get_navaid_icao_fix_notation_not_found(self):
        response = client.get("/navaids/XXX270005")
        assert response.status_code == 404


# =============================================================================
# Waypoint endpoints
# =============================================================================

class TestWaypoints:
    def test_get_waypoint(self):
        response = client.get("/waypoints/BANGR")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "BANGR"
        assert data["type"] == "FIX"
        assert data["state"] == "WA"
        assert data["latitude"] == 47.4625
        assert data["longitude"] == -122.928611

    def test_get_waypoint_case_insensitive(self):
        response = client.get("/waypoints/bangr")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "BANGR"

    def test_get_waypoint_not_found(self):
        response = client.get("/waypoints/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_waypoint_radial_distance(self):
        response = client.get("/waypoints/BANGR/180/15")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "BANGR"
        assert data["type"] == "waypoint"
        assert data["radial"] == 180
        assert data["distance_nm"] == 15

    def test_get_waypoint_radial_distance_not_found(self):
        response = client.get("/waypoints/INVALID/180/15")
        assert response.status_code == 404


# =============================================================================
# Points endpoints (search all types)
# =============================================================================

class TestPoints:
    def test_get_point_finds_airport(self):
        """Points endpoint should find airports first."""
        response = client.get("/points/PDX")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "PDX"
        assert data["type"] == "AIRPORT"

    def test_get_point_finds_navaid(self):
        """Points endpoint should find navaids."""
        response = client.get("/points/BTG")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "BTG"
        assert data["type"] == "VOR/DME"

    def test_get_point_finds_waypoint(self):
        """Points endpoint should find waypoints."""
        response = client.get("/points/BANGR")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "BANGR"
        assert data["type"] == "FIX"

    def test_get_point_priority_airport_over_navaid(self):
        """When ID exists in both airports and navaids, airport wins."""
        # SEA exists in both AIRPORTS and NAVAIDS
        response = client.get("/points/SEA")
        assert response.status_code == 200
        data = response.json()
        # Should return airport data (has icao field)
        assert "icao" in data
        assert data["type"] == "AIRPORT"

    def test_get_point_case_insensitive(self):
        response = client.get("/points/bangr")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "BANGR"

    def test_get_point_not_found(self):
        response = client.get("/points/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_point_icao_fix_notation(self):
        """Points endpoint should support ICAO fix notation."""
        response = client.get("/points/SEA270005")
        assert response.status_code == 200
        data = response.json()
        assert data["radial"] == 270
        assert data["distance_nm"] == 5

    def test_get_point_radial_distance_from_airport(self):
        response = client.get("/points/PDX/45/20")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "PDX"
        assert data["type"] == "airport"
        assert data["radial"] == 45
        assert data["distance_nm"] == 20

    def test_get_point_radial_distance_from_navaid(self):
        response = client.get("/points/BTG/180/10")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "BTG"
        assert data["type"] == "navaid"

    def test_get_point_radial_distance_from_waypoint(self):
        response = client.get("/points/WAVEY/90/5")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "WAVEY"
        assert data["type"] == "waypoint"

    def test_get_point_radial_distance_not_found(self):
        response = client.get("/points/INVALID/90/5")
        assert response.status_code == 404


# =============================================================================
# Radial/Distance validation
# =============================================================================

class TestRadialDistanceValidation:
    def test_radial_negative_invalid(self):
        response = client.get("/navaids/SEA/-1/5")
        assert response.status_code == 400
        assert "radial" in response.json()["detail"].lower()

    def test_radial_over_360_invalid(self):
        response = client.get("/navaids/SEA/361/5")
        assert response.status_code == 400
        assert "radial" in response.json()["detail"].lower()

    def test_distance_negative_invalid(self):
        response = client.get("/navaids/SEA/90/-5")
        assert response.status_code == 400
        assert "distance" in response.json()["detail"].lower()

    def test_radial_boundary_zero(self):
        response = client.get("/navaids/SEA/0/5")
        assert response.status_code == 200

    def test_radial_boundary_360(self):
        response = client.get("/navaids/SEA/360/5")
        assert response.status_code == 200

    def test_distance_zero_valid(self):
        response = client.get("/navaids/SEA/90/0")
        assert response.status_code == 200

    def test_distance_decimal_valid(self):
        response = client.get("/navaids/SEA/90/5.5")
        assert response.status_code == 200
        data = response.json()
        assert data["distance_nm"] == 5.5

    def test_validation_on_airports(self):
        response = client.get("/airports/SEA/400/5")
        assert response.status_code == 400

    def test_validation_on_waypoints(self):
        response = client.get("/waypoints/BANGR/400/5")
        assert response.status_code == 400

    def test_validation_on_points(self):
        response = client.get("/points/SEA/400/5")
        assert response.status_code == 400


# =============================================================================
# Destination calculation
# =============================================================================

class TestDestinationCalculation:
    def test_north_increases_latitude(self):
        """Moving north (0/360) should increase latitude."""
        response = client.get("/navaids/SEA/0/60")
        assert response.status_code == 200
        data = response.json()
        # 60nm north should increase lat by ~1 degree
        assert data["latitude"] > 47.435278

    def test_south_decreases_latitude(self):
        """Moving south (180) should decrease latitude."""
        response = client.get("/navaids/SEA/180/60")
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] < 47.435278

    def test_east_increases_longitude(self):
        """Moving east (90) should increase longitude (less negative)."""
        response = client.get("/navaids/SEA/90/60")
        assert response.status_code == 200
        data = response.json()
        assert data["longitude"] > -122.309722

    def test_west_decreases_longitude(self):
        """Moving west (270) should decrease longitude (more negative)."""
        response = client.get("/navaids/SEA/270/60")
        assert response.status_code == 200
        data = response.json()
        assert data["longitude"] < -122.309722

    def test_zero_distance_returns_same_coords(self):
        """Zero distance should return the reference point coords."""
        response = client.get("/navaids/SEA/90/0")
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 47.435278
        assert data["longitude"] == -122.309722
