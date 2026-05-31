import pytest
from fastapi.testclient import TestClient

from navaid_api import main
from navaid_api.parser import Airport, Navaid, Fix


@pytest.fixture(autouse=True)
def setup_test_data():
    """Set up synthetic test data before each test.

    All identifiers are deliberately synthetic so that fixtures do not drift
    when the FAA decommissions or reclassifies a real-world facility.
    """
    main.AIRPORTS = {
        "XYZ": Airport(
            identifier="XYZ",
            icao="KXYZ",
            name="SYNTHETIC INTL",
            city="SYNTHETICVILLE",
            state="ZZ",
            type="AIRPORT",
            latitude=47.449,
            longitude=-122.309,
        ),
        "KXYZ": Airport(
            identifier="XYZ",
            icao="KXYZ",
            name="SYNTHETIC INTL",
            city="SYNTHETICVILLE",
            state="ZZ",
            type="AIRPORT",
            latitude=47.449,
            longitude=-122.309,
        ),
        "ABC": Airport(
            identifier="ABC",
            icao="KABC",
            name="SECOND SYNTHETIC",
            city="OTHERTOWN",
            state="ZZ",
            type="AIRPORT",
            latitude=45.588,
            longitude=-122.598,
        ),
    }

    main.NAVAIDS = {
        "XYZ": Navaid(
            identifier="XYZ",
            name="SYNTHETIC NAVAID",
            type="VORTAC",
            latitude=47.435278,
            longitude=-122.309722,
        ),
        "DEF": Navaid(
            identifier="DEF",
            name="SECOND SYNTHETIC NAVAID",
            type="VOR/DME",
            latitude=45.815,
            longitude=-122.563,
        ),
    }

    main.FIXES = {
        "SYNTH": Fix(
            identifier="SYNTH",
            state="ZZ",
            latitude=47.4625,
            longitude=-122.928611,
        ),
        "THETA": Fix(
            identifier="THETA",
            state="ZZ",
            latitude=47.5,
            longitude=-122.5,
        ),
    }

    main.EFFECTIVE_DATE = "03/19/2026"

    yield

    # Clean up
    main.AIRPORTS = {}
    main.NAVAIDS = {}
    main.FIXES = {}
    main.EFFECTIVE_DATE = None


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
        assert data["airport_count"] == 3  # XYZ, KXYZ, ABC

    def test_health_returns_effective_date(self):
        response = client.get("/health")
        data = response.json()
        assert data["effective_date"] == "03/19/2026"

    def test_health_returns_null_effective_date_when_unset(self):
        main.EFFECTIVE_DATE = None
        response = client.get("/health")
        data = response.json()
        assert data["effective_date"] is None


# =============================================================================
# Airport endpoints
# =============================================================================

class TestAirports:
    def test_get_airport_by_faa_lid(self):
        response = client.get("/airports/XYZ")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "XYZ"
        assert data["icao"] == "KXYZ"
        assert data["name"] == "SYNTHETIC INTL"
        assert data["city"] == "SYNTHETICVILLE"
        assert data["state"] == "ZZ"
        assert data["type"] == "AIRPORT"
        assert data["latitude"] == 47.449
        assert data["longitude"] == -122.309

    def test_get_airport_by_icao(self):
        response = client.get("/airports/KXYZ")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "XYZ"
        assert data["icao"] == "KXYZ"

    def test_get_airport_case_insensitive(self):
        response = client.get("/airports/xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "XYZ"

    def test_get_airport_not_found(self):
        response = client.get("/airports/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_airport_radial_distance(self):
        response = client.get("/airports/XYZ/90/10")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "XYZ"
        assert data["type"] == "airport"
        assert data["radial"] == 90
        assert data["distance_nm"] == 10
        assert "latitude" in data
        assert "longitude" in data

    def test_get_airport_radial_distance_not_found(self):
        response = client.get("/airports/INVALID/90/10")
        assert response.status_code == 404

    def test_get_airport_radial_zero_distance(self):
        response = client.get("/airports/XYZ/0/0")
        assert response.status_code == 200
        data = response.json()
        assert data["distance_nm"] == 0

    def test_get_airport_radial_360(self):
        response = client.get("/airports/XYZ/360/5")
        assert response.status_code == 200


# =============================================================================
# NAVAID endpoints
# =============================================================================

class TestNavaids:
    def test_get_navaid(self):
        response = client.get("/navaids/XYZ")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "XYZ"
        assert data["name"] == "SYNTHETIC NAVAID"
        assert data["type"] == "VORTAC"
        assert data["latitude"] == 47.435278
        assert data["longitude"] == -122.309722

    def test_get_navaid_case_insensitive(self):
        response = client.get("/navaids/xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "XYZ"

    def test_get_navaid_not_found(self):
        response = client.get("/navaids/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_navaid_radial_distance(self):
        response = client.get("/navaids/XYZ/270/5")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "XYZ"
        assert data["type"] == "navaid"
        assert data["radial"] == 270
        assert data["distance_nm"] == 5
        assert "latitude" in data
        assert "longitude" in data

    def test_get_navaid_radial_distance_not_found(self):
        response = client.get("/navaids/INVALID/270/5")
        assert response.status_code == 404

    def test_get_navaid_icao_fix_notation(self):
        """Test ICAO fix notation: XYZ270005 = XYZ radial 270, 5nm."""
        response = client.get("/navaids/XYZ270005")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "XYZ"
        assert data["radial"] == 270
        assert data["distance_nm"] == 5

    def test_get_navaid_icao_fix_notation_leading_zeros(self):
        """Test ICAO notation with leading zeros: XYZ090010 = radial 090, 10nm."""
        response = client.get("/navaids/XYZ090010")
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
        response = client.get("/waypoints/SYNTH")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SYNTH"
        assert data["type"] == "FIX"
        assert data["state"] == "ZZ"
        assert data["latitude"] == 47.4625
        assert data["longitude"] == -122.928611

    def test_get_waypoint_case_insensitive(self):
        response = client.get("/waypoints/synth")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SYNTH"

    def test_get_waypoint_not_found(self):
        response = client.get("/waypoints/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_waypoint_radial_distance(self):
        response = client.get("/waypoints/SYNTH/180/15")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "SYNTH"
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
        response = client.get("/points/ABC")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "ABC"
        assert data["type"] == "AIRPORT"

    def test_get_point_finds_navaid(self):
        """Points endpoint should find navaids."""
        response = client.get("/points/DEF")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "DEF"
        assert data["type"] == "VOR/DME"

    def test_get_point_finds_waypoint(self):
        """Points endpoint should find waypoints."""
        response = client.get("/points/SYNTH")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SYNTH"
        assert data["type"] == "FIX"

    def test_get_point_priority_airport_over_navaid(self):
        """When ID exists in both airports and navaids, airport wins."""
        # XYZ exists in both AIRPORTS and NAVAIDS
        response = client.get("/points/XYZ")
        assert response.status_code == 200
        data = response.json()
        # Should return airport data (has icao field)
        assert "icao" in data
        assert data["type"] == "AIRPORT"

    def test_get_point_case_insensitive(self):
        response = client.get("/points/synth")
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "SYNTH"

    def test_get_point_not_found(self):
        response = client.get("/points/INVALID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_point_icao_fix_notation(self):
        """Points endpoint should support ICAO fix notation."""
        response = client.get("/points/XYZ270005")
        assert response.status_code == 200
        data = response.json()
        assert data["radial"] == 270
        assert data["distance_nm"] == 5

    def test_get_point_radial_distance_from_airport(self):
        response = client.get("/points/ABC/45/20")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "ABC"
        assert data["type"] == "airport"
        assert data["radial"] == 45
        assert data["distance_nm"] == 20

    def test_get_point_radial_distance_from_navaid(self):
        response = client.get("/points/DEF/180/10")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "DEF"
        assert data["type"] == "navaid"

    def test_get_point_radial_distance_from_waypoint(self):
        response = client.get("/points/THETA/90/5")
        assert response.status_code == 200
        data = response.json()
        assert data["reference"] == "THETA"
        assert data["type"] == "waypoint"

    def test_get_point_radial_distance_not_found(self):
        response = client.get("/points/INVALID/90/5")
        assert response.status_code == 404


# =============================================================================
# Radial/Distance validation
# =============================================================================

class TestRadialDistanceValidation:
    def test_radial_negative_invalid(self):
        response = client.get("/navaids/XYZ/-1/5")
        assert response.status_code == 400
        assert "radial" in response.json()["detail"].lower()

    def test_radial_over_360_invalid(self):
        response = client.get("/navaids/XYZ/361/5")
        assert response.status_code == 400
        assert "radial" in response.json()["detail"].lower()

    def test_distance_negative_invalid(self):
        response = client.get("/navaids/XYZ/90/-5")
        assert response.status_code == 400
        assert "distance" in response.json()["detail"].lower()

    def test_radial_boundary_zero(self):
        response = client.get("/navaids/XYZ/0/5")
        assert response.status_code == 200

    def test_radial_boundary_360(self):
        response = client.get("/navaids/XYZ/360/5")
        assert response.status_code == 200

    def test_distance_zero_valid(self):
        response = client.get("/navaids/XYZ/90/0")
        assert response.status_code == 200

    def test_distance_decimal_valid(self):
        response = client.get("/navaids/XYZ/90/5.5")
        assert response.status_code == 200
        data = response.json()
        assert data["distance_nm"] == 5.5

    def test_validation_on_airports(self):
        response = client.get("/airports/XYZ/400/5")
        assert response.status_code == 400

    def test_validation_on_waypoints(self):
        response = client.get("/waypoints/SYNTH/400/5")
        assert response.status_code == 400

    def test_validation_on_points(self):
        response = client.get("/points/XYZ/400/5")
        assert response.status_code == 400


# =============================================================================
# Destination calculation
# =============================================================================

class TestDestinationCalculation:
    def test_north_increases_latitude(self):
        """Moving north (0/360) should increase latitude."""
        response = client.get("/navaids/XYZ/0/60")
        assert response.status_code == 200
        data = response.json()
        # 60nm north should increase lat by ~1 degree
        assert data["latitude"] > 47.435278

    def test_south_decreases_latitude(self):
        """Moving south (180) should decrease latitude."""
        response = client.get("/navaids/XYZ/180/60")
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] < 47.435278

    def test_east_increases_longitude(self):
        """Moving east (90) should increase longitude (less negative)."""
        response = client.get("/navaids/XYZ/90/60")
        assert response.status_code == 200
        data = response.json()
        assert data["longitude"] > -122.309722

    def test_west_decreases_longitude(self):
        """Moving west (270) should decrease longitude (more negative)."""
        response = client.get("/navaids/XYZ/270/60")
        assert response.status_code == 200
        data = response.json()
        assert data["longitude"] < -122.309722

    def test_zero_distance_returns_same_coords(self):
        """Zero distance should return the reference point coords."""
        response = client.get("/navaids/XYZ/90/0")
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 47.435278
        assert data["longitude"] == -122.309722


class TestIdentifierValidation:
    """SEC NA-002: path identifiers are length- and charset-constrained.

    Every identifier route is bound to ``IdentifierParam`` (max_length=16,
    pattern ^[A-Za-z0-9]+$) in main.py, so malformed identifiers are rejected
    with 422 at the framework boundary before being uppercased and used as a
    dict key. These tests guard that mechanism: reverting any handler to a bare
    ``str`` makes the rejected cases reach the handler and return 404/200
    instead of 422, turning the relevant test red.
    """

    # Every route that accepts an identifier, in both single and radial forms.
    SINGLE_ROUTES = ("/airports/{id}", "/waypoints/{id}", "/navaids/{id}", "/points/{id}")
    RADIAL_ROUTES = (
        "/airports/{id}/90/5",
        "/waypoints/{id}/90/5",
        "/navaids/{id}/90/5",
        "/points/{id}/90/5",
    )

    def test_overlong_identifier_rejected_on_every_single_route(self):
        too_long = "A" * 17
        for route in self.SINGLE_ROUTES:
            response = client.get(route.format(id=too_long))
            assert response.status_code == 422, f"{route} accepted a 17-char identifier"

    def test_overlong_identifier_rejected_on_every_radial_route(self):
        too_long = "A" * 17
        for route in self.RADIAL_ROUTES:
            response = client.get(route.format(id=too_long))
            assert response.status_code == 422, f"{route} accepted a 17-char identifier"

    def test_non_alphanumeric_identifier_rejected_on_every_single_route(self):
        for bad in ("A-B", "A.B", "A_B", "A B"):
            for route in self.SINGLE_ROUTES:
                response = client.get(route.format(id=bad))
                assert response.status_code == 422, f"{route} accepted {bad!r}"

    def test_non_alphanumeric_identifier_rejected_on_every_radial_route(self):
        for bad in ("A-B", "A.B", "A_B"):
            for route in self.RADIAL_ROUTES:
                response = client.get(route.format(id=bad))
                assert response.status_code == 422, f"{route} accepted {bad!r}"

    def test_max_length_boundary_is_accepted(self):
        """A 16-char alphanumeric identifier passes validation (reaches the
        handler and 404s because it is not in the synthetic dataset) — proving
        the limit is 16, not shorter."""
        sixteen = "A" * 16
        for route in self.SINGLE_ROUTES:
            response = client.get(route.format(id=sixteen))
            assert response.status_code == 404, f"{route} rejected a valid 16-char identifier"

    def test_valid_identifiers_still_resolve(self):
        """Lowercase and combined radial notation remain valid under the
        constraint (regression guard for the charset/length allowing them)."""
        assert client.get("/airports/xyz").status_code == 200
        assert client.get("/navaids/XYZ270005").status_code == 200
