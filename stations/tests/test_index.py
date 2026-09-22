import pytest

from stations.index import IndexedStation, StationIndex


def station(id: int, latitude: float, longitude: float, price: float = 3.0) -> IndexedStation:
    return IndexedStation(id, id, f"Station {id}", "I-40", "Town", "OK", price, latitude, longitude)


@pytest.fixture
def index():
    return StationIndex(
        [
            station(1, 35.0, -100.0),
            station(2, 35.03, -100.0),  # about 2 miles north
            station(3, 35.5, -100.0),  # about 35 miles north
            station(4, 35.0, -100.249),  # about 14 miles west, across a cell boundary
        ],
        cell_size_degrees=0.25,
    )


def test_within_returns_stations_inside_radius_with_distances(index):
    matches = {found.id: distance for found, distance in index.within(35.0, -100.0, 5.0)}

    assert set(matches) == {1, 2}
    assert matches[1] == pytest.approx(0.0)
    assert matches[2] == pytest.approx(2.07, abs=0.05)


def test_within_crosses_cell_boundaries(index):
    ids = {found.id for found, _ in index.within(35.0, -100.0, 15.0)}

    assert ids == {1, 2, 4}


def test_within_far_from_any_station(index):
    assert index.within(40.0, -90.0, 10.0) == []
    assert index.size == 4
