import math
import threading
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Count, Max

from geo.distance import MILES_PER_DEGREE_LATITUDE, degrees_span
from stations.models import FuelStation

type IndexVersion = tuple[int, object]


@dataclass(frozen=True, slots=True)
class IndexedStation:
    id: int
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price: float
    latitude: float
    longitude: float


class StationIndex:
    """In-memory grid over station coordinates so radius queries touch only nearby cells."""

    def __init__(
        self, stations: Iterable[IndexedStation], cell_size_degrees: float = 0.25, version: IndexVersion | None = None
    ):
        self.cell_size = cell_size_degrees
        self.version = version
        self._cells: dict[tuple[int, int], list[IndexedStation]] = defaultdict(list)
        self.size = 0
        for station in stations:
            self._cells[self._cell(station.latitude, station.longitude)].append(station)
            self.size += 1

    def within(self, latitude: float, longitude: float, radius_miles: float) -> list[tuple[IndexedStation, float]]:
        """Stations within the radius of a point, paired with their distance in miles."""
        d_lat, d_lon = degrees_span(latitude, radius_miles)
        min_row, min_col = self._cell(latitude - d_lat, longitude - d_lon)
        max_row, max_col = self._cell(latitude + d_lat, longitude + d_lon)
        miles_per_degree_lon = MILES_PER_DEGREE_LATITUDE * math.cos(math.radians(latitude))
        radius_squared = radius_miles * radius_miles

        matches = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                for station in self._cells.get((row, col), ()):
                    dy = (station.latitude - latitude) * MILES_PER_DEGREE_LATITUDE
                    dx = (station.longitude - longitude) * miles_per_degree_lon
                    distance_squared = dx * dx + dy * dy
                    if distance_squared <= radius_squared:
                        matches.append((station, math.sqrt(distance_squared)))
        return matches

    def _cell(self, latitude: float, longitude: float) -> tuple[int, int]:
        return math.floor(latitude / self.cell_size), math.floor(longitude / self.cell_size)


_index: StationIndex | None = None
_index_lock = threading.Lock()


def get_station_index() -> StationIndex:
    """Process-wide index, rebuilt whenever the station table changes (new import or geocoding run)."""
    global _index
    version = _table_version()
    if _index is None or _index.version != version:
        with _index_lock:
            if _index is None or _index.version != version:
                _index = StationIndex(_load_indexed_stations(), version=version)
    return _index


def _table_version() -> IndexVersion:
    stats = FuelStation.objects.filter(latitude__isnull=False).aggregate(count=Count("id"), updated=Max("updated_at"))
    return stats["count"], stats["updated"]


def _load_indexed_stations() -> list[IndexedStation]:
    rows = (
        FuelStation.objects.filter(latitude__isnull=False, longitude__isnull=False)
        .values_list("id", "opis_id", "name", "address", "city", "state", "retail_price", "latitude", "longitude")
        .iterator()
    )
    return [
        IndexedStation(id, opis_id, name, address, city, state, float(price), latitude, longitude)
        for id, opis_id, name, address, city, state, price, latitude, longitude in rows
    ]
