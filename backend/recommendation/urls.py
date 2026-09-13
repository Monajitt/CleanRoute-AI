from django.urls import path
from .views import RecommendationPlaceholderView, RouteScoringView

urlpatterns = [
    path('', RecommendationPlaceholderView.as_view(), name='recommendation-placeholder'),
    path('score/', RouteScoringView.as_view(), name='route-scoring'),
]
