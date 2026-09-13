import json
import logging
import urllib.parse
import urllib.request
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
    95: {"description": "Thunderstorm", "icon": "⛈️"},
    96: {"description": "Thunderstorm with slight hail", "icon": "⛈️"},
    99: {"description": "Thunderstorm with heavy hail", "icon": "⛈️"}
}


class WeatherService:
    """
    Retrieves real atmospheric weather data from the public Open-Meteo Forecast API.
    """

    @staticmethod
    def get_weather_description(code: int) -> Dict[str, str]:
        return WMO_WEATHER_CODES.get(code, {"description": "Unknown atmospheric conditions", "icon": "⛅"})

    @staticmethod
    def get_weather(latitude: float, longitude: float, location_label: str = "Weather near destination") -> Optional[Dict[str, Any]]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
            "wind_speed_unit": "kmh",
            "timezone": "auto"
        }
        url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "CleanRouteAI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Open-Meteo returned status {response.status}")
                    return None

                data = json.loads(response.read().decode("utf-8"))
                current = data.get("current", {})

                code = current.get("weather_code", 0)
                meta = WeatherService.get_weather_description(code)

                return {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "weather_code": code,
                    "description": meta["description"],
                    "icon": meta["icon"],
                    "precipitation": current.get("precipitation", 0),
                    "location_label": location_label,
                    "source": "Open-Meteo"
                }

        except Exception as e:
            logger.error(f"Weather fetch error for ({latitude}, {longitude}): {str(e)}")
            return None
