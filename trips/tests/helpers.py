from stations.index import IndexedStation
from trips.services.corridor import RouteStation


def indexed_station(id: int, price: float, latitude: float = 35.0, longitude: float = -100.0) -> IndexedStation:
    return IndexedStation(id, id, f"Station {id}", "I-40, EXIT 1", f"Town {id}", "OK", price, latitude, longitude)


def route_station(id: int, position_miles: float, price: float) -> RouteStation:
    return RouteStation(indexed_station(id, price), position_miles, 1.0, 35.0, -100.0)
