import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from geo.us import US_STATES
from integrations.exceptions import UpstreamServiceError
from integrations.nominatim import GeocodeResult, NominatimClient
from stations.coordinates import city_key, load_city_coordinates, save_city_coordinates
from stations.models import FuelStation

SAVE_EVERY = 25


class Command(BaseCommand):
    help = "Resolve coordinates for station cities through Nominatim (rate limited to one request per second)."

    def add_arguments(self, parser):
        parser.add_argument("--coordinates", type=Path, default=settings.CITY_COORDINATES_FILE)
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between requests")
        parser.add_argument("--retry-failed", action="store_true", help="Retry cities that previously returned nothing")

    def handle(self, *args, **options):
        path: Path = options["coordinates"]
        coordinates = load_city_coordinates(path)
        client = NominatimClient(
            settings.NOMINATIM_BASE_URL, settings.NOMINATIM_USER_AGENT, settings.EXTERNAL_API_TIMEOUT_SECONDS
        )

        pending = self._pending_cities(coordinates, options["retry_failed"])
        self.stdout.write(f"{len(pending)} cities to geocode.")

        for number, (city, state) in enumerate(pending, start=1):
            result = self._lookup(client, city, state, options["delay"])
            coordinates[city_key(city, state)] = (result.latitude, result.longitude) if result else None
            if number % SAVE_EVERY == 0:
                save_city_coordinates(path, coordinates)
                self.stdout.write(f"{number}/{len(pending)} done")

        save_city_coordinates(path, coordinates)
        updated = self._apply(coordinates)
        self.stdout.write(self.style.SUCCESS(f"Updated coordinates for {updated} stations."))

    @staticmethod
    def _pending_cities(coordinates, retry_failed: bool) -> list[tuple[str, str]]:
        cities = (
            FuelStation.objects.filter(latitude__isnull=True)
            .order_by("state", "city")
            .values_list("city", "state")
            .distinct()
        )
        pending = []
        for city, state in cities:
            key = city_key(city, state)
            if key not in coordinates or (retry_failed and coordinates[key] is None):
                pending.append((city, state))
        return pending

    def _lookup(self, client: NominatimClient, city: str, state: str, delay: float) -> GeocodeResult | None:
        state_name = US_STATES[state]
        try:
            result = client.search_city(city, state_name)
            time.sleep(delay)
            if not _in_state(result, state_name):
                result = client.search(f"{city}, {state_name}", settlements_only=True)
                time.sleep(delay)
        except UpstreamServiceError as exc:
            self.stderr.write(f"{city}, {state}: {exc}")
            return None
        return result if _in_state(result, state_name) else None

    @staticmethod
    def _apply(coordinates) -> int:
        updated = 0
        for station in FuelStation.objects.filter(latitude__isnull=True).only("id", "city", "state"):
            found = coordinates.get(city_key(station.city, station.state))
            if found:
                station.latitude, station.longitude = found
                station.save(update_fields=["latitude", "longitude"])
                updated += 1
        return updated


def _in_state(result: GeocodeResult | None, state_name: str) -> bool:
    return result is not None and result.state == state_name
