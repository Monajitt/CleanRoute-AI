import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geocoding.services import GeocodingService
from weather.services import WeatherService
from air_quality.services import AirQualityService
from recommendation.services import RecommendationService
from .models import RouteSearch
from .serializers import RouteSearchSerializer
from .services import RoutingService

logger = logging.getLogger(__name__)


class RouteSearchCreateView(APIView):
    """
    Unified Route Search Endpoint:
    1. Geocodes origin & destination via Nominatim.
    2. Retrieves real route geometry, distance, and duration via OpenRouteService.
    3. Fetches live weather conditions near destination via Open-Meteo.
    4. Persists the search inquiry to PostgreSQL.
    5. Returns unified payload to the frontend.
    POST /api/routes/search/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RouteSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Invalid input parameters",
                        "details": serializer.errors
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        origin_name = serializer.validated_data["origin_name"].strip()
        dest_name = serializer.validated_data["destination_name"].strip()
        travel_mode = serializer.validated_data.get("travel_mode", "cycling")
        route_preference = serializer.validated_data.get("route_preference", "balanced")

        # 1. Resolve Origin Coordinates
        orig_lat = serializer.validated_data.get("origin_latitude")
        orig_lon = serializer.validated_data.get("origin_longitude")

        if orig_lat is not None and orig_lon is not None:
            origin_geo = {
                "name": origin_name,
                "latitude": float(orig_lat),
                "longitude": float(orig_lon),
                "display_name": origin_name,
                "cached": False
            }
        else:
            origin_geo = GeocodingService.geocode_location(origin_name)

        if not origin_geo:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Location not found. Please select a location from the suggestions."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Resolve Destination Coordinates
        dest_lat = serializer.validated_data.get("destination_latitude")
        dest_lon = serializer.validated_data.get("destination_longitude")

        if dest_lat is not None and dest_lon is not None:
            dest_geo = {
                "name": dest_name,
                "latitude": float(dest_lat),
                "longitude": float(dest_lon),
                "display_name": dest_name,
                "cached": False
            }
        else:
            dest_geo = GeocodingService.geocode_location(dest_name)

        if not dest_geo:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Location not found. Please select a location from the suggestions."
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Calculate Real Routes via OpenRouteService
        try:
            routes = RoutingService.get_routes(
                origin_coords=[origin_geo["latitude"], origin_geo["longitude"]],
                dest_coords=[dest_geo["latitude"], dest_geo["longitude"]],
                travel_mode=travel_mode
            )
        except ValueError as val_err:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": str(val_err)
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as err:
            logger.error(f"Routing computation error: {str(err)}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "Route service is temporarily unavailable. Please verify connection and try again."
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not routes:
            return Response(
                {
                    "success": False,
                    "error": {
                        "message": "No navigable route found between the specified locations for this travel mode."
                    }
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. Attach Route-Level Air Quality & Estimated Pollution Exposure
        for route in routes:
            geom = route.get("geometry", [])
            route_aq = AirQualityService.sample_route_air_quality(geom, num_samples=8)
            route["air_quality"] = route_aq
            route["pollution_exposure"] = route_aq.get("estimated_pollution_exposure")

        # 5. Calculate Deterministic Multi-Criteria Recommendation Scoring & Ranking
        scored_routes = RecommendationService.score_and_rank_routes(routes, preference=route_preference)

        # 6. Fetch Real Atmospheric Weather near Destination via Open-Meteo
        weather_info = WeatherService.get_weather(
            dest_geo["latitude"],
            dest_geo["longitude"],
            location_label=f"Weather near destination ({dest_name})"
        )

        # 7. Persist inquiry to PostgreSQL
        search_record = serializer.save()

        # 8. Return unified real-data response
        return Response(
            {
                "success": True,
                "data": {
                    "search_id": search_record.id,
                    "origin_name": origin_name,
                    "destination_name": dest_name,
                    "origin": {
                        "name": origin_name,
                        "latitude": origin_geo["latitude"],
                        "longitude": origin_geo["longitude"],
                        "display_name": origin_geo["display_name"]
                    },
                    "destination": {
                        "name": dest_name,
                        "latitude": dest_geo["latitude"],
                        "longitude": dest_geo["longitude"],
                        "display_name": dest_geo["display_name"]
                    },
                    "travel_mode": travel_mode,
                    "route_preference": route_preference,
                    "routes": scored_routes,
                    "recommended_route": next((r for r in scored_routes if r.get("is_recommended")), scored_routes[0]),
                    "weather": weather_info
                }
            },
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        recent_searches = RouteSearch.objects.all()[:10]
        serializer = RouteSearchSerializer(recent_searches, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
