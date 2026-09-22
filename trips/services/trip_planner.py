from dataclasses import dataclass
from time import perf_counter

from django.conf import settings

from integrations.http import external_calls_made, reset_external_calls
from stations.index import get_station_index
from trips.exceptions import StationsNotLoaded
from trips.services.corridor import find_stations_along_route
from trips.services.fuel_planner import FuelPlan, Vehicle, plan_fuel_stops
from trips.services.locations import Location, resolve_location
from trips.services.routing import Route, fetch_route


@dataclass(frozen=True, slots=True)
class TripPlan:
    start: Location
    finish: Location
    route: Route
    vehicle: Vehicle
    starting_fuel_gallons: float
    fuel_plan: FuelPlan
    stations_considered: int
    external_api_calls: int
    processing_ms: float


def plan_trip(start: str, finish: str) -> TripPlan:
    started = perf_counter()
    reset_external_calls()
    index = get_station_index()
    if index.size == 0:
        raise StationsNotLoaded("No fuel stations are loaded; run `python manage.py import_stations` first")

    origin = resolve_location(start)
    destination = resolve_location(finish)
    route = fetch_route(origin, destination)

    vehicle = Vehicle(range_miles=settings.VEHICLE_RANGE_MILES, mpg=settings.VEHICLE_MPG)
    stations = find_stations_along_route(
        route.points,
        route.distance_miles,
        index,
        settings.STATION_CORRIDOR_MILES,
        settings.ROUTE_SAMPLE_MILES,
    )
    fuel_plan = plan_fuel_stops(
        stations, route.distance_miles, vehicle, vehicle.tank_gallons, settings.EXTRA_COST_TOLERANCE_USD
    )

    return TripPlan(
        start=origin,
        finish=destination,
        route=route,
        vehicle=vehicle,
        starting_fuel_gallons=vehicle.tank_gallons,
        fuel_plan=fuel_plan,
        stations_considered=len(stations),
        external_api_calls=external_calls_made(),
        processing_ms=(perf_counter() - started) * 1000,
    )
