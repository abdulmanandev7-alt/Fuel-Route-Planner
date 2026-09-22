from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from stations.importer import import_stations


class Command(BaseCommand):
    help = "Load fuel stations from the OPIS price CSV, attaching cached city coordinates."

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=Path, default=settings.FUEL_PRICES_CSV)
        parser.add_argument("--coordinates", type=Path, default=settings.CITY_COORDINATES_FILE)

    def handle(self, *args, **options):
        summary = import_stations(options["csv"], options["coordinates"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {summary.imported} stations "
                f"({summary.skipped_non_us} non-US rows skipped, "
                f"{summary.without_coordinates} without coordinates)."
            )
        )
        if summary.without_coordinates:
            self.stdout.write("Run `manage.py geocode_stations` to resolve missing coordinates.")
