from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import pairwise

from geo.distance import haversine_miles
from stations.index import IndexedStation, StationIndex

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class RouteStation:
    station: IndexedStation
    position_miles: float
    distance_from_route_miles: float
    latitude: float  # point on the route closest to the station, where its highway exit is
    longitude: float


def find_stations_along_route(
    points: Sequence[Point],
    total_miles: float,
    index: StationIndex,
    corridor_miles: float,
    sample_miles: float,
) -> list[RouteStation]:
    """Stations within the corridor, each with its closest position along the route, ordered by that position."""
    polyline_miles = sum(haversine_miles(*a, *b) for a, b in pairwise(points))
    scale = total_miles / polyline_miles if polyline_miles else 1.0

    closest: dict[int, RouteStation] = {}
    for latitude, longitude, position in _sample_points(points, sample_miles):
        for station, distance in index.within(latitude, longitude, corridor_miles):
            seen = closest.get(station.id)
            if seen is None or distance < seen.distance_from_route_miles:
                closest[station.id] = RouteStation(station, position * scale, distance, latitude, longitude)

    return sorted(closest.values(), key=lambda entry: entry.position_miles)


def _sample_points(points: Sequence[Point], step_miles: float) -> Iterator[tuple[float, float, float]]:
    """Yield (latitude, longitude, distance from start) at regular intervals along the polyline."""
    position = 0.0
    next_sample = 0.0
    for (lat1, lon1), (lat2, lon2) in pairwise(points):
        segment_miles = haversine_miles(lat1, lon1, lat2, lon2)
        if segment_miles == 0:
            continue
        segment_end = position + segment_miles
        while next_sample <= segment_end:
            fraction = (next_sample - position) / segment_miles
            yield lat1 + (lat2 - lat1) * fraction, lon1 + (lon2 - lon1) * fraction, next_sample
            next_sample += step_miles
        position = segment_end

    if points:
        yield points[-1][0], points[-1][1], position
