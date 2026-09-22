import pytest
import requests

from integrations.exceptions import NoRouteError, UpstreamServiceError
from integrations.http import external_calls_made, reset_external_calls
from integrations.nominatim import NominatimClient
from integrations.osrm import OsrmClient


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"status {self.status}")


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture(autouse=True)
def reset_counter():
    reset_external_calls()


def test_nominatim_search_parses_first_result_and_counts_call():
    session = FakeSession(
        FakeResponse(
            [{"lat": "41.88", "lon": "-87.63", "display_name": "Chicago, Illinois", "address": {"state": "Illinois"}}]
        )
    )
    client = NominatimClient("https://geo.example", "agent", timeout=5, session=session)

    result = client.search_city("Chicago", "Illinois")

    assert (result.latitude, result.longitude, result.state) == (41.88, -87.63, "Illinois")
    url, params = session.calls[0]
    assert url == "https://geo.example/search"
    assert params == {
        "city": "Chicago",
        "state": "Illinois",
        "country": "US",
        "featureType": "settlement",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    assert external_calls_made() == 1


def test_nominatim_free_text_reports_the_kind_of_place():
    payload = [{"lat": "47.5", "lon": "-120.5", "display_name": "Washington, United States", "addresstype": "state"}]
    session = FakeSession(FakeResponse(payload))
    client = NominatimClient("https://geo.example", "agent", timeout=5, session=session)

    result = client.search("Washington")

    assert result.kind == "state"
    assert result.is_administrative_area
    assert "featureType" not in session.calls[0][1]


def test_nominatim_returns_none_when_nothing_matches():
    client = NominatimClient("https://geo.example", "agent", timeout=5, session=FakeSession(FakeResponse([])))

    assert client.search("Atlantis") is None


def test_nominatim_wraps_network_errors():
    client = NominatimClient("https://geo.example", "agent", timeout=5, session=FakeSession(requests.ConnectionError()))

    with pytest.raises(UpstreamServiceError):
        client.search("Chicago")


def test_osrm_route_uses_lon_lat_order_and_full_geometry():
    payload = {"code": "Ok", "routes": [{"distance": 1000.0, "duration": 60.0, "geometry": "abc"}]}
    session = FakeSession(FakeResponse(payload))
    client = OsrmClient("https://osrm.example", "agent", timeout=5, session=session)

    route = client.route((41.88, -87.63), (34.05, -118.24))

    assert (route.distance_meters, route.duration_seconds, route.geometry) == (1000.0, 60.0, "abc")
    url, params = session.calls[0]
    assert url == "https://osrm.example/route/v1/driving/-87.63,41.88;-118.24,34.05"
    assert params == {"overview": "full", "geometries": "polyline", "steps": "false"}


def test_osrm_no_route_raises_dedicated_error():
    session = FakeSession(FakeResponse({"code": "NoRoute", "message": "Impossible route."}, status=400))
    client = OsrmClient("https://osrm.example", "agent", timeout=5, session=session)

    with pytest.raises(NoRouteError):
        client.route((21.3, -157.8), (34.05, -118.24))


def test_osrm_unexpected_payload_raises_upstream_error():
    session = FakeSession(FakeResponse({"code": "InvalidQuery"}, status=400))
    client = OsrmClient("https://osrm.example", "agent", timeout=5, session=session)

    with pytest.raises(UpstreamServiceError):
        client.route((41.88, -87.63), (34.05, -118.24))
