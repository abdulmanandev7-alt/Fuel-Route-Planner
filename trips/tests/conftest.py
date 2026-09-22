import json

import pytest
from django.core.cache import cache
from django.test import override_settings

from trips.services import locations

MAJOR_CITIES = {
    "new york|NY": (40.712728, -74.006015),
    "los angeles|CA": (34.053691, -118.242766),
    "washington|DC": (38.895098, -77.036385),
    "springfield|MO": (37.208957, -93.292299),
    "springfield|IL": (39.799017, -89.643957),
}


@pytest.fixture(autouse=True)
def isolated_caches(tmp_path):
    """Fresh Django cache and a small, known gazetteer for every test."""
    path = tmp_path / "major_cities.json"
    path.write_text(json.dumps({key: {"lat": lat, "lon": lon} for key, (lat, lon) in MAJOR_CITIES.items()}))
    cache.clear()
    locations._major_cities.cache_clear()
    with override_settings(MAJOR_CITIES_FILE=path):
        yield
    cache.clear()
    locations._major_cities.cache_clear()
