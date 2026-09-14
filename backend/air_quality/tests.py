from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from .services import AirQualityService, get_aqi_category, get_exposure_level


class AirQualityCategoryTests(TestCase):
    def test_aqi_categories(self):
        self.assertEqual(get_aqi_category(25), "Good")
        self.assertEqual(get_aqi_category(50), "Good")
        self.assertEqual(get_aqi_category(75), "Moderate")
        self.assertEqual(get_aqi_category(100), "Moderate")
        self.assertEqual(get_aqi_category(125), "Unhealthy for Sensitive Groups")
        self.assertEqual(get_aqi_category(150), "Unhealthy for Sensitive Groups")
        self.assertEqual(get_aqi_category(180), "Unhealthy")
        self.assertEqual(get_aqi_category(250), "Very Unhealthy")
        self.assertEqual(get_aqi_category(350), "Hazardous")
        self.assertEqual(get_aqi_category(None), "Moderate")

    def test_exposure_levels(self):
        self.assertEqual(get_exposure_level(30), "Low estimated pollution exposure")
        self.assertEqual(get_exposure_level(85), "Moderate estimated pollution exposure")
        self.assertEqual(get_exposure_level(130), "Elevated estimated pollution exposure")
        self.assertEqual(get_exposure_level(220), "High estimated pollution exposure")


class AirQualityServiceTests(TestCase):
    def setUp(self):
        AirQualityService.clear_cache()

    def test_sample_route_air_quality_empty_coords(self):
        res = AirQualityService.sample_route_air_quality([])
        self.assertIn("average_aqi", res)
        self.assertIn("pm25", res)
        self.assertIn("aqi_category", res)
        self.assertIn("estimated_pollution_exposure", res)

    @patch("air_quality.services.urllib.request.urlopen")
    def test_get_air_quality_mock(self, mock_urlopen):
        import io
        fake_json = b'{"current":{"us_aqi":45,"pm2_5":11.2,"pm10":22.0,"nitrogen_dioxide":9.5,"ozone":28.0}}'
        mock_response = io.BytesIO(fake_json)
        mock_response.status = 200
        mock_urlopen.return_value = mock_response

        res = AirQualityService.get_air_quality(28.6139, 77.2090)
        self.assertIsNotNone(res)
        self.assertEqual(res["aqi"], 45.0)
        self.assertEqual(res["aqi_category"], "Good")
        self.assertEqual(res["estimated_pollution_exposure"], "Low estimated pollution exposure")


class AirQualityAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('air-quality-current')

    def test_missing_params_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))

    def test_invalid_coords_returns_400(self):
        response = self.client.get(self.url, {"latitude": "invalid", "longitude": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))

    def test_valid_coords_returns_air_quality(self):
        response = self.client.get(self.url, {"latitude": "28.6139", "longitude": "77.2090"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        data = response.data.get("data", {})
        self.assertIn("aqi", data)
        self.assertIn("pm25", data)
        self.assertIn("estimated_pollution_exposure", data)
