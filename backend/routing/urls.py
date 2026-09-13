from django.urls import path
from .views import RouteSearchCreateView

urlpatterns = [
    path('search/', RouteSearchCreateView.as_view(), name='route-search-create'),
]
