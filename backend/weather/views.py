from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import WeatherService


class WeatherCurrentView(APIView):
    """
    Retrieves live weather conditions for given coordinates via Open-Meteo.
    GET or POST /api/weather/
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        lat = request.query_params.get("latitude") or request.query_params.get("lat")
        lon = request.query_params.get("longitude") or request.query_params.get("lon")
        return self._fetch_weather(lat, lon)

    def post(self, request):
        lat = request.data.get("latitude") or request.data.get("lat")
        lon = request.data.get("longitude") or request.data.get("lon")
        return self._fetch_weather(lat, lon)

    def _fetch_weather(self, lat, lon):
        if lat is None or lon is None:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Both latitude and longitude parameters are required."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            latitude = float(lat)
            longitude = float(lon)
            if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "message": "Coordinates out of bounds (-90 to 90 lat, -180 to 180 lon)."
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Latitude and longitude must be valid floating-point numbers."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        weather_data = WeatherService.get_weather(latitude, longitude)
        if not weather_data:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Weather information is currently unavailable from Open-Meteo."
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "success": True,
                "data": weather_data
            },
            status=status.HTTP_200_OK
        )
