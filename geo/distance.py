import math

EARTH_RADIUS_MILES = 3958.7613
MILES_PER_METER = 0.000621371
MILES_PER_DEGREE_LATITUDE = 69.0


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def degrees_span(latitude: float, radius_miles: float) -> tuple[float, float]:
    """Latitude/longitude deltas that enclose a circle of the given radius."""
    d_lat = radius_miles / MILES_PER_DEGREE_LATITUDE
    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    d_lon = radius_miles / (MILES_PER_DEGREE_LATITUDE * cos_lat)
    return d_lat, d_lon
