import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from core.negotiation import IgnoreClientContentNegotiation
from .services import GeocodingService

logger = logging.getLogger(__name__)


class GeocodeLocationView(APIView):
    """
    Geocodes a location query name into coordinates.
    POST /api/geocoding/
    """
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]
    content_negotiation_class = IgnoreClientContentNegotiation

    def post(self, request):
        location_name = request.data.get("location") or request.data.get("name")
        if not location_name or not str(location_name).strip():
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Location parameter is required and cannot be empty."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = GeocodingService.geocode_location(str(location_name).strip())
        except Exception as e:
            logger.error(f"Geocoding error for '{location_name}': {e}")
            result = None

        if not result:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": f"Could not find coordinates for location '{location_name}'."
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "data": result
            },
            status=status.HTTP_200_OK
        )


class GeocodeSuggestionsView(APIView):
    """
    Search-as-you-type location suggestions powered by Photon Komoot API.
    GET /api/geocoding/suggestions/?q=<query>&limit=5
    """
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Response(
                {
                    "success": True,
                    "data": []
                },
                status=status.HTTP_200_OK
            )

        limit = request.query_params.get("limit", 5)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 5

        try:
            suggestions = GeocodingService.get_suggestions(query, limit=limit)
        except Exception as e:
            logger.error(f"Geocoding suggestions error for query '{query}': {e}")
            suggestions = []

        return Response(
            {
                "success": True,
                "data": suggestions
            },
            status=status.HTTP_200_OK
        )
