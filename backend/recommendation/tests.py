from django.test import TestCase
from rest_framework.test import APIClient
from .services import RecommendationService, normalize_preference


class RecommendationServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_normalize_min_better_varying(self):
        vals = [10.0, 20.0, 30.0]
        norm = RecommendationService.normalize_min_better(vals)
        self.assertEqual(norm, [100.0, 50.0, 0.0])

    def test_normalize_min_better_identical(self):
        vals = [25.0, 25.0]
        norm = RecommendationService.normalize_min_better(vals)
        self.assertEqual(norm, [100.0, 100.0])

    def test_single_route_fallback(self):
        routes = [{
            "id": 1,
            "name": "Route 1",
            "distance_km": 5.2,
            "duration_minutes": 18.0,
            "air_quality": {"average_aqi": 45.0}
        }]
        ranked = RecommendationService.score_and_rank_routes(routes, preference="health_first")
        self.assertEqual(len(ranked), 1)
        self.assertTrue(ranked[0]["is_recommended"])
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertIn("lower estimated pollution exposure", ranked[0]["why_recommended"])

    def test_priority_switching_behavior(self):
        # Route A: Fast & direct, but heavily polluted
        route_a = {
            "id": 1,
            "name": "Arterial Highway",
            "distance_km": 10.0,
            "duration_minutes": 15.0,
            "air_quality": {"average_aqi": 160.0}
        }
        # Route B: Longer detour, but clean greenway
        route_b = {
            "id": 2,
            "name": "Green Corridor",
            "distance_km": 12.5,
            "duration_minutes": 22.0,
            "air_quality": {"average_aqi": 35.0}
        }
        routes = [route_a, route_b]

        # 1. Under Health First: Route B (clean air) must win
        ranked_health = RecommendationService.score_and_rank_routes(routes, preference="health_first")
        self.assertEqual(ranked_health[0]["name"], "Green Corridor")
        self.assertTrue(ranked_health[0]["is_recommended"])
        self.assertEqual(ranked_health[0]["rank"], 1)
        self.assertIn("lower estimated pollution exposure", ranked_health[0]["why_recommended"])

        # 2. Under Time First: Route A (fastest) must win
        ranked_time = RecommendationService.score_and_rank_routes(routes, preference="time_first")
        self.assertEqual(ranked_time[0]["name"], "Arterial Highway")
        self.assertTrue(ranked_time[0]["is_recommended"])
        self.assertEqual(ranked_time[0]["rank"], 1)
        self.assertIn("fastest available navigable route", ranked_time[0]["why_recommended"])

        # 3. Under Balanced: Check wording
        ranked_bal = RecommendationService.score_and_rank_routes(routes, preference="balanced")
        self.assertIn("balance between estimated pollution exposure", ranked_bal[0]["why_recommended"])

    def test_normalize_preference_aliases(self):
        self.assertEqual(normalize_preference("Health First"), "health_first")
        self.assertEqual(normalize_preference("time-first"), "time_first")
        self.assertEqual(normalize_preference("Balanced Priority"), "balanced")
        self.assertEqual(normalize_preference(None), "balanced")

    def test_route_scoring_api_view(self):
        routes = [
            {
                "id": 1,
                "name": "Route Fast",
                "distance_km": 5.0,
                "duration_minutes": 10.0,
                "air_quality": {"average_aqi": 120.0}
            },
            {
                "id": 2,
                "name": "Route Clean",
                "distance_km": 6.5,
                "duration_minutes": 14.0,
                "air_quality": {"average_aqi": 25.0}
            }
        ]

        # Test POST /api/recommendation/score/ with Health First
        res = self.client.post("/api/recommendation/score/", {
            "routes": routes,
            "preference": "health_first"
        }, format="json")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["recommended_route"]["name"], "Route Clean")

        # Test with Time First
        res_time = self.client.post("/api/recommendation/score/", {
            "routes": routes,
            "preference": "time_first"
        }, format="json")
        self.assertEqual(res_time.status_code, 200)
        data_time = res_time.json()["data"]
        self.assertEqual(data_time["recommended_route"]["name"], "Route Fast")

        # Test empty routes validation
        res_empty = self.client.post("/api/recommendation/score/", {"routes": []}, format="json")
        self.assertEqual(res_empty.status_code, 400)

    def test_deterministic_tie_breaking_order(self):
        # Two routes constructed to test tie-breaking
        # When scores tie, lower pollution exposure must win over lower duration
        routes = [
            {
                "id": 1,
                "name": "Route Lower Pollution",
                "distance_km": 10.0,
                "duration_minutes": 20.0,
                "air_quality": {"average_aqi": 30.0}
            },
            {
                "id": 2,
                "name": "Route Shorter Duration",
                "distance_km": 10.0,
                "duration_minutes": 20.0,
                "air_quality": {"average_aqi": 60.0}
            }
        ]
        # In balanced mode, normalized distance and duration are equal (100.0 each)
        # Route 1 has lower pollution (30 < 60), so it must be ranked #1
        ranked = RecommendationService.score_and_rank_routes(routes, preference="balanced")
        self.assertEqual(ranked[0]["name"], "Route Lower Pollution")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertTrue(ranked[0]["is_recommended"])
