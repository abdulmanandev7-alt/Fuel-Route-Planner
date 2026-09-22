import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache

from geo.us import US_STATES, is_within_us, state_code
from integrations.nominatim import NominatimClient
from stations.coordinates import Coordinates, city_key, load_city_coordinates
from stations.models import FuelStation
from trips.exceptions import LocationNotFound

COORDINATES_PATTERN = re.compile(r"^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$")
CITY_STATE_PATTERN = re.compile(
    r"^([A-Za-z .'-]+?)\s*,\s*([A-Za-z .]+?)(?:\s*,\s*(?:USA|US|United States))?$", re.IGNORECASE
)
CITY_ONLY_PATTERN = re.compile(r"^([A-Za-z .'-]+?)(?:\s*,\s*(?:USA|US|United States))?$", re.IGNORECASE)
MC_PREFIX = re.compile(r"\bMc([a-z])")


@dataclass(frozen=True, slots=True)
class Location:
    query: str
    label: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class PlaceSuggestion:
    label: str
    city: str
    state: str
    latitude: float
    longitude: float


def resolve_location(query: str) -> Location:
    """Resolve user input to coordinates: raw "lat,lon", a city in the local gazetteer, or a Nominatim lookup."""
    query = query.strip()
    return _from_coordinates(query) or _from_gazetteer(query) or _from_geocoder(query)


def suggest_places(q: str, limit: int) -> list[PlaceSuggestion]:
    """Cities whose name starts with the text: the largest US cities first, then every station city."""
    city, _, state = q.partition(",")
    city, state = city.strip().lower(), state.strip()
    if not city:
        return []
    states = _states_matching(state) if state else None

    suggestions: dict[str, PlaceSuggestion] = {}
    for key, coordinates in _major_cities().items():
        name, _, code = key.partition("|")
        if name.startswith(city) and (states is None or code in states):
            suggestions[key] = _suggestion(name, code, coordinates)

    rows = FuelStation.objects.filter(latitude__isnull=False, city__istartswith=city)
    if states is not None:
        rows = rows.filter(state__in=states)
    for name, code, latitude, longitude in (
        rows.values_list("city", "state", "latitude", "longitude").order_by("city", "state").distinct()
    ):
        suggestions.setdefault(city_key(name, code), _suggestion(name, code, (latitude, longitude)))

    return list(suggestions.values())[:limit]


def _from_coordinates(query: str) -> Location | None:
    match = COORDINATES_PATTERN.match(query)
    if not match:
        return None
    latitude, longitude = float(match.group(1)), float(match.group(2))
    if not is_within_us(latitude, longitude):
        raise LocationNotFound(f"Coordinates {latitude}, {longitude} are outside the USA")
    return Location(query, f"{latitude:.5f}, {longitude:.5f}", latitude, longitude)


def _from_gazetteer(query: str) -> Location | None:
    """Match `City, ST`, `City, State` or a bare city name against the largest US cities and the station cities."""
    match = CITY_STATE_PATTERN.match(query)
    if match:
        state = state_code(match.group(2))
        return _known_city(query, match.group(1).strip(), state) if state else None
    match = CITY_ONLY_PATTERN.match(query)
    return _known_city(query, match.group(1).strip(), None) if match else None


def _known_city(query: str, city: str, state: str | None) -> Location | None:
    wanted = city.lower()
    for key, coordinates in _major_cities().items():
        name, _, code = key.partition("|")
        if name == wanted and state in (None, code):
            return _location(query, name, code, coordinates)

    rows = FuelStation.objects.filter(city__iexact=city, latitude__isnull=False)
    if state:
        rows = rows.filter(state=state)
    found = {
        city_key(name, code): (name, code, (latitude, longitude))
        for name, code, latitude, longitude in rows.values_list("city", "state", "latitude", "longitude").distinct()
    }
    if len(found) != 1:
        return None  # unknown, or ambiguous without a state: let the geocoder decide
    return _location(query, *next(iter(found.values())))


def _from_geocoder(query: str) -> Location:
    key = "geocode:" + hashlib.sha1(query.lower().encode()).hexdigest()
    result = cache.get(key)
    if result is None:
        result = _geocoder().search(query)
        if result is not None and result.is_administrative_area:
            result = _geocoder().search(query, settlements_only=True) or result
        if result is None:
            raise LocationNotFound(f"Could not find '{query}' in the USA")
        cache.set(key, result, settings.GEOCODE_CACHE_SECONDS)
    return Location(query, result.display_name, result.latitude, result.longitude)


def _location(query: str, name: str, code: str, coordinates: Coordinates) -> Location:
    return Location(query, f"{_display_city(name)}, {US_STATES[code]}, United States", *coordinates)


def _suggestion(name: str, code: str, coordinates: Coordinates) -> PlaceSuggestion:
    display = _display_city(name)
    return PlaceSuggestion(f"{display}, {code}", display, code, *coordinates)


def _display_city(name: str) -> str:
    if name == name.lower() or name == name.upper():
        name = name.title()
    return MC_PREFIX.sub(lambda match: "Mc" + match.group(1).upper(), name)


def _states_matching(prefix: str) -> list[str]:
    prefix = prefix.lower()
    return [
        code for code, name in US_STATES.items() if code.lower().startswith(prefix) or name.lower().startswith(prefix)
    ]


@lru_cache(maxsize=1)
def _major_cities() -> dict[str, Coordinates]:
    """The largest US cities in population order, so common trip endpoints resolve without any geocoding call."""
    return {key: value for key, value in load_city_coordinates(settings.MAJOR_CITIES_FILE).items() if value}


@lru_cache(maxsize=1)
def _geocoder() -> NominatimClient:
    return NominatimClient(
        settings.NOMINATIM_BASE_URL, settings.NOMINATIM_USER_AGENT, settings.EXTERNAL_API_TIMEOUT_SECONDS
    )
