from urllib.parse import urlencode

from django.urls import reverse
from rest_framework import serializers


class RoundedFloatField(serializers.FloatField):
    def __init__(self, decimals: int = 2, **kwargs):
        self.decimals = decimals
        super().__init__(read_only=True, **kwargs)

    def to_representation(self, value):
        return round(float(value), self.decimals) + 0.0


class TripRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)


class PlaceSearchSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=100)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=8)


class PlaceSuggestionSerializer(serializers.Serializer):
    label = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = RoundedFloatField(6)
    longitude = RoundedFloatField(6)


class LocationSerializer(serializers.Serializer):
    query = serializers.CharField()
    label = serializers.CharField()
    latitude = RoundedFloatField(6)
    longitude = RoundedFloatField(6)


class StationSerializer(serializers.Serializer):
    opis_id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = RoundedFloatField(6)
    longitude = RoundedFloatField(6)


class PointSerializer(serializers.Serializer):
    latitude = RoundedFloatField(6)
    longitude = RoundedFloatField(6)


class FuelStopSerializer(serializers.Serializer):
    station = StationSerializer()
    location = PointSerializer(source="*")
    distance_from_start_miles = RoundedFloatField(1, source="position_miles")
    distance_from_route_miles = RoundedFloatField(1)
    price_per_gallon = RoundedFloatField(3)
    gallons = RoundedFloatField(2)
    cost = RoundedFloatField(2)
    fuel_before_gallons = RoundedFloatField(2)
    fuel_after_gallons = RoundedFloatField(2)


class VehicleSerializer(serializers.Serializer):
    range_miles = RoundedFloatField(1)
    mpg = RoundedFloatField(1)
    tank_gallons = RoundedFloatField(2)


class RouteSerializer(serializers.Serializer):
    geometry_format = serializers.SerializerMethodField()
    geometry = serializers.CharField()

    def get_geometry_format(self, route) -> str:
        return "polyline5"


class TripPlanSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()
    distance_miles = RoundedFloatField(1, source="route.distance_miles")
    duration_hours = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    fuel_stops = serializers.SerializerMethodField()
    total_fuel_cost = RoundedFloatField(2, source="fuel_plan.total_cost")
    total_fuel_gallons = RoundedFloatField(2, source="fuel_plan.total_gallons")
    fuel_used_gallons = serializers.SerializerMethodField()
    fuel_remaining_gallons = RoundedFloatField(2, source="fuel_plan.fuel_remaining_gallons")
    stations_considered = serializers.IntegerField()
    map_url = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()
    route = RouteSerializer()

    def get_duration_hours(self, plan) -> float:
        return round(plan.route.duration_seconds / 3600, 1)

    def get_vehicle(self, plan) -> dict:
        return {**VehicleSerializer(plan.vehicle).data, "starting_fuel_gallons": round(plan.starting_fuel_gallons, 2)}

    def get_fuel_stops(self, plan) -> list[dict]:
        return [
            {"stop_number": number, **FuelStopSerializer(stop).data}
            for number, stop in enumerate(plan.fuel_plan.stops, start=1)
        ]

    def get_fuel_used_gallons(self, plan) -> float:
        return round(plan.route.distance_miles / plan.vehicle.mpg, 2)

    def get_map_url(self, plan) -> str:
        query = urlencode({"start": plan.start.query, "finish": plan.finish.query})
        path = f"{reverse('route-map')}?{query}"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    def get_meta(self, plan) -> dict:
        return {"external_api_calls": plan.external_api_calls, "processing_ms": round(plan.processing_ms, 1)}
