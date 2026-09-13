import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .services import AIAssistantService, RESPONSIBLE_AI_DISCLAIMER


class AIAssistantTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.chat_url = reverse("chat-api")

        self.sample_route_context = {
            "origin_name": "Kalyani",
            "destination_name": "Kolkata",
            "travel_mode": "cycling",
            "route_preference": "Health First",
            "routes": [
                {
                    "name": "Route 1 (Primary Route)",
                    "distance_km": 55.28,
                    "duration_minutes": 189.0,
                    "rank": 1,
                    "recommended": True,
                    "scores": {"final_score": 88.5},
                    "air_quality": {
                        "average_aqi": 64.0,
                        "aqi_category": "Moderate",
                        "estimated_pollution_exposure": "Moderate"
                    }
                }
            ],
            "weather": {"temperature": 27.5, "description": "Overcast"}
        }

    def test_get_chat_service_info(self):
        """GET /api/chat/ returns service metadata and suggested prompts."""
        response = self.client.get(self.chat_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("suggested_questions", data["data"])
        self.assertEqual(data["data"]["disclaimer"], RESPONSIBLE_AI_DISCLAIMER)

    def test_post_empty_message_fails(self):
        """POST /api/chat/ with empty message returns 400 Bad Request."""
        response = self.client.post(self.chat_url, {"message": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_missing_message_fails(self):
        """POST /api/chat/ with missing message returns 400 Bad Request."""
        response = self.client.post(self.chat_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ask_why_recommended_with_context(self):
        """Verify recommendation query uses actual route context values."""
        payload = {
            "message": "Why was this route recommended?",
            "route_context": self.sample_route_context
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]

        self.assertIn("Route 1", data["answer"])
        self.assertIn("Health First", data["answer"])
        self.assertIn("55.28", data["answer"])
        self.assertIn("189", data["answer"])
        self.assertEqual(data["disclaimer"], RESPONSIBLE_AI_DISCLAIMER)

    def test_ask_why_recommended_without_context(self):
        """Verify recommendation query works gracefully when no route context is passed."""
        payload = {
            "message": "Why was this route recommended?"
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("deterministic multi-criteria", data["answer"])
        self.assertEqual(data["disclaimer"], RESPONSIBLE_AI_DISCLAIMER)

    def test_ask_what_is_pm25(self):
        """Verify PM2.5 query returns grounded explanation citing pm25.md."""
        payload = {
            "message": "What does PM2.5 mean?"
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("2.5 micrometers", data["answer"])
        sources = [s["source"] for s in data["sources"]]
        self.assertIn("pm25.md", sources)

    def test_ask_what_is_aqi(self):
        """Verify AQI query explains standard categories citing aqi.md."""
        payload = {
            "message": "What does the AQI mean?"
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("0–50 is Good", data["answer"])
        sources = [s["source"] for s in data["sources"]]
        self.assertIn("aqi.md", sources)

    def test_ask_why_cycling_sustainable(self):
        """Verify cycling query explains active mobility benefits citing cycling.md."""
        payload = {
            "message": "Why is cycling considered sustainable?"
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("zero-emission", data["answer"])
        sources = [s["source"] for s in data["sources"]]
        self.assertTrue(any("cycling.md" in s or "sustainable" in s for s in sources))

    def test_safety_guarantee_inquiry_responsible_disclaimer(self):
        """Verify medical/safety guarantee queries reject claims and provide non-medical boundaries."""
        payload = {
            "message": "Is this route guaranteed safe for my health?"
        }
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("not medical assessments or guarantees of safety", data["answer"])
        self.assertEqual(data["disclaimer"], RESPONSIBLE_AI_DISCLAIMER)
