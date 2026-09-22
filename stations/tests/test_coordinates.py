from stations.coordinates import city_key, load_city_coordinates, save_city_coordinates


def test_city_key_normalises_case_and_whitespace():
    assert city_key("  Big Cabin ", "ok") == "big cabin|OK"


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "cities.json"
    save_city_coordinates(path, {"chicago|IL": (41.88, -87.63), "nowhere|ZZ": None})

    assert load_city_coordinates(path) == {"chicago|IL": (41.88, -87.63), "nowhere|ZZ": None}


def test_load_missing_file_returns_empty(tmp_path):
    assert load_city_coordinates(tmp_path / "missing.json") == {}
