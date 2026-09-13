import json
import logging
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any
from .models import GeocodeCache

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "CleanRouteAI/1.0 (cleanroute.project@gmail.com)"


PHOTON_BASE_URL = "https://photon.komoot.io/api/"


class GeocodingService:
    """
    Server-side geocoding and search-as-you-type suggestion service
    backed by Komoot Photon (OpenStreetMap) and Nominatim with local database caching.
    """

    @staticmethod
    def get_suggestions(query: str, limit: int = 5) -> list[Dict[str, Any]]:
        """
        Search-as-you-type location suggestions powered by Photon OpenStreetMap API.
        Returns a structured list with place name, city/locality, state, country, and coordinates.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip()
        params = {
            "q": clean_query,
            "limit": min(max(1, limit), 10)
        }
        query_string = urllib.parse.urlencode(params)
        request_url = f"{PHOTON_BASE_URL}?{query_string}"

        req = urllib.request.Request(
            request_url,
            headers={
                "User-Agent": NOMINATIM_USER_AGENT,
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    logger.warning(f"Photon suggestions returned HTTP {response.status}")
                    return []

                data = json.loads(response.read().decode("utf-8"))
                features = data.get("features", [])
                suggestions = []

                for feat in features:
                    props = feat.get("properties", {})
                    geometry = feat.get("geometry", {})
                    coords = geometry.get("coordinates", [])

                    if len(coords) < 2:
                        continue

                    lon = float(coords[0])
                    lat = float(coords[1])

                    name = props.get("name") or props.get("street") or clean_query
                    city = props.get("city") or props.get("district") or props.get("locality")
                    state = props.get("state")
                    country = props.get("country")

                    subtitle_elements = []
                    if city and city.lower() != name.lower():
                        subtitle_elements.append(city)
                    if state and state.lower() != name.lower() and state.lower() != (city or "").lower():
                        subtitle_elements.append(state)
                    if country and country.lower() != name.lower():
                        subtitle_elements.append(country)

                    subtitle = ", ".join(subtitle_elements) if subtitle_elements else (country or "")
                    display_name = f"{name}, {subtitle}" if subtitle else name

                    suggestions.append({
                        "name": name,
                        "city": city or "",
                        "state": state or "",
                        "country": country or "",
                        "display_name": display_name,
                        "latitude": lat,
                        "longitude": lon,
                        "osm_key": props.get("osm_key", ""),
                        "osm_value": props.get("osm_value", "")
                    })

                return suggestions

        except Exception as e:
            logger.error(f"Photon suggestion lookup failed for '{clean_query}': {str(e)}")
            return []

    @staticmethod
    def geocode_location(location_name: str) -> Optional[Dict[str, Any]]:
        if not location_name or not location_name.strip():
            return None

        query_normalized = location_name.strip()

        # 1. Check local database cache
        cached = GeocodeCache.objects.filter(query__iexact=query_normalized).first()
        if cached:
            return {
                "name": cached.name,
                "latitude": cached.latitude,
                "longitude": cached.longitude,
                "display_name": cached.display_name,
                "cached": True
            }

        # 2. Try Nominatim API
        params = {
            "q": query_normalized,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        query_string = urllib.parse.urlencode(params)
        request_url = f"{NOMINATIM_BASE_URL}?{query_string}"

        req = urllib.request.Request(
            request_url,
            headers={
                "User-Agent": NOMINATIM_USER_AGENT,
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if data and len(data) > 0:
                        primary_result = data[0]
                        lat = float(primary_result.get("lat"))
                        lon = float(primary_result.get("lon"))
                        display_name = primary_result.get("display_name", query_normalized)

                        # Save to local database cache
                        GeocodeCache.objects.update_or_create(
                            query=query_normalized,
                            defaults={
                                "name": query_normalized,
                                "latitude": lat,
                                "longitude": lon,
                                "display_name": display_name
                            }
                        )

                        return {
                            "name": query_normalized,
                            "latitude": lat,
                            "longitude": lon,
                            "display_name": display_name,
                            "cached": False
                        }
        except Exception as e:
            logger.warning(f"Nominatim lookup failed for '{query_normalized}', attempting Photon fallback: {str(e)}")

        # 3. Fallback to Photon
        try:
            suggestions = GeocodingService.get_suggestions(query_normalized, limit=1)
            if suggestions:
                top = suggestions[0]
                GeocodeCache.objects.update_or_create(
                    query=query_normalized,
                    defaults={
                        "name": top["name"],
                        "latitude": top["latitude"],
                        "longitude": top["longitude"],
                        "display_name": top["display_name"]
                    }
                )
                return {
                    "name": top["name"],
                    "latitude": top["latitude"],
                    "longitude": top["longitude"],
                    "display_name": top["display_name"],
                    "cached": False
                }
        except Exception as e:
            logger.error(f"Photon fallback geocode failed for '{query_normalized}': {str(e)}")

        return None
