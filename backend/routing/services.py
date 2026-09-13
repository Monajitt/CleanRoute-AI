import os
import json
import logging
import urllib.request
import time
import copy
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

ORS_DIRECTIONS_BASE_URL = "https://api.heigit.org/openrouteservice/v2/directions"

# Centralized mapping from CleanRoute AI travel modes to OpenRouteService profiles
ORS_PROFILE_MAPPING = {
    "walking": "foot-walking",
    "cycling": "cycling-regular",
    "driving": "driving-car"
}


class RoutingService:
    """
    Integrates with OpenRouteService Directions API v2 to retrieve real road routes,
    accurate distances, durations, and coordinate geometries.
    Includes in-memory caching to eliminate redundant API calls and avoid rate limits.
    """
    _route_cache: Dict[tuple, tuple] = {}

    @staticmethod
    def get_api_key() -> Optional[str]:
        return os.getenv("OPENROUTESERVICE_API_KEY", "").strip()

    @staticmethod
    def get_profile(travel_mode: str) -> str:
        mode_clean = (travel_mode or "cycling").lower().strip()
        return ORS_PROFILE_MAPPING.get(mode_clean, "cycling-regular")

    @classmethod
    def get_routes(
        cls,
        origin_coords: List[float],
        dest_coords: List[float],
        travel_mode: str = "cycling"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Queries OpenRouteService for real route geometry, distance, and duration.
        Coordinates parameter format: [latitude, longitude]
        """
        api_key = RoutingService.get_api_key()
        if not api_key:
            logger.error("OPENROUTESERVICE_API_KEY is not configured in environment.")
            raise ValueError("OpenRouteService API key is missing on the server.")

        profile = RoutingService.get_profile(travel_mode)
        endpoint_url = f"{ORS_DIRECTIONS_BASE_URL}/{profile}/geojson"

        # Calculate approximate straight-line distance
        import math
        lat1, lon1 = float(origin_coords[0]), float(origin_coords[1])
        lat2, lon2 = float(dest_coords[0]), float(dest_coords[1])
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        approx_km = 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

        cache_key = (
            round(lat1, 4),
            round(lon1, 4),
            round(lat2, 4),
            round(lon2, 4),
            profile
        )

        # Check in-memory route cache (30-minute freshness window)
        if cache_key in cls._route_cache:
            cached_time, cached_routes = cls._route_cache[cache_key]
            if time.time() - cached_time < 1800:
                logger.info(f"Returning {len(cached_routes)} cached routes for {cache_key}")
                return copy.deepcopy(cached_routes)

        # ORS restricts alternative_routes algorithm to distance <= 100km
        use_alternatives = approx_km < 80.0

        def build_request(include_alternatives: bool):
            body = {
                "coordinates": [
                    [lon1, lat1],
                    [lon2, lat2]
                ]
            }
            if include_alternatives:
                body["alternative_routes"] = {"target_count": 3}

            raw_payload = json.dumps(body).encode("utf-8")
            headers = {
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/geo+json, application/json",
                "User-Agent": "CleanRouteAI/1.0"
            }
            return urllib.request.Request(endpoint_url, data=raw_payload, headers=headers)

        req = build_request(use_alternatives)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"OpenRouteService returned HTTP {response.status}")
                    return None
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            # If rejected due to alternative routes distance limit, retry without alternatives
            if use_alternatives and ("alternative Routes" in error_body or "2004" in error_body):
                logger.info("Retrying ORS directions without alternative_routes algorithm.")
                retry_req = build_request(False)
                with urllib.request.urlopen(retry_req, timeout=30) as retry_response:
                    data = json.loads(retry_response.read().decode("utf-8"))
            else:
                logger.error(f"OpenRouteService HTTPError {http_err.code}: {error_body}")
                if cache_key in cls._route_cache:
                    logger.warning(f"Using cached routes due to ORS HTTP error: {cache_key}")
                    return copy.deepcopy(cls._route_cache[cache_key][1])
                raise RuntimeError(f"OpenRouteService error: HTTP {http_err.code}")
        except Exception as err:
            logger.error(f"OpenRouteService request failure: {str(err)}")
            if cache_key in cls._route_cache:
                logger.warning(f"Using cached routes due to ORS connection failure: {cache_key}")
                return copy.deepcopy(cls._route_cache[cache_key][1])
            return None

        try:
            features = data.get("features", [])
            if not features:
                logger.warning("OpenRouteService returned no features for given points.")
                return None

            route_colors = ["#059669", "#0284c7", "#7c3aed"]
            parsed_routes = []

            for idx, feat in enumerate(features):
                props = feat.get("properties", {})
                summary = props.get("summary", {})
                geometry = feat.get("geometry", {})

                dist_meters = summary.get("distance", 0.0)
                dur_seconds = summary.get("duration", 0.0)

                # Convert meters to kilometers and seconds to minutes
                distance_km = round(dist_meters / 1000.0, 2)
                duration_minutes = round(dur_seconds / 60.0, 1)

                raw_coords = geometry.get("coordinates", [])
                # Invert [lon, lat] to [lat, lon] for Leaflet mapping compatibility
                leaflet_coordinates = [[point[1], point[0]] for point in raw_coords]

                is_primary = (idx == 0)
                route_name = f"Route {idx + 1}" + (" (Primary Route)" if is_primary else " (Alternative)")

                parsed_routes.append({
                    "id": idx + 1,
                    "name": route_name,
                    "tagline": f"Via OpenRouteService {profile}",
                    "distance_km": distance_km,
                    "duration_minutes": duration_minutes,
                    "geometry": leaflet_coordinates,
                    "is_recommended": is_primary,
                    "color": route_colors[idx % len(route_colors)],
                    "travel_mode": travel_mode,
                    "profile": profile
                })

            cls._route_cache[cache_key] = (time.time(), copy.deepcopy(parsed_routes))
            return parsed_routes

        except Exception as err:
            logger.error(f"Error parsing ORS features: {str(err)}")
            return None
