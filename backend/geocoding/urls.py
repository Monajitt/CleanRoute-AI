from django.urls import path
from .views import GeocodeLocationView, GeocodeSuggestionsView

urlpatterns = [
    path('', GeocodeLocationView.as_view(), name='geocode-location'),
    path('suggestions/', GeocodeSuggestionsView.as_view(), name='geocode-suggestions'),
]
