import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def get_aqi_category(aqi: float) -> str:
    """Classifies standard US EPA AQI into official health categories."""
    if aqi is None:
        return "Moderate"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def get_exposure_level(aqi: float) -> str:
    """Provides non-medical estimated exposure description."""
    if aqi is None:
        return "Moderate estimated pollution exposure"
    if aqi <= 50:
        return "Low estimated pollution exposure"
    if aqi <= 100:
        return "Moderate estimated pollution exposure"
    if aqi <= 150:
        return "Elevated estimated pollution exposure"
    return "High estimated pollution exposure"


import time
# Server-side in-memory cache for air quality: "lat,lon" -> {"timestamp": float, "data": dict}
_aqi_cache: Dict[str, Dict[str, Any]] = {}
AQI_CACHE_TTL_SECONDS = 900  # 15 minutes


class AirQualityService:
    """
    Fetches live atmospheric criteria air pollutants (PM2.5, PM10, NO2, O3, US AQI)
    from Open-Meteo Air Quality API. Samples road route coordinates for route-level
    pollution exposure estimation.
    """

    @classmethod
    def clear_cache(cls):
        global _aqi_cache
        _aqi_cache.clear()

    @staticmethod
    def get_air_quality(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        Fetches current air quality metrics for a single coordinate point with server-side caching.
        """
        try:
            lat = round(float(latitude), 2)
            lon = round(float(longitude), 2)
        except (ValueError, TypeError):
            logger.warning(f"Invalid coordinates passed to get_air_quality: lat={latitude}, lon={longitude}")
            return None

        cache_key = f"{lat:.2f},{lon:.2f}"
        now = time.time()

        cached_entry = _aqi_cache.get(cache_key)
        if cached_entry and (now - cached_entry["timestamp"] < AQI_CACHE_TTL_SECONDS):
            return dict(cached_entry["data"])

        url = (
            f"{OPEN_METEO_AIR_QUALITY_URL}"
            f"?latitude={lat}&longitude={lon}"
            f"&current=pm10,pm2_5,nitrogen_dioxide,ozone,us_aqi"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CleanRouteAI/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Open-Meteo Air Quality returned HTTP {response.status}")
                    if cached_entry:
                        return dict(cached_entry["data"])
                    return None
                data = json.loads(response.read().decode("utf-8"))

            current = data.get("current", {})
            aqi = current.get("us_aqi")
            if aqi is None:
                # Fallback to standard conversion if us_aqi is absent
                pm25 = current.get("pm2_5", 25.0)
                aqi = round(min(500.0, pm25 * 2.1), 1)

            result = {
                "latitude": lat,
                "longitude": lon,
                "aqi": round(float(aqi), 1),
                "pm25": round(float(current.get("pm2_5") or 0.0), 1),
                "pm10": round(float(current.get("pm10") or 0.0), 1),
                "no2": round(float(current.get("nitrogen_dioxide") or 0.0), 1),
                "ozone": round(float(current.get("ozone") or 0.0), 1),
                "aqi_category": get_aqi_category(float(aqi)),
                "estimated_pollution_exposure": get_exposure_level(float(aqi)),
                "source": "Open-Meteo Air Quality"
            }
            _aqi_cache[cache_key] = {"timestamp": now, "data": result}
            return result
        except Exception as err:
            logger.warning(f"Air quality fetch error at [{lat}, {lon}]: {err}")
            if cached_entry:
                return dict(cached_entry["data"])
            return {
                "latitude": lat,
                "longitude": lon,
                "aqi": 58.0,
                "pm25": 16.5,
                "pm10": 28.0,
                "no2": 12.0,
                "ozone": 24.0,
                "aqi_category": "Moderate",
                "estimated_pollution_exposure": "Moderate estimated pollution exposure",
                "source": "Estimated baseline (Service temporarily unavailable)"
            }

    @staticmethod
    def sample_route_air_quality(coordinates: List[List[float]], num_samples: int = 8) -> Dict[str, Any]:
        """
        Samples coordinates along a route geometry [[lat, lon], ...], queries
        Open-Meteo Air Quality in a single batched request, and calculates
        route-level average air quality metrics and estimated pollution exposure.
        """
        if not coordinates:
            return {
                "average_aqi": 60.0,
                "pm25": 18.0,
                "pm10": 30.0,
                "no2": 14.0,
                "ozone": 25.0,
                "aqi_category": "Moderate",
                "estimated_pollution_exposure": "Moderate estimated pollution exposure",
                "points_sampled": 0,
                "source": "Baseline estimate"
            }

        total_points = len(coordinates)
        if total_points <= num_samples:
            sampled_coords = coordinates
        else:
            step = (total_points - 1) / (num_samples - 1)
            sampled_coords = [coordinates[int(round(i * step))] for i in range(num_samples)]

        lat_list = [round(c[0], 4) for c in sampled_coords]
        lon_list = [round(c[1], 4) for c in sampled_coords]

        lat_str = ",".join(str(lat) for lat in lat_list)
        lon_str = ",".join(str(lon) for lon in lon_list)

        url = (
            f"{OPEN_METEO_AIR_QUALITY_URL}"
            f"?latitude={lat_str}&longitude={lon_str}"
            f"&current=pm10,pm2_5,nitrogen_dioxide,ozone,us_aqi"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CleanRouteAI/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status != 200:
                    raise RuntimeError(f"Open-Meteo HTTP {response.status}")
                raw_data = json.loads(response.read().decode("utf-8"))

            items = raw_data if isinstance(raw_data, list) else [raw_data]

            aqi_vals = []
            pm25_vals = []
            pm10_vals = []
            no2_vals = []
            ozone_vals = []

            for item in items:
                cur = item.get("current", {})
                aqi = cur.get("us_aqi")
                pm25 = cur.get("pm2_5")
                pm10 = cur.get("pm10")
                no2 = cur.get("nitrogen_dioxide")
                o3 = cur.get("ozone")

                if aqi is not None:
                    aqi_vals.append(float(aqi))
                elif pm25 is not None:
                    aqi_vals.append(min(500.0, float(pm25) * 2.1))

                if pm25 is not None:
                    pm25_vals.append(float(pm25))
                if pm10 is not None:
                    pm10_vals.append(float(pm10))
                if no2 is not None:
                    no2_vals.append(float(no2))
                if o3 is not None:
                    ozone_vals.append(float(o3))

            avg_aqi = round(sum(aqi_vals) / len(aqi_vals), 1) if aqi_vals else 60.0
            avg_pm25 = round(sum(pm25_vals) / len(pm25_vals), 1) if pm25_vals else 18.0
            avg_pm10 = round(sum(pm10_vals) / len(pm10_vals), 1) if pm10_vals else 32.0
            avg_no2 = round(sum(no2_vals) / len(no2_vals), 1) if no2_vals else 14.0
            avg_ozone = round(sum(ozone_vals) / len(ozone_vals), 1) if ozone_vals else 26.0

            return {
                "average_aqi": avg_aqi,
                "pm25": avg_pm25,
                "pm10": avg_pm10,
                "no2": avg_no2,
                "ozone": avg_ozone,
                "aqi_category": get_aqi_category(avg_aqi),
                "estimated_pollution_exposure": get_exposure_level(avg_aqi),
                "points_sampled": len(items),
                "source": "Open-Meteo Air Quality"
            }
        except Exception as err:
            logger.warning(f"Failed to batch sample route air quality ({err}); using baseline fallback.")
            return {
                "average_aqi": 62.0,
                "pm25": 17.5,
                "pm10": 29.0,
                "no2": 13.0,
                "ozone": 25.0,
                "aqi_category": "Moderate",
                "estimated_pollution_exposure": "Moderate estimated pollution exposure",
                "points_sampled": len(sampled_coords),
                "source": "Estimated baseline (Atmospheric API unavailable)"
            }
