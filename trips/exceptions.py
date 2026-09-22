from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from integrations.exceptions import NoRouteError, UpstreamServiceError


class LocationNotFound(Exception):
    """A start or finish location could not be resolved to a place in the USA."""


class TripNotFeasible(Exception):
    """The route has a gap between fuel stations longer than the vehicle's range."""


class StationsNotLoaded(Exception):
    """The station table is empty, so no trip can be planned."""


_ERROR_RESPONSES: dict[type[Exception], tuple[int, str]] = {
    LocationNotFound: (status.HTTP_422_UNPROCESSABLE_ENTITY, "location_not_found"),
    NoRouteError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "route_not_found"),
    TripNotFeasible: (status.HTTP_422_UNPROCESSABLE_ENTITY, "trip_not_feasible"),
    StationsNotLoaded: (status.HTTP_503_SERVICE_UNAVAILABLE, "stations_not_loaded"),
    UpstreamServiceError: (status.HTTP_503_SERVICE_UNAVAILABLE, "upstream_unavailable"),
}


def api_exception_handler(exc, context):
    for exception_type, (status_code, code) in _ERROR_RESPONSES.items():
        if isinstance(exc, exception_type):
            return Response({"error": {"code": code, "message": str(exc)}}, status=status_code)

    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {
            "error": {"code": "invalid_request", "message": "Invalid request parameters", "details": exc.detail}
        }
    elif isinstance(exc, APIException):
        response.data = {"error": {"code": exc.get_codes(), "message": str(exc.detail)}}
    return response
