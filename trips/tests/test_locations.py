import pytest

from integrations.http import external_calls_made, reset_external_calls
from integrations.nominatim import GeocodeResult
from stations.models import FuelStation
from trips.exceptions import LocationNotFound
from trips.services import locations
from trips.services.locations import resolve_location

DENVER = GeocodeResult(39.7392, -104.9903, "Denver, Colorado, United States", "Colorado", "city")


class FakeGeocoder:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def search(self, query, settlements_only=False):
        self.calls.append((query, settlements_only))
        return self.results.pop(0) if len(self.results) > 1 else (self.results[0] if self.results else None)


@pytest.fixture
def geocoder(monkeypatch):
    fake = FakeGeocoder(DENVER)
    monkeypatch.setattr(locations, "_geocoder", lambda: fake)
    return fake


def station(opis_id, city, state, latitude, longitude):
    return FuelStation.objects.create(
        opis_id=opis_id,
        name=f"Stop {opis_id}",
        address="I-44",
        city=city,
        state=state,
        rack_id=1,
        retail_price="3.0",
        latitude=latitude,
        longitude=longitude,
    )


def test_parses_raw_coordinates():
    location = resolve_location(" 41.8781, -87.6298 ")

    assert (location.latitude, location.longitude) == (41.8781, -87.6298)
    assert location.label == "41.87810, -87.62980"


def test_rejects_coordinates_outside_the_usa():
    with pytest.raises(LocationNotFound, match="outside the USA"):
        resolve_location("51.5, -0.12")


@pytest.mark.django_db
def test_major_city_resolves_with_or_without_state(geocoder):
    with_state = resolve_location("new york, ny")
    bare = resolve_location("New York")

    assert (with_state.latitude, with_state.longitude) == (40.712728, -74.006015)
    assert with_state.label == bare.label == "New York, New York, United States"
    assert geocoder.calls == []


@pytest.mark.django_db
def test_bare_ambiguous_major_city_takes_the_largest(geocoder):
    location = resolve_location("Springfield")

    assert location.label == "Springfield, Missouri, United States"
    assert resolve_location("Springfield, Illinois").label == "Springfield, Illinois, United States"


@pytest.mark.django_db
def test_known_station_city_resolves_without_external_call(geocoder):
    station(1, "Big Cabin", "OK", 36.54, -95.22)

    with_state = resolve_location("big cabin, Oklahoma, USA")
    bare = resolve_location("Big Cabin")

    assert (with_state.latitude, with_state.longitude) == (bare.latitude, bare.longitude) == (36.54, -95.22)
    assert with_state.label == "Big Cabin, Oklahoma, United States"
    assert geocoder.calls == []


@pytest.mark.django_db
def test_ambiguous_station_city_without_state_goes_to_the_geocoder(geocoder):
    station(1, "Jamestown", "NY", 42.1, -79.2)
    station(2, "Jamestown", "ND", 46.9, -98.7)

    location = resolve_location("Jamestown")

    assert location.label == "Denver, Colorado, United States"
    assert geocoder.calls == [("Jamestown", False)]


@pytest.mark.django_db
def test_unknown_place_uses_geocoder_and_cache(geocoder):
    reset_external_calls()

    first = resolve_location("Denver International Airport")
    second = resolve_location("denver international airport")

    assert first.label == "Denver, Colorado, United States"
    assert (second.latitude, second.longitude, second.label) == (first.latitude, first.longitude, first.label)
    assert geocoder.calls == [("Denver International Airport", False)]
    assert external_calls_made() == 0


@pytest.mark.django_db
def test_administrative_area_is_retried_as_a_settlement(monkeypatch):
    state = GeocodeResult(47.5, -120.5, "Washington, United States", "Washington", "state")
    city = GeocodeResult(
        38.895, -77.036, "Washington, District of Columbia, United States", "District of Columbia", "city"
    )
    fake = FakeGeocoder(state, city)
    monkeypatch.setattr(locations, "_geocoder", lambda: fake)

    location = resolve_location("Washington state capital")

    assert location.label == "Washington, District of Columbia, United States"
    assert fake.calls == [("Washington state capital", False), ("Washington state capital", True)]


@pytest.mark.django_db
def test_geocoder_miss_raises_location_not_found(geocoder):
    geocoder.results = []

    with pytest.raises(LocationNotFound, match="Could not find 'Atlantis'"):
        resolve_location("Atlantis")
