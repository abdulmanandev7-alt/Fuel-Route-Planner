from django.urls import path

from trips.views import MapView, PlaceSearchView, TripPlanView

urlpatterns = [
    path("api/route/", TripPlanView.as_view(), name="route-plan"),
    path("api/places/", PlaceSearchView.as_view(), name="place-search"),
    path("", MapView.as_view(), name="route-map"),
]
