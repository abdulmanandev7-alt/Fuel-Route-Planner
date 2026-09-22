import pytest

from trips.exceptions import TripNotFeasible
from trips.services.fuel_planner import Vehicle, plan_fuel_stops
from trips.tests.helpers import route_station

VEHICLE = Vehicle(range_miles=500, mpg=10)
FULL_TANK = VEHICLE.tank_gallons


def test_no_stops_when_trip_fits_in_a_full_tank():
    plan = plan_fuel_stops([route_station(1, 100, 3.0)], 300, VEHICLE, FULL_TANK)

    assert plan.stops == []
    assert plan.total_cost == 0
    assert plan.fuel_remaining_gallons == pytest.approx(20)


def test_buys_only_what_is_needed_at_the_cheapest_station():
    stations = [route_station(1, 100, 4.0), route_station(2, 300, 3.0), route_station(3, 450, 5.0)]

    plan = plan_fuel_stops(stations, 600, VEHICLE, FULL_TANK)

    assert [stop.station.id for stop in plan.stops] == [2]
    assert plan.stops[0].gallons == pytest.approx(10)
    assert plan.total_cost == pytest.approx(30)
    assert plan.fuel_remaining_gallons == pytest.approx(0)


def test_buys_just_enough_to_reach_a_cheaper_station():
    stations = [route_station(1, 100, 4.0), route_station(2, 550, 3.0)]

    plan = plan_fuel_stops(stations, 900, VEHICLE, FULL_TANK)

    assert [(stop.station.id, round(stop.gallons, 6)) for stop in plan.stops] == [(1, 5), (2, 35)]
    assert plan.total_cost == pytest.approx(5 * 4.0 + 35 * 3.0)
    assert plan.total_gallons == pytest.approx(40)


def test_fills_up_when_everything_ahead_is_more_expensive():
    stations = [route_station(1, 100, 3.0), route_station(2, 550, 4.0), route_station(3, 1000, 5.0)]

    plan = plan_fuel_stops(stations, 1200, VEHICLE, FULL_TANK)

    assert [(stop.station.id, round(stop.gallons, 6)) for stop in plan.stops] == [(1, 10), (2, 45), (3, 15)]
    assert plan.stops[0].fuel_after_gallons == pytest.approx(FULL_TANK)
    assert plan.total_cost == pytest.approx(10 * 3.0 + 45 * 4.0 + 15 * 5.0)


def test_equal_prices_defer_the_purchase():
    stations = [route_station(1, 100, 3.0), route_station(2, 400, 3.0)]

    plan = plan_fuel_stops(stations, 600, VEHICLE, FULL_TANK)

    assert [stop.station.id for stop in plan.stops] == [2]
    assert plan.stops[0].gallons == pytest.approx(10)


def test_respects_starting_fuel():
    plan = plan_fuel_stops([route_station(1, 50, 3.0)], 200, VEHICLE, starting_fuel_gallons=10)

    assert plan.stops[0].fuel_before_gallons == pytest.approx(5)
    assert plan.stops[0].gallons == pytest.approx(10)


def test_gap_longer_than_range_is_not_feasible():
    stations = [route_station(1, 100, 3.0), route_station(2, 700, 3.0)]

    with pytest.raises(TripNotFeasible, match="after Station 1"):
        plan_fuel_stops(stations, 1200, VEHICLE, FULL_TANK)


def test_no_station_reachable_from_start_is_not_feasible():
    with pytest.raises(TripNotFeasible, match="from the start"):
        plan_fuel_stops([route_station(1, 150, 3.0)], 400, VEHICLE, starting_fuel_gallons=10)


def test_small_top_up_is_folded_into_a_neighbouring_stop():
    # Strictly optimal: 10 gal at station 1, a 3 gal top-up at station 2, 7 gal at station 3.
    stations = [route_station(1, 100, 3.0), route_station(2, 130, 3.1), route_station(3, 400, 3.2)]

    strict = plan_fuel_stops(stations, 700, VEHICLE, FULL_TANK)
    practical = plan_fuel_stops(stations, 700, VEHICLE, FULL_TANK, extra_cost_tolerance=2.0)

    assert [(stop.station.id, round(stop.gallons, 6)) for stop in strict.stops] == [(1, 10), (2, 3), (3, 7)]
    assert [(stop.station.id, round(stop.gallons, 6)) for stop in practical.stops] == [(1, 10), (3, 10)]
    assert practical.total_cost - strict.total_cost == pytest.approx(0.3)


def test_merges_stop_once_the_extra_cost_budget_is_used():
    stations = [route_station(1, 100, 3.0), route_station(2, 130, 3.1), route_station(3, 400, 3.2)]

    plan = plan_fuel_stops(stations, 700, VEHICLE, FULL_TANK, extra_cost_tolerance=5.0)

    # With a $5 budget the whole trip is fuelled at station 3: $64 versus the $61.70 optimum.
    assert [(stop.station.id, round(stop.gallons, 6)) for stop in plan.stops] == [(3, 20)]
    assert plan.total_cost == pytest.approx(64.0)


def test_stops_are_kept_when_merging_would_overflow_or_run_dry():
    stations = [route_station(1, 100, 3.0), route_station(2, 590, 3.05)]

    plan = plan_fuel_stops(stations, 900, VEHICLE, FULL_TANK, extra_cost_tolerance=2.0)

    # Skipping station 1 would leave the tank 9 gallons short of station 2; moving 30 gallons earlier overflows it.
    assert [(stop.station.id, round(stop.gallons, 6)) for stop in plan.stops] == [(1, 10), (2, 30)]
