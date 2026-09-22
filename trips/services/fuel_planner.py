from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

from stations.index import IndexedStation
from trips.exceptions import TripNotFeasible
from trips.services.corridor import RouteStation

EPSILON = 1e-6


@dataclass(frozen=True, slots=True)
class Vehicle:
    range_miles: float
    mpg: float

    @property
    def tank_gallons(self) -> float:
        return self.range_miles / self.mpg


@dataclass(frozen=True, slots=True)
class FuelStop:
    station: IndexedStation
    position_miles: float
    distance_from_route_miles: float
    latitude: float
    longitude: float
    gallons: float
    price_per_gallon: float
    cost: float
    fuel_before_gallons: float
    fuel_after_gallons: float


@dataclass(frozen=True, slots=True)
class FuelPlan:
    stops: list[FuelStop]
    total_cost: float
    total_gallons: float
    fuel_remaining_gallons: float


@dataclass(frozen=True, slots=True)
class Purchase:
    index: int
    gallons: float


def plan_fuel_stops(
    stations: Sequence[RouteStation],
    total_miles: float,
    vehicle: Vehicle,
    starting_fuel_gallons: float,
    extra_cost_tolerance: float = 0.0,
) -> FuelPlan:
    """Minimum-cost refuelling along a fixed route.

    Runs the classic greedy for the fixed-path gas station problem, which is provably cost-optimal: at each
    station, if a cheaper station is reachable on a full tank, buy just enough to get there; otherwise fill
    up (or buy just enough to finish) and continue to the cheapest reachable station. Stops are then folded
    into their neighbours, cheapest merge first, as long as the plan stays within `extra_cost_tolerance` of
    the optimal cost, because a stop is not worth a few cents.
    """
    trip = _Trip(stations, total_miles, vehicle, min(starting_fuel_gallons, vehicle.tank_gallons))
    purchases = _consolidate(trip, _greedy(trip), extra_cost_tolerance)
    stops, remaining = trip.simulate(purchases)
    return FuelPlan(
        stops=stops,
        total_cost=_total_cost(stops),
        total_gallons=sum(stop.gallons for stop in stops),
        fuel_remaining_gallons=remaining,
    )


class _Trip:
    def __init__(self, stations: Sequence[RouteStation], total_miles: float, vehicle: Vehicle, starting_fuel: float):
        self.stations = stations
        self.positions = [entry.position_miles for entry in stations]
        self.total_miles = total_miles
        self.vehicle = vehicle
        self.tank = vehicle.tank_gallons
        self.gallons_per_mile = 1 / vehicle.mpg
        self.starting_fuel = starting_fuel

    def simulate(self, purchases: Sequence[Purchase]) -> tuple[list[FuelStop], float] | None:
        """Drive the route with the given purchases; None when the tank would run dry or overflow."""
        fuel = self.starting_fuel
        position = 0.0
        stops = []
        for purchase in purchases:
            entry = self.stations[purchase.index]
            fuel -= (entry.position_miles - position) * self.gallons_per_mile
            if fuel < -EPSILON or fuel + purchase.gallons > self.tank + EPSILON:
                return None
            stops.append(_stop(entry, fuel, purchase.gallons))
            fuel += purchase.gallons
            position = entry.position_miles
        fuel -= (self.total_miles - position) * self.gallons_per_mile
        if fuel < -EPSILON:
            return None
        return stops, max(fuel, 0.0)


def _greedy(trip: _Trip) -> list[Purchase]:
    fuel = trip.starting_fuel
    position = 0.0
    current: int | None = None
    purchases: list[Purchase] = []

    while trip.total_miles - position > fuel / trip.gallons_per_mile + EPSILON:
        can_refill = current is not None
        reach = position + (trip.tank if can_refill else fuel) / trip.gallons_per_mile
        first = 0 if current is None else current + 1
        window = range(first, bisect_right(trip.positions, reach + EPSILON))
        current_price = trip.stations[current].station.price if can_refill else float("inf")
        cheaper = next((i for i in window if trip.stations[i].station.price <= current_price), None)
        next_index: int | None

        if cheaper is not None:
            next_index = cheaper
            needed = max(0.0, (trip.positions[cheaper] - position) * trip.gallons_per_mile - fuel)
        elif can_refill and trip.total_miles - position <= trip.vehicle.range_miles + EPSILON:
            next_index = None
            needed = (trip.total_miles - position) * trip.gallons_per_mile - fuel
        elif window:
            next_index = min(window, key=lambda i: trip.stations[i].station.price)
            needed = trip.tank - fuel
        else:
            raise TripNotFeasible(_gap_message(trip.stations, current, trip.vehicle))

        if needed > EPSILON:
            purchases.append(Purchase(current, needed))
            fuel += needed

        if next_index is None:
            break
        fuel -= (trip.positions[next_index] - position) * trip.gallons_per_mile
        position = trip.positions[next_index]
        current = next_index

    return purchases


def _consolidate(trip: _Trip, purchases: list[Purchase], extra_cost_tolerance: float) -> list[Purchase]:
    """Merge purchases into neighbouring stops, cheapest merge first, within the allowed extra cost."""
    if extra_cost_tolerance <= 0:
        return purchases
    stops, _ = trip.simulate(purchases)
    budget = _total_cost(stops) + extra_cost_tolerance

    while len(purchases) > 1:
        best: tuple[float, list[Purchase]] | None = None
        for source in range(len(purchases)):
            for target in (source - 1, source + 1):
                if not 0 <= target < len(purchases):
                    continue
                candidate = _move_purchase(purchases, source, target)
                simulated = trip.simulate(candidate)
                if simulated is None:
                    continue
                cost = _total_cost(simulated[0])
                if best is None or cost < best[0]:
                    best = (cost, candidate)
        if best is None or best[0] >= budget:
            break
        purchases = best[1]
    return purchases


def _move_purchase(purchases: list[Purchase], source: int, target: int) -> list[Purchase]:
    gallons = purchases[source].gallons + purchases[target].gallons
    result = [Purchase(p.index, gallons) if i == target else p for i, p in enumerate(purchases)]
    del result[source]
    return result


def _total_cost(stops: Sequence[FuelStop]) -> float:
    return sum(stop.cost for stop in stops)


def _stop(entry: RouteStation, fuel_before: float, gallons: float) -> FuelStop:
    return FuelStop(
        station=entry.station,
        position_miles=entry.position_miles,
        distance_from_route_miles=entry.distance_from_route_miles,
        latitude=entry.latitude,
        longitude=entry.longitude,
        gallons=gallons,
        price_per_gallon=entry.station.price,
        cost=gallons * entry.station.price,
        fuel_before_gallons=fuel_before,
        fuel_after_gallons=fuel_before + gallons,
    )


def _gap_message(stations: Sequence[RouteStation], current: int | None, vehicle: Vehicle) -> str:
    if current is None:
        return f"No fuel station is reachable from the start within the vehicle's {vehicle.range_miles:.0f}-mile range"
    station = stations[current]
    return (
        f"No fuel station within {vehicle.range_miles:.0f} miles after {station.station.name} "
        f"({station.station.city}, {station.station.state}) at mile {station.position_miles:.0f}"
    )
