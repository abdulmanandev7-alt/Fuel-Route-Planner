import pytest

from geo.distance import haversine_miles
from stations.index import StationIndex
from trips.services.corridor import _sample_points, find_stations_along_route
from trips.tests.helpers import indexed_station

ROUTE = [(35.0, -100.0), (35.0, -99.5), (35.0, -99.0)]
ROUTE_MILES = haversine_miles(35.0, -100.0, 35.0, -99.0)


def test_sample_points_are_evenly_spaced_and_end_at_the_last_point():
    samples = list(_sample_points([(35.0, -100.0), (35.0, -99.9)], step_miles=1.0))
    positions = [position for _, _, position in samples]

    assert positions[:3] == [0.0, 1.0, 2.0]
    assert positions[-1] == pytest.approx(haversine_miles(35.0, -100.0, 35.0, -99.9))
    assert samples[-1][:2] == (35.0, -99.9)


def test_finds_stations_inside_corridor_with_position_along_route():
    index = StationIndex(
        [
            indexed_station(1, 3.0, latitude=35.03, longitude=-99.5),  # about 2 miles off the midpoint
            indexed_station(2, 3.0, latitude=35.3, longitude=-99.5),  # about 20 miles off
            indexed_station(3, 3.0, latitude=35.0, longitude=-99.0),  # at the finish
        ]
    )

    found = find_stations_along_route(ROUTE, ROUTE_MILES, index, corridor_miles=10, sample_miles=1)

    assert [entry.station.id for entry in found] == [1, 3]
    assert found[0].position_miles == pytest.approx(ROUTE_MILES / 2, abs=1)
    assert found[0].distance_from_route_miles == pytest.approx(2.07, abs=0.1)
    assert (found[0].latitude, found[0].longitude) == (pytest.approx(35.0), pytest.approx(-99.5, abs=0.02))
    assert found[1].position_miles == pytest.approx(ROUTE_MILES, abs=0.01)


def test_positions_are_scaled_to_the_reported_route_distance():
    index = StationIndex([indexed_station(1, 3.0, latitude=35.0, longitude=-99.0)])

    found = find_stations_along_route(ROUTE, ROUTE_MILES * 1.1, index, corridor_miles=5, sample_miles=1)

    assert found[0].position_miles == pytest.approx(ROUTE_MILES * 1.1, abs=0.01)
