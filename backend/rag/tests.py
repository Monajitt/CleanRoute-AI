import os
from django.test import TestCase
from django.conf import settings
from .ingest import KnowledgeBaseIngester, ingest_knowledge_base
from .retriever import KnowledgeRetriever, retrieve_relevant_chunks
from .services import RAGService
from .vector_store import get_vector_store


class RAGPipelineTests(TestCase):
    def setUp(self):
        self.vector_store = get_vector_store()
        self.kb_dir = os.path.join(settings.BASE_DIR, "knowledge_base")

    def test_knowledge_base_files_exist(self):
        """Verify all 10 required knowledge base markdown files exist."""
        expected_files = [
            "air_quality/aqi.md",
            "air_quality/pm25.md",
            "air_quality/pm10.md",
            "air_quality/nitrogen_dioxide.md",
            "air_quality/ozone.md",
            "sustainable_transport/walking.md",
            "sustainable_transport/cycling.md",
            "sustainable_transport/sustainable_transport.md",
            "outdoor_pollution/outdoor_pollution.md",
            "responsible_ai/limitations.md"
        ]
        for rel in expected_files:
            full_path = os.path.join(self.kb_dir, rel)
            self.assertTrue(os.path.exists(full_path), f"Missing KB file: {rel}")

    def test_ingestion_indexes_chunks(self):
        """Verify ingestion reads all documents and chunks them with metadata."""
        res = ingest_knowledge_base(force=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["documents_read"], 10)
        self.assertGreaterEqual(res["chunks_indexed"], 10)

    def test_semantic_retrieval_aqi(self):
        """Verify semantic query retrieves relevant air quality documents."""
        chunks = retrieve_relevant_chunks("What does the Air Quality Index mean?", top_k=3)
        self.assertGreater(len(chunks), 0)
        sources = [c["source"] for c in chunks]
        self.assertIn("aqi.md", sources)

    def test_semantic_retrieval_pm25(self):
        """Verify PM2.5 query retrieves pm25.md."""
        chunks = retrieve_relevant_chunks("Explain fine particulate matter PM2.5 inhalation", top_k=3)
        self.assertGreater(len(chunks), 0)
        sources = [c["source"] for c in chunks]
        self.assertIn("pm25.md", sources)

    def test_semantic_retrieval_cycling(self):
        """Verify cycling query retrieves cycling.md or sustainable_transport.md."""
        chunks = retrieve_relevant_chunks("Why is cycling considered sustainable and healthy?", top_k=3)
        self.assertGreater(len(chunks), 0)
        sources = [c["source"] for c in chunks]
        self.assertTrue(any("cycling.md" in s or "sustainable" in s for s in sources))

    def test_empty_query_returns_empty(self):
        """Verify empty or whitespace query returns empty list without error."""
        self.assertEqual(retrieve_relevant_chunks(""), [])
        self.assertEqual(retrieve_relevant_chunks("   "), [])

    def test_build_grounded_context_without_route(self):
        """Verify build_grounded_context works gracefully when no route context is passed."""
        context = RAGService.build_grounded_context("What is ozone?")
        self.assertIn("retrieved_knowledge", context)
        self.assertIn("sources", context)
        self.assertEqual(context["context_summary"], "No active route journey selected.")
        self.assertIsNone(context["route_context"])

    def test_build_grounded_context_with_route(self):
        """Verify build_grounded_context formats active route parameters."""
        sample_route_context = {
            "origin_name": "Kalyani",
            "destination_name": "Kolkata",
            "travel_mode": "cycling",
            "route_preference": "Health First",
            "routes": [
                {
                    "name": "Route 1",
                    "distance_km": 55.28,
                    "duration_minutes": 189.0,
                    "rank": 1,
                    "recommended": True,
                    "air_quality": {
                        "average_aqi": 64.0,
                        "aqi_category": "Moderate",
                        "estimated_pollution_exposure": "Moderate"
                    },
                    "scores": {"final_score": 88.5}
                }
            ],
            "weather": {"temperature": 27.5, "description": "Overcast"}
        }
        context = RAGService.build_grounded_context(
            "Why was this route recommended?",
            route_context=sample_route_context,
            top_k=3
        )
        self.assertIsNotNone(context["route_context"])
        self.assertIn("Kalyani -> Kolkata", context["context_summary"])
        self.assertIn("Cycling", context["context_summary"])
        self.assertIn("Health First", context["context_summary"])
        self.assertIn("55.28 km", context["context_summary"])
