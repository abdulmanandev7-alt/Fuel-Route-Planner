import pytest

from geo.distance import degrees_span, haversine_miles


def test_haversine_chicago_to_los_angeles():
    assert haversine_miles(41.8781, -87.6298, 34.0522, -118.2437) == pytest.approx(1745, abs=3)


def test_haversine_same_point_is_zero():
    assert haversine_miles(40.0, -100.0, 40.0, -100.0) == 0


def test_degrees_span_widens_longitude_away_from_equator():
    d_lat_equator, d_lon_equator = degrees_span(0.0, 69.0)
    d_lat_north, d_lon_north = degrees_span(60.0, 69.0)
    assert d_lat_equator == pytest.approx(1.0)
    assert d_lon_equator == pytest.approx(1.0)
    assert d_lat_north == pytest.approx(1.0)
    assert d_lon_north == pytest.approx(2.0, rel=1e-3)
