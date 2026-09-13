import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import AirQualityQuerySerializer, AirQualityResponseSerializer
from .services import AirQualityService

logger = logging.getLogger(__name__)


class AirQualityCurrentView(APIView):
    """
    Returns current criteria air pollutants and AQI for a given coordinate pair.
    GET /api/air-quality/?latitude=28.6139&longitude=77.2090
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = AirQualityQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Invalid or missing latitude/longitude parameters.",
                        "details": serializer.errors
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        lat = serializer.validated_data["latitude"]
        lon = serializer.validated_data["longitude"]

        air_data = AirQualityService.get_air_quality(lat, lon)
        if not air_data:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Air-quality data is temporarily unavailable. Please try again."
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "success": True,
                "data": air_data
            },
            status=status.HTTP_200_OK
        )
