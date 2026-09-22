class UpstreamServiceError(Exception):
    """An external map or geocoding service failed or returned an unexpected response."""


class NoRouteError(Exception):
    """The routing service could not find a driveable route between the points."""
