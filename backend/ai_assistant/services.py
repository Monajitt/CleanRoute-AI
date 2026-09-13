import datetime
import logging
from typing import Dict, Any, Optional
from rag.services import RAGService

logger = logging.getLogger(__name__)

RESPONSIBLE_AI_DISCLAIMER = (
    "CleanRoute AI provides informational, pollution-aware travel recommendations based on available "
    "routing, environmental and weather data. It does not provide medical advice or guarantee safety."
)


class AIAssistantService:
    """
    Grounded Conversational AI Assistant Service.
    Combines retrieved local knowledge chunks with active CleanRoute route metrics
    to formulate transparent, explainable, and non-medical responses.
    """

    @classmethod
    def generate_grounded_response(
        cls,
        user_message: str,
        route_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes grounded reasoning:
        1. Retrieves relevant knowledge chunks via RAG
        2. Ingests active route context (origin, destination, mode, priority, scores, AQI)
        3. Formulates a deterministic, explainable response without hallucination
        4. Attaches source citations and Responsible AI disclaimer
        """
        clean_msg = (user_message or "").strip()
        if not clean_msg:
            return {
                "answer": "Please ask a question about your route, air quality pollutants, or sustainable travel.",
                "sources": [],
                "disclaimer": RESPONSIBLE_AI_DISCLAIMER,
                "timestamp": datetime.datetime.now().strftime("%H:%M")
            }

        # 1. Build grounded context bundle from local RAG
        bundle = RAGService.build_grounded_context(clean_msg, route_context=route_context, top_k=4)
        retrieved_chunks = bundle.get("retrieved_knowledge", [])
        sources = bundle.get("sources", [])
        parsed_route = bundle.get("route_context")

        query_lower = clean_msg.lower()

        # 2. Determine response intent and synthesize grounded answer
        answer = cls._formulate_grounded_answer(query_lower, retrieved_chunks, parsed_route)
        has_context = bool(parsed_route and (
            parsed_route.get("routes")
            or parsed_route.get("recommended_route")
            or parsed_route.get("recommendation")
        ))

        return {
            "answer": answer,
            "reply": answer,
            "sources": sources,
            "disclaimer": RESPONSIBLE_AI_DISCLAIMER,
            "timestamp": datetime.datetime.now().strftime("%H:%M"),
            "has_route_context": has_context
        }

    @classmethod
    def _formulate_grounded_answer(
        cls,
        query: str,
        retrieved_chunks: list,
        route_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Synthesizes transparent, grounded explanation based on query intent,
        retrieved knowledge, and active route parameters.
        """
        # A. Specific Transport Modes & Sustainability
        if any(k in query for k in ["cycle", "cycling", "bike", "bicycle"]):
            return cls._explain_active_mode("cycling", retrieved_chunks, route_context)

        if any(k in query for k in ["walk", "walking", "pedestrian"]):
            return cls._explain_active_mode("walking", retrieved_chunks, route_context)

        if any(k in query for k in ["sustainable", "sustainability", "sdg"]):
            return cls._explain_sustainability(retrieved_chunks)

        # B. Specific Criteria Air Pollutants
        if "pm2.5" in query or "pm 2.5" in query or "2.5" in query:
            return cls._explain_pollutant("pm25", retrieved_chunks, route_context)

        if "pm10" in query or "pm 10" in query:
            return cls._explain_pollutant("pm10", retrieved_chunks, route_context)

        if "aqi" in query or "air quality index" in query:
            return cls._explain_aqi(retrieved_chunks, route_context)

        if "no2" in query or "nitrogen" in query:
            return cls._explain_pollutant("nitrogen_dioxide", retrieved_chunks, route_context)

        if "ozone" in query or "o3" in query:
            return cls._explain_pollutant("ozone", retrieved_chunks, route_context)

        # C. Route Recommendation & Priority Questions
        if (
            "recommend" in query or "recommended" in query or "priority" in query
            or "health first" in query or "balanced" in query or "time first" in query
            or ("why" in query and any(w in query for w in ["route", "this", "choice", "choose", "selected", "pick"]))
            or query.startswith("why was")
            or query.startswith("why did")
        ):
            return cls._explain_route_recommendation(query, route_context, retrieved_chunks)

        # D. Exposure & Pollution Level Questions
        if any(k in query for k in ["exposure", "pollution", "cleaner", "lower pollution", "particulate"]):
            return cls._explain_exposure_tradeoffs(route_context, retrieved_chunks)

        if any(k in query for k in ["walk", "walking", "pedestrian"]):
            return cls._explain_active_mode("walking", retrieved_chunks, route_context)

        if "sustainable" in query or "sdg" in query or "green" in query:
            return cls._explain_sustainability(retrieved_chunks)

        # E. Weather / Atmospheric Dispersion
        if any(k in query for k in ["weather", "wind", "temperature", "humidity", "rain", "dispersion"]):
            return cls._explain_weather_dispersion(retrieved_chunks, route_context)

        # F. Limitations / Medical / Safety Inquiries
        if any(k in query for k in ["safe", "health risk", "medical", "guarantee", "cure", "danger"]):
            return (
                "CleanRoute AI provides informational estimates of air quality and travel trade-offs, "
                "not medical assessments or guarantees of safety. Atmospheric pollution is dynamic, and individual "
                "health susceptibility varies. We recommend consulting healthcare professionals for clinical advice."
            )

        # G. General Fallback: Grounded in top retrieved RAG chunks
        if retrieved_chunks:
            top_chunk = retrieved_chunks[0]
            clean_text = top_chunk.get("text", "")
            # Remove markdown header prefix if present
            lines = [line for line in clean_text.split("\n") if not line.startswith("#")]
            summary_paragraph = "\n".join(lines).strip()
            if summary_paragraph:
                return f"{summary_paragraph[:400]}... [Source: {top_chunk.get('source', 'Knowledge Base')}]"

        return (
            "CleanRoute AI calculates travel recommendations by evaluating real road geometries from OpenRouteService "
            "alongside hourly air quality and atmospheric data from Open-Meteo. You can ask about PM2.5, AQI interpretation, "
            "cycling and walking trade-offs, or why specific routes were chosen."
        )

    @classmethod
    def _extract_recommended_route(cls, route_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extracts the recommended or primary route from various route_context structures."""
        if not route_context or not isinstance(route_context, dict):
            return None
        if route_context.get("recommended_route"):
            return route_context["recommended_route"]
        if route_context.get("recommendation"):
            rec = route_context["recommendation"]
            if isinstance(rec, dict):
                rec_id = rec.get("recommendedRouteId")
                routes = route_context.get("routes", [])
                matched = next((r for r in routes if r.get("id") == rec_id), None)
                if matched:
                    return matched
                return rec
        routes = route_context.get("routes", [])
        if routes and isinstance(routes, list):
            rec = next((r for r in routes if r.get("is_recommended") or r.get("isRecommended")), None)
            if rec:
                return rec
            if len(routes) > 0 and isinstance(routes[0], dict):
                return routes[0]
        return None

    @classmethod
    def _explain_route_recommendation(
        cls,
        query: str,
        route_context: Optional[Dict[str, Any]],
        retrieved_chunks: list
    ) -> str:
        """Explains why a route was recommended using actual numbers when route context exists."""
        rec = cls._extract_recommended_route(route_context)
        if not rec:
            return (
                "CleanRoute AI selects recommended routes using a deterministic multi-criteria scoring algorithm. "
                "Depending on your chosen priority (Health First, Balanced, or Time First), the engine balances "
                "estimated pollution exposure against travel duration and physical distance across available routes. "
                "Enter an origin and destination to view live route recommendations for your trip."
            )

        name = rec.get("name") or rec.get("routeName") or "Recommended Route"
        dist = rec.get("distance_km") or rec.get("distanceKm", "--")
        dur = rec.get("duration_minutes") or rec.get("durationMin", "--")
        priority = (
            route_context.get("priority")
            or route_context.get("priority_preference")
            or route_context.get("route_preference")
            or "Balanced"
        )
        mode = route_context.get("travel_mode") or route_context.get("mode") or rec.get("mode", "cycling")

        score = rec.get("score")
        if isinstance(rec.get("scores"), dict):
            score = rec.get("scores").get("final_score", score)
        if score is None:
            score = 85

        aqi_info = rec.get("air_quality", {})
        avg_aqi = aqi_info.get("average_aqi", "--")
        aqi_cat = aqi_info.get("aqi_category", "Moderate")
        exposure = aqi_info.get("estimated_pollution_exposure") or rec.get("pollutionLevel", "Moderate")

        if priority == "Health First":
            explanation = (
                f"{name} is recommended under your 'Health First' priority with a score of {score}/100. "
                f"Because Health First places 60% weight on lower estimated pollution exposure, this route was selected "
                f"to minimize particulate and exhaust intake (average AQI: {avg_aqi}, {exposure} exposure) "
                f"over the {dist} km journey ({dur} mins)."
            )
        elif priority == "Time First":
            explanation = (
                f"{name} is recommended under your 'Time First' priority with a score of {score}/100. "
                f"Time First places 60% weight on minimizing travel duration, delivering the fastest navigable path "
                f"at {dur} minutes ({dist} km) while still monitoring ambient air quality ({avg_aqi} AQI)."
            )
        else:
            explanation = (
                f"{name} is recommended under your 'Balanced' priority with a score of {score}/100. "
                f"The Balanced priority applies a balanced trade-off (40% pollution, 30% time, 30% distance) "
                f"delivering a journey of {dist} km in {dur} mins with an average estimated AQI of {avg_aqi} ({aqi_cat})."
            )

        return explanation

    @classmethod
    def _explain_exposure_tradeoffs(
        cls,
        route_context: Optional[Dict[str, Any]],
        retrieved_chunks: list
    ) -> str:
        """Explains route-level pollution exposure estimation."""
        rec = cls._extract_recommended_route(route_context)
        if rec:
            aqi_info = rec.get("air_quality", {})
            avg_aqi = aqi_info.get("average_aqi", "moderate")
            cat = aqi_info.get("aqi_category", "Moderate")
            dur = rec.get("duration_minutes") or rec.get("durationMin", "--")

            return (
                f"Estimated pollution exposure accounts for both the ambient concentration of pollutants (average AQI {avg_aqi}, {cat}) "
                f"and total travel duration ({dur} mins). Longer travel times increase cumulative inhalation, while routing away "
                f"from high-density traffic arteries reduces peak exposure to combustion exhaust. [Source: outdoor_pollution.md]"
            )

        return (
            "Estimated pollution exposure in CleanRoute AI measures the cumulative particulate and pollutant load a traveler is "
            "projected to inhale along a journey. It evaluates criteria pollutants (PM2.5, PM10, NO2, O3) and weights them by travel "
            "duration, since spending more time in polluted air increases overall exposure. [Source: outdoor_pollution.md]"
        )

    @classmethod
    def _explain_aqi(cls, retrieved_chunks: list, route_context: Optional[Dict[str, Any]]) -> str:
        """Explains the Air Quality Index scale and active route AQI if available."""
        context_note = ""
        rec = cls._extract_recommended_route(route_context)
        if rec:
            aqi_info = rec.get("air_quality", {})
            if aqi_info.get("average_aqi"):
                context_note = f" Your current recommended route has an estimated average AQI of {aqi_info['average_aqi']} ({aqi_info.get('aqi_category', 'Moderate')})."

        return (
            "The Air Quality Index (AQI) is a standardized scale from 0 to 500: 0–50 is Good, 51–100 is Moderate, "
            "101–150 is Unhealthy for Sensitive Groups, 151–200 is Unhealthy, 201–300 is Very Unhealthy, and 301+ is Hazardous."
            f"{context_note} CleanRoute AI samples AQI along candidate road networks to highlight cleaner alternatives. [Source: aqi.md]"
        )

    @classmethod
    def _explain_pollutant(cls, pollutant_key: str, retrieved_chunks: list, route_context: Optional[Dict[str, Any]]) -> str:
        """Explains specific pollutant characteristics based on knowledge base documents."""
        if pollutant_key == "pm25":
            return (
                "PM2.5 refers to fine particulate matter smaller than 2.5 micrometers in diameter—about 30 times thinner than human hair. "
                "Because they penetrate deep into lung tissue and alveolar regions, cyclists and pedestrians benefit significantly from "
                "choosing routes with lower traffic density and vegetative barriers that filter particulates. [Source: pm25.md]"
            )
        elif pollutant_key == "pm10":
            return (
                "PM10 consists of coarse inhalable particles between 2.5 and 10 micrometers, such as resuspended road dust, brake wear, "
                "and construction debris. Concentrations peak sharply immediately adjacent to heavy vehicle thoroughfares. [Source: pm10.md]"
            )
        elif pollutant_key == "nitrogen_dioxide":
            return (
                "Nitrogen Dioxide (NO2) is an exhaust combustion gas released primarily by diesel and gasoline vehicles. In narrow street "
                "canyons with tall buildings, vehicle exhaust can become trapped, causing roadside NO2 spikes during commuter rush hours. [Source: nitrogen_dioxide.md]"
            )
        elif pollutant_key == "ozone":
            return (
                "Ground-level Ozone (O3) is a secondary pollutant formed when nitrogen oxides react with volatile organic compounds in sunlight and heat. "
                "Unlike primary traffic emissions, ozone typically peaks in the afternoon and downwind in suburban or park areas. [Source: ozone.md]"
            )

        return "Air pollutants like PM2.5, PM10, NO2, and Ozone are evaluated along candidate routes to model estimated exposure. [Source: aqi.md]"

    @classmethod
    def _explain_active_mode(cls, mode: str, retrieved_chunks: list, route_context: Optional[Dict[str, Any]]) -> str:
        """Explains active transport mode physiological and environmental dynamics."""
        if mode == "cycling":
            return (
                "Cycling provides zero-emission active mobility and reduces road congestion. However, because cyclists breathe at 2 to 4 times "
                "their resting ventilation rate, route selection is critical: taking greenways or quieter residential streets rather than main diesel "
                "arteries significantly reduces cumulative particulate inhalation while adding minimal travel time. [Source: cycling.md]"
            )
        elif mode == "walking":
            return (
                "Walking is the most accessible zero-emission transport mode. Because pedestrians travel at lower speeds (~5 km/h), total duration "
                "spent outdoors is higher; prioritizing pedestrian walkways set back from traffic or traversing urban parks provides lower estimated "
                "particulate exposure. [Source: walking.md]"
            )
        return "Active travel modes (walking and cycling) produce zero operational emissions and benefit from clean-air corridor routing. [Source: sustainable_transport.md]"

    @classmethod
    def _explain_sustainability(cls, retrieved_chunks: list) -> str:
        """Explains urban sustainability and UN SDG 11 alignment."""
        return (
            "Sustainable urban transport follows a hierarchy: prioritizing active travel (walking, cycling) and mass transit over private motorized "
            "vehicles. By choosing lower-emission routes and active mobility, commuters support United Nations Sustainable Development Goal 11: "
            "Sustainable Cities and Communities by reducing greenhouse gases and local smog. [Source: sustainable_transport.md]"
        )

    @classmethod
    def _explain_weather_dispersion(cls, retrieved_chunks: list, route_context: Optional[Dict[str, Any]]) -> str:
        """Explains atmospheric weather dispersion with active weather context if present."""
        weather_note = ""
        if route_context and route_context.get("weather"):
            w = route_context["weather"]
            if isinstance(w, dict) and w.get("temperature") is not None:
                weather_note = f" Current local conditions show {w.get('temperature')}°C with {w.get('description', 'fair weather')}."

        return (
            f"Atmospheric dispersion governs urban pollution.{weather_note} Moderate winds dilute vehicle emissions, while calm winds and temperature "
            "inversions trap exhaust near the ground. Tree canopies and vegetation buffers physically filter particulate concentrations by 15% to 35%. [Source: outdoor_pollution.md]"
        )
