# CleanRoute AI — Testing & Verification Report

This document details the multi-layered testing strategy and verification results for CleanRoute AI, encompassing unit testing, real-world corridor testing, edge-case failure modes, and automated integration verification.

---

## 1. Test Suite Architecture

CleanRoute AI utilizes a three-tier testing strategy:
1. **Django App Unit Tests**: Tests internal service logic, serializers, models, error conditions, and API endpoints with mocked external APIs.
2. **Real-World Integration Matrix**: End-to-end tests against live Open-Meteo, Photon, and OpenRouteService endpoints across varying geographical scales and transport modalities.
3. **Edge Case & Defensive Validation**: Tests boundary conditions, adversarial prompt attempts, coordinate limits, and invalid parameters.

---

## 2. Unit Testing Breakdown (55 Tests)

All unit tests are executed using Django's test runner:
```bash
cd backend
python manage.py test
```

### Coverage by Application:
| Application Module | Test Count | Key Scenarios Verified |
| :--- | :---: | :--- |
| **`core`** | 3 | System health endpoint (`/api/health/`), database connection ping, JSON formatting. |
| **`geocoding`** | 8 | Photon suggestions parser, Nominatim coordinate extraction, caching, empty string handling, 404 on unresolvable locations. |
| **`routing`** | 12 | ORS profile mapping, alternative route requests, distance-aware algorithm switching (<80km vs >80km), serializer validation, route persistence. |
| **`weather`** | 6 | Open-Meteo weather response parsing, WMO weather code mapping, missing coordinate 400 validation, upstream fallback. |
| **`air_quality`** | 7 | Open-Meteo AQI retrieval, criteria pollutant parsing (PM2.5, PM10, NO2, O3), multi-point route coordinate sampling, exposure level category mapping. |
| **`recommendation`**| 6 | Deterministic multi-criteria scoring, min-max inverted normalization, priority weight vectors (Health First 60/20/20, Balanced 40/30/30, Time First 20/60/20), single-route fallback, deterministic tie-breaking. |
| **`rag`** | 7 | ChromaDB vector store initialization, document chunking, semantic retrieval by cosine distance, relevance scoring. |
| **`ai_assistant`** | 6 | Conversational grounding, route context injection, system instructions compliance, non-medical disclaimer presence. |

---

## 3. Real-World Corridor Matrix Verification

Executed via automated script `scratch/test_real_world_matrix.py`:

```
==================================================
CLEANROUTE AI — REAL WORLD MATRIX TEST SUITE
==================================================

[1] Health Check: Status 200
    Database status: connected, System: success

[2] Geocoding Matrix:
    OK: Delhi -> (28.6664, 77.2169) - Delhi, India
    OK: Kolkata -> (22.5726, 88.3638) - Kolkata, West Bengal, India
    OK: Kalyani -> (22.9749, 88.4345) - Kalyani, West Bengal, India
    OK: Mumbai -> (19.0549, 72.8692) - Mumbai, Maharashtra, India

[3] Environmental APIs (Delhi):
    Weather: 31.8°C, Humidity 63%
    Air Quality: AQI=Moderate, PM2.5 monitored

[4] Urban Corridor Matrix (Delhi CP -> India Gate):
    Returned 3 route option(s).
      - Route 2 (Alternative): Dist=3.58km, Duration=5.4min, Score=99.0, Recommended=True
      - Route 1 (Primary Route): Dist=3.72km, Duration=5.4min, Score=89.2, Recommended=False
      - Route 3 (Alternative): Dist=3.84km, Duration=5.6min, Score=60.0, Recommended=False
    Mode [WALKING]: Dist=3.29km, Dur=39.5min, Score=99.0
    Mode [CYCLING]: Dist=3.88km, Dur=16.7min, Score=85.0
    Mode [DRIVING]: Dist=3.58km, Dur=5.4min, Score=99.0

[5] Priority Weight Sensitivity Test (CP -> India Gate, Driving):
    Priority [HEALTH_FIRST]: Recommended=Route 2 | Overall=99.0
    Priority [BALANCED]: Recommended=Route 2 | Overall=99.0
    Priority [TIME_FIRST]: Recommended=Route 2 | Overall=99.0

[6] Regional Corridor Matrix (Kalyani -> Kolkata):
    Returned 3 route option(s).
      - Route 2 (Alternative): Dist=52.45km, Dur=51.0min, Score=73.9
      - Route 1 (Primary Route): Dist=56.71km, Dur=49.0min, Score=70.0
      - Route 3 (Alternative): Dist=52.48km, Dur=51.3min, Score=69.8

[7] Long Distance Corridor Matrix (Delhi -> Kolkata):
    Returned 1 route option(s) (Long-distance bypass).
    Top: Dist=1457.14km, Dur=956.6min, Score=85.0

[8] AI Assistant RAG Chat Verification:
    Sources retrieved: [{'title': 'Air Quality Index (AQI) Interpretation', 'source': 'aqi.md'}]
    Disclaimer present: Yes ("CleanRoute AI provides informational, pollution-aware travel recommendations...")

==================================================
SUCCESS: ALL REAL-WORLD MATRIX TESTS PASSED!
==================================================
```

---

## 4. Edge Cases & Boundary Conditions Verification

Executed via automated script `scratch/test_edge_cases.py`:

```
==================================================
CLEANROUTE AI — EDGE CASE & ERROR HANDLING TESTS
==================================================

[1] Geocoding Edge Cases:
    Empty query 'q=': Status 200, Suggestions: 0 (Graceful empty list)
    Short query 'a': Status 200, Suggestions: 0 (No unnecessary API calls)
    Non-existent location: Status 200, Suggestions: 0 (No 500 error)
    Direct geocode empty string: Status 400 Bad Request

[2] Weather & Air Quality Boundary Cases:
    Weather with no coordinates: Status 400 Bad Request
    Air quality with no coordinates: Status 400 Bad Request
    AQI with out-of-bound coords (999, 999): Status 400 Bad Request

[3] Route Search Edge Cases:
    Empty route payload: Status 400 Bad Request
    Identical origin & destination: Status 400 Bad Request ("Origin and destination cannot be identical")
    Invalid travel mode 'rocket_ship': Status 400 Bad Request ("Invalid travel mode")
    Invalid priority string: Status 400 Bad Request ("Invalid route preference")

[4] AI Assistant Edge Cases:
    Empty chat message: Status 400 Bad Request
    Adversarial/Medical inquiry: Status 200 OK with strict non-medical refusal and disclaimer

==================================================
SUCCESS: ALL EDGE CASE TESTS PASSED!
==================================================
```
