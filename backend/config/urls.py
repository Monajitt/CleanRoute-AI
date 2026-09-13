"""
CleanRoute AI URL Configuration.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin Interface
    path('admin/', admin.site.urls),

    # Core System Health API
    path('api/health/', include('core.urls')),

    # Domain Specific API Namespaces
    path('api/routes/', include('routing.urls')),
    path('api/geocoding/', include('geocoding.urls')),
    path('api/weather/', include('weather.urls')),
    path('api/air-quality/', include('air_quality.urls')),
    path('api/recommendation/', include('recommendation.urls')),
    path('api/chat/', include('ai_assistant.urls')),
]
