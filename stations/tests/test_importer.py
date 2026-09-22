from decimal import Decimal

import pytest

from stations.coordinates import save_city_coordinates
from stations.importer import import_stations, read_station_rows
from stations.models import FuelStation

CSV_CONTENT = """OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.00733333
105,TA SAGINAW,"I-75, EXIT 144-B",Bridgeport,MI,260,3.269
105,TA SAGINAW,"I-75, EXIT 144-B",Bridgeport,MI,260,3.199
105,TA SAGINAW,"I-75, EXIT 144-B",Bridgeport,MI,260,3.429
128,THE EFFINGHAM CHROME SHOP,"I-57 & I-70, EXIT 159",Effingham                     ,IL,510,3.399
900,FLYING J CALGARY,HWY 2,Calgary,AB,100,3.100
"""


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_read_station_rows_dedupes_filters_and_strips(csv_path):
    rows, skipped = read_station_rows(csv_path)

    assert skipped == 1
    assert [row.opis_id for row in rows] == [7, 105, 128]
    assert rows[1].retail_price == Decimal("3.199")
    assert rows[2].city == "Effingham"


@pytest.mark.django_db
def test_import_stations_attaches_coordinates_and_upserts(csv_path, tmp_path):
    coordinates_path = tmp_path / "cities.json"
    save_city_coordinates(coordinates_path, {"big cabin|OK": (36.5379, -95.2214), "effingham|IL": None})

    summary = import_stations(csv_path, coordinates_path)

    assert (summary.imported, summary.skipped_non_us, summary.without_coordinates) == (3, 1, 2)
    big_cabin = FuelStation.objects.get(opis_id=7)
    assert (big_cabin.latitude, big_cabin.longitude) == (36.5379, -95.2214)
    assert FuelStation.objects.get(opis_id=105).latitude is None

    csv_path.write_text(CSV_CONTENT.replace("3.00733333", "2.999"), encoding="utf-8")
    import_stations(csv_path, coordinates_path)

    assert FuelStation.objects.count() == 3
    assert FuelStation.objects.get(opis_id=7).retail_price == Decimal("2.999")
