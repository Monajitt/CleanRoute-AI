from django.urls import path
from .views import AirQualityCurrentView

urlpatterns = [
    path('', AirQualityCurrentView.as_view(), name='air-quality-current'),
]
