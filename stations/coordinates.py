import json
from pathlib import Path

type Coordinates = tuple[float, float]


def city_key(city: str, state: str) -> str:
    return f"{city.strip().lower()}|{state.strip().upper()}"


def load_city_coordinates(path: Path) -> dict[str, Coordinates | None]:
    """Read the geocoding cache: city key -> (latitude, longitude), or None when a lookup found nothing."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return {key: (value["lat"], value["lon"]) if value else None for key, value in raw.items()}


def save_city_coordinates(path: Path, coordinates: dict[str, Coordinates | None]) -> None:
    serializable = {
        key: {"lat": value[0], "lon": value[1]} if value else None for key, value in sorted(coordinates.items())
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=1)
