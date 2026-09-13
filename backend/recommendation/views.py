import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import RecommendationService, normalize_preference

logger = logging.getLogger(__name__)


class RouteScoringView(APIView):
    """
    Deterministically scores and ranks route alternatives for a requested priority.
    Does not perform external routing queries; re-scores existing route data.
    POST /api/recommendation/score/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        routes = request.data.get("routes", [])
        preference = request.data.get("preference") or request.data.get("priority") or "balanced"

        if not isinstance(routes, list) or len(routes) == 0:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "A non-empty list of route objects is required for scoring."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            scored_routes = RecommendationService.score_and_rank_routes(routes, preference=str(preference))
            recommended = next((r for r in scored_routes if r.get("is_recommended")), scored_routes[0])

            return Response(
                {
                    "success": True,
                    "data": {
                        "priority": normalize_preference(preference),
                        "routes": scored_routes,
                        "recommended_route": recommended
                    }
                },
                status=status.HTTP_200_OK
            )
        except Exception as err:
            logger.error(f"Error in RouteScoringView: {err}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Failed to re-score routes.",
                        "details": str(err)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommendationPlaceholderView(APIView):
    """
    Status endpoint for AI Recommendation engine.
    GET /api/recommendation/
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "success": True,
                "message": "CleanRoute AI Deterministic Recommendation Engine is active.",
                "supported_priorities": ["health_first", "balanced", "time_first"],
                "weights": {
                    "health_first": {"pollution": 0.60, "time": 0.20, "distance": 0.20},
                    "balanced": {"pollution": 0.40, "time": 0.30, "distance": 0.30},
                    "time_first": {"pollution": 0.20, "time": 0.60, "distance": 0.20}
                }
            },
            status=status.HTTP_200_OK
        )
