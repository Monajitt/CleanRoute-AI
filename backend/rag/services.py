import logging
from typing import List, Dict, Any, Optional
from .retriever import retrieve_relevant_chunks

logger = logging.getLogger(__name__)


class RAGService:
    """
    High-level RAG orchestration service: retrieves relevant knowledge base context
    and bundles it with active CleanRoute route context.
    """

    @staticmethod
    def retrieve_relevant_context(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most relevant knowledge base chunks for a given question.
        """
        return retrieve_relevant_chunks(question, top_k=top_k)

    @staticmethod
    def build_grounded_context(
        question: str,
        route_context: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Constructs a unified, structured grounded context package combining:
        1. Retrieved knowledge chunks from local vector store
        2. Parsed current CleanRoute route metrics and environmental parameters
        """
        retrieved_chunks = retrieve_relevant_chunks(question, top_k=top_k)

        # Extract unique sources for citations
        sources = []
        seen_sources = set()
        for chunk in retrieved_chunks:
            src = chunk.get("source")
            if src and src not in seen_sources:
                seen_sources.add(src)
                sources.append({
                    "title": chunk.get("title", src),
                    "source": src,
                    "topic": chunk.get("topic", "general")
                })

        # Process and normalize route context
        parsed_context = None
        context_summary_lines = []

        if route_context and isinstance(route_context, dict):
            origin = route_context.get("origin_name") or route_context.get("origin")
            if isinstance(origin, dict):
                origin = origin.get("name") or origin.get("display_name")

            destination = route_context.get("destination_name") or route_context.get("destination")
            if isinstance(destination, dict):
                destination = destination.get("name") or destination.get("display_name")

            mode = route_context.get("travel_mode") or route_context.get("mode") or "cycling"
            priority = (
                route_context.get("priority_preference")
                or route_context.get("priority")
                or route_context.get("route_preference")
                or route_context.get("preference")
                or "Balanced"
            )

            routes = route_context.get("routes", [])
            recommended_route = route_context.get("recommended_route")
            if not recommended_route and routes:
                for r in routes:
                    if r.get("recommended") is True or r.get("is_recommended") is True or r.get("isRecommended") is True or r.get("rank") == 1:
                        recommended_route = r
                        break
            if not recommended_route and routes:
                recommended_route = routes[0]

            weather = route_context.get("weather", {})

            parsed_context = {
                "origin": origin,
                "destination": destination,
                "travel_mode": mode,
                "priority": priority,
                "recommended_route": recommended_route,
                "all_routes_count": len(routes),
                "weather": weather
            }

            if origin and destination:
                context_summary_lines.append(f"Journey: {origin} -> {destination}")
            context_summary_lines.append(f"Travel Mode: {mode.title()}")
            context_summary_lines.append(f"Selected Priority: {priority}")

            if recommended_route:
                name = recommended_route.get("name", "Primary Route")
                dist = recommended_route.get("distance_km") or recommended_route.get("distanceKm")
                dur = recommended_route.get("duration_minutes") or recommended_route.get("durationMin")
                score = recommended_route.get("score")
                if isinstance(recommended_route.get("scores"), dict):
                    score = recommended_route["scores"].get("final_score", score)

                aqi_info = recommended_route.get("air_quality", {})
                avg_aqi = aqi_info.get("average_aqi")
                aqi_cat = aqi_info.get("aqi_category")
                exposure = aqi_info.get("estimated_pollution_exposure") or recommended_route.get("pollutionLevel")

                context_summary_lines.append(f"Recommended Route: {name}")
                if dist is not None:
                    context_summary_lines.append(f"Distance: {dist} km")
                if dur is not None:
                    context_summary_lines.append(f"Duration: {dur} mins")
                if score is not None:
                    context_summary_lines.append(f"Recommendation Score: {score}/100")
                if avg_aqi is not None:
                    context_summary_lines.append(f"Average AQI: {avg_aqi} ({aqi_cat or 'Moderate'})")
                if exposure is not None:
                    context_summary_lines.append(f"Estimated Pollution Exposure: {exposure}")

            if weather and isinstance(weather, dict):
                temp = weather.get("temperature")
                cond = weather.get("description")
                if temp is not None:
                    context_summary_lines.append(f"Weather: {temp}°C, {cond or 'Fair'}")

        return {
            "question": question,
            "retrieved_knowledge": retrieved_chunks,
            "sources": sources,
            "route_context": parsed_context,
            "context_summary": "\n".join(context_summary_lines) if context_summary_lines else "No active route journey selected."
        }
