from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache

from geo.distance import MILES_PER_METER
from geo.polyline import decode
from integrations.osrm import OsrmClient
from trips.services.locations import Location


@dataclass(frozen=True, slots=True)
class Route:
    distance_miles: float
    duration_seconds: float
    geometry: str
    points: list[tuple[float, float]]


def fetch_route(start: Location, finish: Location) -> Route:
    key = f"route:{start.latitude:.5f},{start.longitude:.5f}:{finish.latitude:.5f},{finish.longitude:.5f}"
    osrm_route = cache.get(key)
    if osrm_route is None:
        osrm_route = _router().route((start.latitude, start.longitude), (finish.latitude, finish.longitude))
        cache.set(key, osrm_route, settings.ROUTE_CACHE_SECONDS)
    return Route(
        distance_miles=osrm_route.distance_meters * MILES_PER_METER,
        duration_seconds=osrm_route.duration_seconds,
        geometry=osrm_route.geometry,
        points=decode(osrm_route.geometry),
    )


@lru_cache(maxsize=1)
def _router() -> OsrmClient:
    return OsrmClient(settings.OSRM_BASE_URL, settings.NOMINATIM_USER_AGENT, settings.EXTERNAL_API_TIMEOUT_SECONDS)
