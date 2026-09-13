from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import RouteSearch, TravelMode, RoutePreference
from .serializers import RouteSearchSerializer


class RouteSearchModelTests(TestCase):
    def test_create_route_search_instance(self):
        search = RouteSearch.objects.create(
            origin_name="Kalyani",
            destination_name="Kolkata",
            travel_mode=TravelMode.CYCLING,
            route_preference=RoutePreference.BALANCED
        )
        self.assertEqual(search.origin_name, "Kalyani")
        self.assertEqual(search.destination_name, "Kolkata")
        self.assertEqual(search.travel_mode, "cycling")
        self.assertEqual(search.route_preference, "balanced")
        self.assertIsNotNone(search.created_at)
        self.assertIn("Kalyani -> Kolkata", str(search))


class RouteSearchSerializerTests(TestCase):
    def test_valid_serializer_data(self):
        data = {
            "origin_name": "Kalyani University",
            "destination_name": "Railway Station",
            "travel_mode": "cycling",
            "route_preference": "health_first"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_travel_mode_rejected(self):
        data = {
            "origin_name": "Kalyani",
            "destination_name": "Kolkata",
            "travel_mode": "flying",
            "route_preference": "balanced"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("travel_mode", serializer.errors)

    def test_invalid_route_preference_rejected(self):
        data = {
            "origin_name": "Kalyani",
            "destination_name": "Kolkata",
            "travel_mode": "cycling",
            "route_preference": "cheapest"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("route_preference", serializer.errors)

    def test_missing_origin_rejected(self):
        data = {
            "origin_name": "",
            "destination_name": "Kolkata",
            "travel_mode": "cycling",
            "route_preference": "balanced"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("origin_name", serializer.errors)

    def test_missing_destination_rejected(self):
        data = {
            "origin_name": "Kalyani",
            "destination_name": "",
            "travel_mode": "cycling",
            "route_preference": "balanced"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("destination_name", serializer.errors)

    def test_identical_origin_and_destination_rejected(self):
        data = {
            "origin_name": "Kalyani",
            "destination_name": "kalyani",
            "travel_mode": "walking",
            "route_preference": "time_first"
        }
        serializer = RouteSearchSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class RouteSearchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('route-search-create')

    def test_successful_route_search_creation(self):
        payload = {
            "origin_name": "Kalyani",
            "destination_name": "Kolkata",
            "travel_mode": "cycling",
            "route_preference": "health_first"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("success"))
        data = response.data.get("data", {})
        self.assertEqual(data.get("origin_name"), "Kalyani")
        self.assertEqual(data.get("destination_name"), "Kolkata")
        self.assertEqual(RouteSearch.objects.count(), 1)

    def test_bad_request_on_empty_fields(self):
        payload = {
            "origin_name": "",
            "destination_name": "Kolkata"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertEqual(RouteSearch.objects.count(), 0)

    def test_direct_coordinates_nested_payload(self):
        payload = {
            "origin": {
                "name": "Delhi",
                "latitude": 28.6328027,
                "longitude": 77.2197713
            },
            "destination": {
                "name": "Kolkata",
                "latitude": 22.5726459,
                "longitude": 88.3638953
            },
            "travel_mode": "cycling",
            "priority": "balanced"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("success"))
        data = response.data.get("data", {})
        self.assertEqual(data.get("origin", {}).get("name"), "Delhi")
        self.assertEqual(data.get("destination", {}).get("name"), "Kolkata")
        self.assertGreater(len(data.get("routes", [])), 0)

    def test_unresolvable_location_returns_400_with_message(self):
        payload = {
            "origin_name": "xyznonexistentlocation99999",
            "destination_name": "Kolkata",
            "travel_mode": "cycling"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        msg = response.data.get("error", {}).get("message", "")
        self.assertIn("Location not found. Please select a location from the suggestions.", msg)
