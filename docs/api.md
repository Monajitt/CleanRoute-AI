# CleanRoute AI — REST API Documentation

Base URL: `http://127.0.0.1:8000/api` (Local) or `https://<render-app-name>.onrender.com/api` (Production)

All requests and responses use standard JSON (`Content-Type: application/json`).

---

## 1. System & Health

### `GET /api/health/`
Returns system status and verifies active PostgreSQL database connection.

**Response `200 OK`:**
```json
{
  "status": "success",
  "database": "connected",
  "version": "1.0.0",
  "timestamp": "2026-09-13T11:15:00.000000Z"
}
```

---

## 2. Geocoding

### `GET /api/geocoding/suggestions/?q=<query>&limit=5`
Retrieves search-as-you-type location suggestions powered by the Photon Komoot API.

**Query Parameters:**
- `q` (string, required): Search query (minimum 2 characters).
- `limit` (integer, optional): Maximum suggestions to return (default: 5).

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "name": "Connaught Place",
      "display_name": "Connaught Place, New Delhi, Delhi, India",
      "latitude": 28.6328,
      "longitude": 77.2197,
      "city": "New Delhi",
      "state": "Delhi",
      "country": "India"
    }
  ]
}
```

### `POST /api/geocoding/`
Directly geocodes a single location string into geographic coordinates.

**Request Body:**
```json
{
  "location": "India Gate, New Delhi"
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "name": "India Gate",
    "display_name": "India Gate, Rajpath, New Delhi, Delhi, India",
    "latitude": 28.6129,
    "longitude": 77.2295
  }
}
```

---

## 3. Environmental APIs

### `GET /api/weather/?latitude=<lat>&longitude=<lon>`
Fetches real atmospheric conditions from Open-Meteo.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "temperature": 29.4,
    "weather_code": 1,
    "weather_description": "Mainly Clear",
    "humidity": 68,
    "wind_speed": 7.2,
    "precipitation": 0.0,
    "location_label": "Weather near destination",
    "is_live": true
  }
}
```

### `GET /api/air-quality/?latitude=<lat>&longitude=<lon>`
Fetches live air quality and criteria pollutants from Open-Meteo Air Quality API.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "european_aqi": 48,
    "aqi_category": "Good",
    "us_aqi": 62,
    "pm2_5": 16.4,
    "pm10": 34.1,
    "nitrogen_dioxide": 22.0,
    "ozone": 45.2,
    "sulphur_dioxide": 8.1,
    "carbon_monoxide": 310.0,
    "is_live": true
  }
}
```

---

## 4. Routing & Recommendation

### `POST /api/routes/search/`
Unified routing and scoring endpoint. Evaluates route alternatives, samples air quality, calculates multi-criteria recommendation scores, and persists the search inquiry to PostgreSQL.

**Request Body:**
```json
{
  "origin_name": "Connaught Place",
  "destination_name": "India Gate",
  "origin_latitude": 28.6328,
  "origin_longitude": 77.2197,
  "destination_latitude": 28.6129,
  "destination_longitude": 77.2295,
  "travel_mode": "cycling",
  "route_preference": "health_first"
}
```
*Note: Nested objects (`"origin": {"name": "...", "latitude": ..., "longitude": ...}`) and alias `"priority": "health"` are also supported.*

**Response `201 Created`:**
```json
{
  "success": true,
  "data": {
    "search_id": 42,
    "origin_name": "Connaught Place",
    "destination_name": "India Gate",
    "travel_mode": "cycling",
    "route_preference": "health_first",
    "routes": [
      {
        "id": 1,
        "name": "Route 1 (Primary Route)",
        "distance_km": 3.88,
        "duration_minutes": 16.7,
        "geometry": [[28.6328, 77.2197], [28.6129, 77.2295]],
        "overall_score": 88.5,
        "scores": {
          "pollution_score": 92.0,
          "time_score": 85.0,
          "distance_score": 88.0,
          "final_score": 88.5
        },
        "air_quality": {
          "average_aqi": 46.5,
          "aqi_category": "Good",
          "average_pm2_5": 15.2,
          "estimated_pollution_exposure": "Low estimated pollution exposure"
        },
        "is_recommended": true,
        "rank": 1,
        "why_recommended": "Recommended under Health First priority for providing the lowest air pollution exposure."
      }
    ],
    "recommended_route": { ... },
    "weather": { ... }
  }
}
```

---

## 5. Grounded AI Assistant (Local RAG)

### `POST /api/chat/`
Submits a user question to the grounded Local RAG AI Assistant.

**Request Body:**
```json
{
  "message": "Which route should I choose if I have asthma?",
  "route_context": {
    "origin": "Connaught Place",
    "destination": "India Gate",
    "aqi": 48
  }
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "reply": "Under moderate or elevated air quality, selecting the Health First route is advisable as it minimizes exposure to PM2.5 and vehicular nitrogen dioxide...",
    "sources": ["WHO Air Quality Guidelines", "CleanRoute AI Environmental Routing Docs"],
    "disclaimer": "CleanRoute AI provides informational, pollution-aware travel recommendations based on available routing, environmental and weather data. It does not provide medical advice or guarantee safety."
  }
}
```

### `GET /api/chat/`
Returns assistant capabilities, prompt suggestions, and ethical disclaimer.
