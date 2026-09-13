from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from .models import GeocodeCache
from .services import GeocodingService


class GeocodeCacheModelTests(TestCase):
    def test_create_geocode_cache_record(self):
        cache_entry = GeocodeCache.objects.create(
            query="kalyani",
            name="Kalyani",
            latitude=22.9749723,
            longitude=88.4345915,
            display_name="Kalyani, Nadia, West Bengal, India"
        )
        self.assertEqual(cache_entry.query, "kalyani")
        self.assertAlmostEqual(cache_entry.latitude, 22.9749723, places=5)
        self.assertAlmostEqual(cache_entry.longitude, 88.4345915, places=5)
        self.assertIn("kalyani", str(cache_entry))


class GeocodingServiceTests(TestCase):
    def test_cached_lookup(self):
        GeocodeCache.objects.create(
            query="kolkata",
            name="Kolkata",
            latitude=22.5726459,
            longitude=88.3638953,
            display_name="Kolkata, West Bengal, India"
        )
        result = GeocodingService.geocode_location("Kolkata")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("cached"))
        self.assertAlmostEqual(result["latitude"], 22.5726459, places=5)

    def test_empty_query_returns_none(self):
        self.assertIsNone(GeocodingService.geocode_location(""))
        self.assertIsNone(GeocodingService.geocode_location("   "))


class GeocodingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('geocode-location')

    def test_missing_location_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))

    def test_geocoding_api_cached_response(self):
        GeocodeCache.objects.create(
            query="kalyani",
            name="Kalyani",
            latitude=22.9749723,
            longitude=88.4345915,
            display_name="Kalyani, Nadia, West Bengal"
        )
        response = self.client.post(self.url, {"location": "Kalyani"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data["data"]["name"], "Kalyani")


class GeocodeSuggestionsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('geocode-suggestions')

    def test_empty_query_returns_empty_list(self):
        response = self.client.get(self.url, {"q": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("data"), [])

    def test_short_query_returns_empty_list(self):
        response = self.client.get(self.url, {"q": "d"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("data"), [])

    def test_valid_query_returns_suggestions(self):
        response = self.client.get(self.url, {"q": "Delhi", "limit": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        data = response.data.get("data", [])
        self.assertIsInstance(data, list)
        if len(data) > 0:
            first = data[0]
            self.assertIn("name", first)
            self.assertIn("latitude", first)
            self.assertIn("longitude", first)
