import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Deterministic Multi-Criteria Weights defined by Phase 2 & Phase 4 Specifications
PRIORITY_WEIGHTS = {
    "health_first": {"pollution": 0.60, "time": 0.20, "distance": 0.20},
    "balanced": {"pollution": 0.40, "time": 0.30, "distance": 0.30},
    "time_first": {"pollution": 0.20, "time": 0.60, "distance": 0.20},
}


def normalize_preference(pref: str) -> str:
    """Normalizes any priority string variant to standard canonical key."""
    cleaned = (pref or "balanced").lower().strip().replace(" ", "_").replace("-", "_")
    if cleaned in PRIORITY_WEIGHTS:
        return cleaned
    if "health" in cleaned:
        return "health_first"
    if "time" in cleaned or "speed" in cleaned or "fast" in cleaned:
        return "time_first"
    return "balanced"


class RecommendationService:
    """
    Deterministic multi-criteria route ranking engine.
    Applies min-max normalization and mathematically weights:
    - Estimated route pollution exposure
    - Travel duration
    - Road distance
    """

    @staticmethod
    def normalize_min_better(values: List[float]) -> List[float]:
        """
        Normalizes metrics where lower is better (shorter time, shorter distance, lower pollution).
        Returns normalized scores on a 0.0 to 100.0 scale.
        If all values are equal, returns 100.0 for all.
        """
        if not values:
            return []
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return [100.0 for _ in values]
        return [round(100.0 * (max_v - v) / (max_v - min_v), 2) for v in values]

    @classmethod
    def score_and_rank_routes(cls, routes: List[Dict[str, Any]], preference: str = "balanced") -> List[Dict[str, Any]]:
        """
        Evaluates and ranks candidate route alternatives deterministically.
        """
        if not routes:
            return []

        # Single-route fallback
        if len(routes) == 1:
            r = dict(routes[0])
            r["scores"] = {
                "pollution_score": 85.0,
                "time_score": 85.0,
                "distance_score": 85.0,
                "final_score": 85.0
            }
            r["sub_scores"] = r["scores"]
            r["score"] = 85.0
            r["overall_score"] = 85.0
            r["rank"] = 1
            r["is_recommended"] = True
            pref_key = normalize_preference(preference)
            if pref_key == "health_first":
                r["why_recommended"] = (
                    "Recommended for Health First because this route has lower estimated pollution exposure under the selected priority."
                )
            elif pref_key == "time_first":
                r["why_recommended"] = (
                    "Recommended for Time First because it provides the fastest available navigable route under the selected priority."
                )
            else:
                r["why_recommended"] = (
                    "Recommended for Balanced priority because it provides a balance between estimated pollution exposure, travel time, and distance."
                )
            return [r]

        pref_key = normalize_preference(preference)
        weights = PRIORITY_WEIGHTS[pref_key]

        durations = [float(r.get("duration_minutes") or 0.0) for r in routes]
        distances = [float(r.get("distance_km") or 0.0) for r in routes]

        # Extract pollution exposure metrics from route air_quality object
        pollutions = []
        has_pollution = False
        for r in routes:
            aq = r.get("air_quality") or {}
            aqi = aq.get("average_aqi")
            if aqi is not None:
                has_pollution = True
                pollutions.append(float(aqi))
            else:
                pollutions.append(50.0)

        # Rebalance weights dynamically if pollution data is completely missing
        if not has_pollution:
            effective_w_poll = 0.0
            effective_w_time = round(weights["time"] / (weights["time"] + weights["distance"]), 2)
            effective_w_dist = round(weights["distance"] / (weights["time"] + weights["distance"]), 2)
        else:
            effective_w_poll = weights["pollution"]
            effective_w_time = weights["time"]
            effective_w_dist = weights["distance"]

        norm_time = cls.normalize_min_better(durations)
        norm_dist = cls.normalize_min_better(distances)
        norm_poll = cls.normalize_min_better(pollutions)

        scored_routes = []
        for i, r in enumerate(routes):
            s_time = norm_time[i]
            s_dist = norm_dist[i]
            s_poll = norm_poll[i]

            raw_score = (effective_w_poll * s_poll) + (effective_w_time * s_time) + (effective_w_dist * s_dist)
            bounded_score = round(max(10.0, min(99.0, raw_score)), 1)

            r_copy = dict(r)
            r_copy["scores"] = {
                "pollution_score": round(s_poll, 1),
                "time_score": round(s_time, 1),
                "distance_score": round(s_dist, 1),
                "final_score": bounded_score
            }
            r_copy["sub_scores"] = r_copy["scores"]
            r_copy["score"] = bounded_score
            r_copy["overall_score"] = bounded_score
            scored_routes.append(r_copy)

        # Deterministic sort: 1. highest score, 2. lowest pollution exposure, 3. lowest duration, 4. lowest distance, id
        scored_routes.sort(
            key=lambda x: (
                -x["scores"]["final_score"],
                float((x.get("air_quality") or {}).get("average_aqi") or x.get("aqi") or 50.0),
                float(x.get("duration_minutes") or 0.0),
                float(x.get("distance_km") or 0.0),
                x.get("id", 0)
            )
        )

        for rank, r in enumerate(scored_routes, start=1):
            r["rank"] = rank
            is_rec = (rank == 1)
            r["is_recommended"] = is_rec
            dur = r.get("duration_minutes")
            dist = r.get("distance_km")
            score = r["scores"]["final_score"]

            if is_rec:
                if pref_key == "health_first":
                    r["why_recommended"] = (
                        "Recommended for Health First because this route has lower estimated pollution exposure under the selected priority."
                    )
                elif pref_key == "time_first":
                    r["why_recommended"] = (
                        "Recommended for Time First because it provides the fastest available navigable route under the selected priority."
                    )
                else:
                    r["why_recommended"] = (
                        "Recommended for Balanced priority because it provides a balance between estimated pollution exposure, travel time, and distance."
                    )
            else:
                r["why_recommended"] = (
                    f"Alternative route (rank #{rank}, Route Match: {score}/100). "
                    f"Covers {dist} km in {dur} mins."
                )

        return scored_routes
