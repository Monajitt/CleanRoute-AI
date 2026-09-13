# CleanRoute AI — Responsible AI Framework & Ethics Specification

CleanRoute AI is built upon rigorous Responsible AI design principles to ensure fairness, transparency, safety, privacy, and scientific groundedness across all routing recommendations and conversational interactions.

---

## 1. Core Principles

### 1.1 Transparency & Explainability
Unlike opaque black-box deep learning recommendation systems, CleanRoute AI uses a **fully deterministic, transparent multi-criteria ranking algorithm**:
- **Normalized Sub-Scores**: Every route alternative provides clear, normalized sub-scores on a 0.0–100.0 scale:
  - **Pollution Exposure Score** ($S_{pollution}$): Min-max inverted based on route AQI exposure (higher = cleaner air).
  - **Travel Duration Score** ($S_{time}$): Min-max inverted based on trip duration (higher = faster).
  - **Distance Score** ($S_{distance}$): Min-max inverted based on odometer distance (higher = shorter).
- **Explicit Weight Vectors**:
  - *Health First*: 60% Pollution, 20% Time, 20% Distance
  - *Balanced*: 40% Pollution, 30% Time, 30% Distance
  - *Time First*: 20% Pollution, 60% Time, 20% Distance
- **Human-Readable Justification**: Every evaluated alternative includes an explicit `why_recommended` narrative explaining why the selected route matches the user's selected priority.

### 1.2 Multi-Modal Fairness & Inclusivity
- Provides equitable sustainable mobility recommendations across three distinct travel modes: **Walking**, **Cycling**, and **Driving**.
- Ensures that non-motorized and active commuters (pedestrians and cyclists), who are disproportionately exposed to vehicle emissions, receive tailored low-exposure corridors through parks, pedestrian paths, and secondary streets.
- Zero economic barriers: No account paywalls or subscription tiers.

### 1.3 Privacy by Design & Data Minimization
- **No Continuous Tracking**: CleanRoute AI does not record persistent GPS telemetry or trace user movement coordinates.
- **Minimal Retention**: Only the user's initial search query strings (origin name, destination name, travel mode, preference) and creation timestamps are persisted to PostgreSQL for analytics and query history.
- **Local RAG Execution**: Conversational questions and route inquiries are processed locally with ChromaDB embeddings; no personal queries are forwarded to external third-party proprietary chat platforms.

### 1.4 Robustness, Resilience & Graceful Degradation
- **Network Resilience**: In the event of upstream API rate limiting or temporary sensor downtime (e.g., OpenRouteService or Open-Meteo), CleanRoute AI falls back gracefully to in-memory cached corridors, regional default air quality medians, or single-route navigability without throwing unhandled exceptions.
- **Distance-Aware Routing**: ORS limits alternative route algorithms for journeys exceeding 80–100 km. CleanRoute AI dynamically detects trip length and falls back seamlessly to long-distance primary routing (e.g., Delhi to Kolkata).

### 1.5 Hallucination Prevention & Factual Grounding
- The conversational AI assistant utilizes a strict **Retrieval-Augmented Generation (RAG)** architecture.
- Assistant responses are grounded solely in curated knowledge base documents covering:
  - WHO Global Air Quality Guidelines
  - Air Quality Index (AQI) thresholds and health advisories
  - Sustainable urban mobility and active transport benefits
  - CleanRoute AI scoring formulas and system architecture
- If relevant context is absent or an inquiry falls outside environmental routing, the assistant politely declines rather than fabricating information.

---

## 2. Non-Medical Advisory Disclaimer

CleanRoute AI does **not** provide clinical diagnosis, medical treatment, or personalized healthcare advice.

> **MANDATORY NOTICE:**  
> *"CleanRoute AI provides informational, pollution-aware travel recommendations based on available routing, environmental and weather data. It does not provide medical advice or guarantee safety."*

This disclaimer is:
1. Permanently displayed in the frontend footer and route summary card.
2. Returned in every API payload from `POST /api/chat/` and `GET /api/chat/`.
3. Embedded in the assistant's system instructions and response template.

---

## 3. Human-in-the-Loop & User Autonomy
- CleanRoute AI never overrides user discretion or enforces a specific route.
- All candidate route alternatives remain interactive, clickable, and visually comparable on the Leaflet map and route card list. Users retain complete autonomy to inspect alternative paths and select the route that best suits their individual schedule and risk tolerance.
