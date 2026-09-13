from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import GeocodingService


class GeocodeLocationView(APIView):
    """
    Geocodes a location query name into coordinates.
    POST /api/geocoding/
    """
    authentication_classes = []
    permission_classes = []

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

        result = GeocodingService.geocode_location(str(location_name).strip())
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

        suggestions = GeocodingService.get_suggestions(query, limit=limit)
        return Response(
            {
                "success": True,
                "data": suggestions
            },
            status=status.HTTP_200_OK
        )
