from django.urls import path
from .views import WeatherCurrentView

urlpatterns = [
    path('', WeatherCurrentView.as_view(), name='weather-current'),
]
