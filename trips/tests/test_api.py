import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from geo.distance import haversine_miles
from geo.polyline import encode
from integrations.exceptions import NoRouteError, UpstreamServiceError
from integrations.http import record_external_call
from integrations.osrm import OsrmRoute
from stations.models import FuelStation
from trips.services import routing

# Straight route east along latitude 35 from -100 to -89, roughly 625 miles.
ROUTE_POINTS = [(35.0, -100.0 + step * 0.5) for step in range(23)]
ROUTE_MILES = sum(haversine_miles(*ROUTE_POINTS[i], *ROUTE_POINTS[i + 1]) for i in range(len(ROUTE_POINTS) - 1))
STATIONS = [
    (1, "Cheap Stop", -99.0, 2.90),
    (2, "Pricey Stop", -96.0, 3.90),
    (3, "Mid Stop", -93.0, 3.20),
]


class FakeRouter:
    def __init__(self, error=None):
        self.error = error

    def route(self, start, finish):
        record_external_call()
        if self.error:
            raise self.error
        return OsrmRoute(ROUTE_MILES / 0.000621371, 36000, encode(ROUTE_POINTS))


@pytest.fixture
def router(monkeypatch):
    fake = FakeRouter()
    monkeypatch.setattr(routing, "_router", lambda: fake)
    return fake


@pytest.fixture
def stations(db):
    for opis_id, name, longitude, price in STATIONS:
        FuelStation.objects.create(
            opis_id=opis_id,
            name=name,
            address="I-40",
            city=f"City {opis_id}",
            state="OK",
            rack_id=1,
            retail_price=str(price),
            latitude=35.0,
            longitude=longitude,
        )


@pytest.fixture
def client():
    return APIClient()


@override_settings(EXTRA_COST_TOLERANCE_USD=0)
def test_plans_route_with_cost_optimal_stops(client, router, stations):
    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    assert response.status_code == 200
    body = response.json()
    assert body["distance_miles"] == pytest.approx(ROUTE_MILES, abs=0.1)
    assert body["stations_considered"] == 3
    # The tank cap limits how much the cheapest station can supply; the rest comes from the next cheapest.
    assert [stop["station"]["name"] for stop in body["fuel_stops"]] == ["Cheap Stop", "Mid Stop"]
    cheap, mid = body["fuel_stops"]
    assert [cheap["stop_number"], mid["stop_number"]] == [1, 2]
    assert cheap["gallons"] == pytest.approx(cheap["distance_from_start_miles"] / 10, abs=0.1)
    assert cheap["fuel_after_gallons"] == 50.0
    assert cheap["location"]["latitude"] == pytest.approx(35.0)
    assert cheap["location"]["longitude"] == pytest.approx(-99.0, abs=0.02)
    assert body["total_fuel_gallons"] == pytest.approx(body["distance_miles"] / 10 - 50, abs=0.1)
    assert body["total_fuel_cost"] == pytest.approx(cheap["gallons"] * 2.90 + mid["gallons"] * 3.20, abs=0.05)
    assert body["fuel_used_gallons"] == pytest.approx(body["distance_miles"] / 10, abs=0.01)
    assert body["vehicle"] == {"range_miles": 500.0, "mpg": 10.0, "tank_gallons": 50.0, "starting_fuel_gallons": 50.0}
    assert body["meta"]["external_api_calls"] == 1
    assert body["route"]["geometry_format"] == "polyline5"
    assert body["map_url"].startswith("http://testserver/?start=")


def test_small_stop_is_folded_when_within_tolerance(client, router, stations):
    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    # The 5.65 gal top-up at the cheap station costs $1.70 more at the mid station, under the $2 tolerance.
    assert [stop["station"]["name"] for stop in response.json()["fuel_stops"]] == ["Mid Stop"]


def test_repeated_request_is_served_from_cache(client, router, stations):
    client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})
    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    assert response.json()["meta"]["external_api_calls"] == 0


def test_post_with_json_body(client, router, stations):
    response = client.post("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"}, format="json")

    assert response.status_code == 200
    assert response.json()["fuel_stops"]


def test_missing_parameter_returns_400(client):
    response = client.get("/api/route/", {"start": "35.0,-100.0"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert "finish" in response.json()["error"]["details"]


def test_other_api_errors_share_the_error_shape(client):
    response = client.put("/api/route/", {"start": "a", "finish": "b"}, format="json")

    assert response.status_code == 405
    assert response.json() == {"error": {"code": "method_not_allowed", "message": 'Method "PUT" not allowed.'}}


def test_trip_with_no_reachable_station_returns_422(client, router, db):
    FuelStation.objects.create(
        opis_id=99,
        name="Far Away",
        address="I-95",
        city="Elsewhere",
        state="FL",
        rack_id=1,
        retail_price="3.0",
        latitude=28.0,
        longitude=-81.0,
    )

    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "trip_not_feasible"


def test_empty_station_table_returns_503(client, router, db):
    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "stations_not_loaded"
    assert "import_stations" in response.json()["error"]["message"]


def test_no_route_returns_422(client, router, stations):
    router.error = NoRouteError("No driveable route found between the given locations")

    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "21.3,-157.8"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "route_not_found"


def test_upstream_failure_returns_503(client, router, stations):
    router.error = UpstreamServiceError("Routing service is unavailable")

    response = client.get("/api/route/", {"start": "35.0,-100.0", "finish": "35.0,-89.0"})

    assert response.status_code == 503
    assert response.json()["error"] == {"code": "upstream_unavailable", "message": "Routing service is unavailable"}


def test_map_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Fuel Route Planner" in response.content
    assert b"server.arcgisonline.com" in response.content
