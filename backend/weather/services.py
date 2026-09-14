import time
import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo WMO Weather interpretation codes (WW)
WMO_WEATHER_CODES = {
    0: {"description": "Clear sky", "icon": "☀️"},
    1: {"description": "Mainly clear", "icon": "🌤️"},
    2: {"description": "Partly cloudy", "icon": "⛅"},
    3: {"description": "Overcast", "icon": "☁️"},
    45: {"description": "Fog", "icon": "🌫️"},
    48: {"description": "Depositing rime fog", "icon": "🌫️"},
    51: {"description": "Light drizzle", "icon": "🌦️"},
    53: {"description": "Moderate drizzle", "icon": "🌧️"},
    55: {"description": "Dense drizzle", "icon": "🌧️"},
    56: {"description": "Light freezing drizzle", "icon": "🌧️"},
    57: {"description": "Dense freezing drizzle", "icon": "🌧️"},
    61: {"description": "Slight rain", "icon": "🌦️"},
    63: {"description": "Moderate rain", "icon": "🌧️"},
    65: {"description": "Heavy rain", "icon": "🌧️"},
    66: {"description": "Light freezing rain", "icon": "🌧️"},
    67: {"description": "Heavy freezing rain", "icon": "🌧️"},
    71: {"description": "Slight snow fall", "icon": "🌨️"},
    73: {"description": "Moderate snow fall", "icon": "🌨️"},
    75: {"description": "Heavy snow fall", "icon": "❄️"},
    77: {"description": "Snow grains", "icon": "❄️"},
    80: {"description": "Slight rain showers", "icon": "🌦️"},
    81: {"description": "Moderate rain showers", "icon": "🌧️"},
    82: {"description": "Violent rain showers", "icon": "⛈️"},
    85: {"description": "Slight snow showers", "icon": "🌨️"},
    86: {"description": "Heavy snow showers", "icon": "❄️"},
    85: {"description": "Slight snow showers", "icon": "🌨️"},
    95: {"description": "Thunderstorm", "icon": "⛈️"},
    96: {"description": "Thunderstorm with slight hail", "icon": "⛈️"},
    99: {"description": "Thunderstorm with heavy hail", "icon": "⛈️"}
}

# Server-side in-memory cache: (lat_round, lon_round) -> { "timestamp": float, "data": dict }
_weather_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


class WeatherService:
    """
    Retrieves real atmospheric weather data from the public Open-Meteo Forecast API
    with server-side grid caching, coordinate rounding, and HTTP 429 rate-limit resilience.
    """

    @classmethod
    def clear_cache(cls):
        global _weather_cache
        _weather_cache.clear()

    @staticmethod
    def get_weather_description(code: int) -> Dict[str, str]:
        return WMO_WEATHER_CODES.get(code, {"description": "Unknown atmospheric conditions", "icon": "⛅"})

    @staticmethod
    def get_weather(
        latitude: float,
        longitude: float,
        location_label: str = "Weather near destination"
    ) -> Optional[Dict[str, Any]]:
        try:
            # Round coordinates to 2 decimal places (~1.1 km grid) to prevent duplicate calls
            lat = round(float(latitude), 2)
            lon = round(float(longitude), 2)
        except (ValueError, TypeError):
            logger.warning(f"Invalid weather coordinates: lat={latitude}, lon={longitude}")
            return None

        cache_key = f"{lat:.2f},{lon:.2f}"
        now = time.time()

        # 1. Check in-memory server cache
        cached_entry = _weather_cache.get(cache_key)
        if cached_entry and (now - cached_entry["timestamp"] < CACHE_TTL_SECONDS):
            cached_data = dict(cached_entry["data"])
            cached_data["location_label"] = location_label
            return cached_data

        # 2. Query upstream Open-Meteo API
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
            "wind_speed_unit": "kmh",
            "timezone": "auto"
        }
        url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "CleanRouteAI/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    logger.error(f"Open-Meteo returned status {response.status}")
                    return None

                data = json.loads(response.read().decode("utf-8"))
                current = data.get("current", {})

                code = current.get("weather_code", 0)
                meta = WeatherService.get_weather_description(code)

                result = {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "weather_code": code,
                    "description": meta["description"],
                    "icon": meta["icon"],
                    "precipitation": current.get("precipitation", 0),
                    "location_label": location_label,
                    "source": "Open-Meteo",
                    "is_available": True
                }

                # Store in server cache
                _weather_cache[cache_key] = {"timestamp": now, "data": result}
                return result

        except urllib.error.HTTPError as http_err:
            if http_err.code == 429:
                logger.warning(f"Open-Meteo HTTP 429 (Rate Limited) for ({lat}, {lon})")
                # If we have any existing cache (even older than TTL), return it gracefully
                if cached_entry:
                    fallback_data = dict(cached_entry["data"])
                    fallback_data["location_label"] = location_label
                    fallback_data["source"] = "Open-Meteo (cached - rate limit active)"
                    return fallback_data

                # Return clear rate-limited indicator without fake values
                return {
                    "temperature": None,
                    "humidity": None,
                    "wind_speed": None,
                    "weather_code": None,
                    "description": "Weather service temporarily busy (Rate limited)",
                    "icon": "⛅",
                    "precipitation": None,
                    "location_label": location_label,
                    "source": "Open-Meteo (rate limited)",
                    "is_available": False,
                    "rate_limited": True
                }
            logger.error(f"Open-Meteo HTTP error {http_err.code} for ({lat}, {lon}): {http_err.reason}")
            # If cached entry exists, serve it
            if cached_entry:
                fallback_data = dict(cached_entry["data"])
                fallback_data["location_label"] = location_label
                return fallback_data
            return None

        except Exception as e:
            logger.error(f"Weather fetch error for ({lat}, {lon}): {str(e)}")
            if cached_entry:
                fallback_data = dict(cached_entry["data"])
                fallback_data["location_label"] = location_label
                return fallback_data
            return None
