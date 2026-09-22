import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from geo.us import US_STATES
from stations.coordinates import Coordinates, city_key, load_city_coordinates
from stations.models import FuelStation


@dataclass(slots=True)
class StationRow:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    rack_id: int
    retail_price: Decimal


@dataclass(slots=True)
class ImportSummary:
    imported: int
    skipped_non_us: int
    without_coordinates: int


def read_station_rows(csv_path: Path) -> tuple[list[StationRow], int]:
    """Parse the OPIS price file, keeping US stations only and the lowest price per station."""
    rows_by_id: dict[int, StationRow] = {}
    skipped = 0

    with csv_path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            state = raw["State"].strip().upper()
            if state not in US_STATES:
                skipped += 1
                continue
            row = StationRow(
                opis_id=int(raw["OPIS Truckstop ID"]),
                name=raw["Truckstop Name"].strip(),
                address=raw["Address"].strip(),
                city=raw["City"].strip(),
                state=state,
                rack_id=int(raw["Rack ID"]),
                retail_price=Decimal(raw["Retail Price"].strip()),
            )
            existing = rows_by_id.get(row.opis_id)
            if existing is None:
                rows_by_id[row.opis_id] = row
            elif row.retail_price < existing.retail_price:
                existing.retail_price = row.retail_price

    return list(rows_by_id.values()), skipped


def import_stations(csv_path: Path, coordinates_path: Path) -> ImportSummary:
    rows, skipped = read_station_rows(csv_path)
    coordinates = load_city_coordinates(coordinates_path)

    stations = [_build_station(row, coordinates.get(city_key(row.city, row.state))) for row in rows]
    FuelStation.objects.bulk_create(
        stations,
        update_conflicts=True,
        unique_fields=["opis_id"],
        update_fields=[
            "name",
            "address",
            "city",
            "state",
            "rack_id",
            "retail_price",
            "latitude",
            "longitude",
            "updated_at",
        ],
        batch_size=500,
    )
    return ImportSummary(
        imported=len(stations),
        skipped_non_us=skipped,
        without_coordinates=sum(1 for station in stations if station.latitude is None),
    )


def _build_station(row: StationRow, coordinates: Coordinates | None) -> FuelStation:
    latitude, longitude = coordinates if coordinates else (None, None)
    return FuelStation(
        opis_id=row.opis_id,
        name=row.name,
        address=row.address,
        city=row.city,
        state=row.state,
        rack_id=row.rack_id,
        retail_price=row.retail_price,
        latitude=latitude,
        longitude=longitude,
    )
