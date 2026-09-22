from django.conf import settings
from django.views.generic import TemplateView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.serializers import (
    PlaceSearchSerializer,
    PlaceSuggestionSerializer,
    TripPlanSerializer,
    TripRequestSerializer,
)
from trips.services.locations import suggest_places
from trips.services.trip_planner import plan_trip


class TripPlanView(APIView):
    """Plan a trip: route geometry, cost-optimal fuel stops and total fuel spend."""

    def get(self, request: Request) -> Response:
        return self._plan(request, request.query_params)

    def post(self, request: Request) -> Response:
        return self._plan(request, request.data)

    def _plan(self, request: Request, data) -> Response:
        params = TripRequestSerializer(data=data)
        params.is_valid(raise_exception=True)
        plan = plan_trip(**params.validated_data)
        return Response(TripPlanSerializer(plan, context={"request": request}).data)


class PlaceSearchView(APIView):
    """Autocomplete for US cities that have fuel stations, served from the local station table."""

    def get(self, request: Request) -> Response:
        params = PlaceSearchSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        suggestions = suggest_places(**params.validated_data)
        return Response(PlaceSuggestionSerializer(suggestions, many=True).data)


class MapView(TemplateView):
    template_name = "trips/map.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            tile_url=settings.MAP_TILE_URL, tile_attribution=settings.MAP_TILE_ATTRIBUTION, **kwargs
        )
