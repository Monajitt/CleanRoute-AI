from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .services import WeatherService, WMO_WEATHER_CODES


class WeatherServiceTests(TestCase):
    def test_weather_description_known_code(self):
        desc = WeatherService.get_weather_description(0)
        self.assertEqual(desc["description"], "Clear sky")
        self.assertEqual(desc["icon"], "☀️")

    def test_weather_description_partly_cloudy(self):
        desc = WeatherService.get_weather_description(2)
        self.assertEqual(desc["description"], "Partly cloudy")
        self.assertEqual(desc["icon"], "⛅")

    def test_weather_description_unknown_code_fallback(self):
        desc = WeatherService.get_weather_description(999)
        self.assertIn("Unknown", desc["description"])
        self.assertEqual(desc["icon"], "⛅")


class WeatherAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('weather-current')

    def test_missing_coordinates_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))

    def test_invalid_coordinates_returns_400(self):
        response = self.client.get(self.url, {"latitude": "invalid", "longitude": "88.43"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))

    def test_weather_with_browser_accept_header(self):
        response = self.client.get(self.url, {"latitude": "invalid", "longitude": "88.43"}, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['Content-Type'], 'application/json')

