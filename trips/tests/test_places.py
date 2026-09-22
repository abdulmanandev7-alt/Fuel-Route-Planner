import pytest
from rest_framework.test import APIClient

from stations.models import FuelStation
from trips.services.locations import suggest_places

CITIES = [
    (1, "Chicago", "IL", 41.88, -87.63),
    (2, "CHICAGO", "IL", 41.88, -87.63),
    (3, "Chickasha", "OK", 35.05, -97.94),
    (4, "Chico", "CA", 39.73, -121.84),
    (5, "Springfield", "MO", 37.2, -93.3),
    (6, "Chillicothe", "OH", None, None),
]


@pytest.fixture
def cities(db):
    for opis_id, city, state, latitude, longitude in CITIES:
        FuelStation.objects.create(
            opis_id=opis_id,
            name=f"Stop {opis_id}",
            address="I-55",
            city=city,
            state=state,
            rack_id=1,
            retail_price="3.0",
            latitude=latitude,
            longitude=longitude,
        )


def test_major_cities_come_first_in_population_order(cities):
    labels = [place.label for place in suggest_places("new", limit=8)]

    assert labels == ["New York, NY"]
    assert [place.label for place in suggest_places("los", limit=8)] == ["Los Angeles, CA"]


def test_suggests_by_city_prefix_and_dedupes_case_variants(cities):
    labels = [place.label for place in suggest_places("chi", limit=8)]

    assert labels == ["Chicago, IL", "Chickasha, OK", "Chico, CA"]


def test_state_after_comma_narrows_by_code_or_name(cities):
    assert [place.label for place in suggest_places("chi, ok", limit=8)] == ["Chickasha, OK"]
    assert [place.label for place in suggest_places("chi, calif", limit=8)] == ["Chico, CA"]


def test_limit_and_blank_query(cities):
    assert len(suggest_places("chi", limit=1)) == 1
    assert suggest_places(" , il", limit=8) == []


def test_places_endpoint(cities):
    response = APIClient().get("/api/places/", {"q": "chic", "limit": 5})

    assert response.status_code == 200
    assert response.json()[0] == {
        "label": "Chicago, IL",
        "city": "Chicago",
        "state": "IL",
        "latitude": 41.88,
        "longitude": -87.63,
    }


def test_places_endpoint_requires_query(db):
    response = APIClient().get("/api/places/")

    assert response.status_code == 400
    assert "q" in response.json()["error"]["details"]
