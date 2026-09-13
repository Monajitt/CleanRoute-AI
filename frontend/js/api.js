/**
 * CleanRoute AI — API Integration Layer
 * 
 * ARCHITECTURAL FLOW:
 * Frontend UI -> api.js -> Django REST Framework (http://127.0.0.1:8000/api) -> PostgreSQL
 */

const CleanRouteAPI = (() => {
  'use strict';

  // Centralized Django REST API Base URL (dynamic via config.js with local fallback)
  const API_BASE_URL = (typeof window !== 'undefined' && window.CLEANROUTE_CONFIG && window.CLEANROUTE_CONFIG.getApiBaseUrl)
    ? window.CLEANROUTE_CONFIG.getApiBaseUrl()
    : 'http://127.0.0.1:8000/api';

  // =========================================================================
  // Centralized Demo Data Architecture (for Phase 1 frontend mock previews)
  // =========================================================================

  const demoLocations = {
    origin: {
      name: "Kalyani University Campus",
      coords: [22.9868, 88.4485]
    },
    destination: {
      name: "Kalyani Main Railway Station",
      coords: [22.9753, 88.4340]
    }
  };

  const demoRoutes = [
    {
      id: "route-1",
      name: "Eco-Balanced Route",
      tagline: "Via University Link & Central Greenway",
      isRecommended: true,
      mode: "cycling",
      distanceKm: 4.8,
      durationMin: 18,
      pollutionLevel: "Lower estimated pollution",
      pollutionScoreCategory: "eco-better",
      score: 88,
      preferenceMatch: "Balanced",
      whyRecommended: "Recommended because it provides an optimal trade-off: 38% lower estimated pollution exposure compared to main thoroughfares with only a 1.5-minute time addition.",
      coordinates: [
        [22.9868, 88.4485],
        [22.9852, 88.4462],
        [22.9830, 88.4435],
        [22.9812, 88.4410],
        [22.9790, 88.4385],
        [22.9765, 88.4360],
        [22.9753, 88.4340]
      ],
      color: "#059669"
    },
    {
      id: "route-2",
      name: "Health-First Green Corridor",
      tagline: "Via Lakeview Parkway & Park Avenue",
      isRecommended: false,
      mode: "cycling",
      distanceKm: 5.4,
      durationMin: 22,
      pollutionLevel: "Lowest estimated pollution exposure",
      pollutionScoreCategory: "eco-better",
      score: 94,
      preferenceMatch: "Health First",
      whyRecommended: "Maximizes tree canopy shade and bypasses commercial intersections; ideal for sensitive groups and clean air priority.",
      coordinates: [
        [22.9868, 88.4485],
        [22.9880, 88.4440],
        [22.9860, 88.4395],
        [22.9825, 88.4365],
        [22.9785, 88.4345],
        [22.9753, 88.4340]
      ],
      color: "#0284c7"
    },
    {
      id: "route-3",
      name: "Direct Arterial Route",
      tagline: "Via Main Commercial Boulevard",
      isRecommended: false,
      mode: "cycling",
      distanceKm: 4.2,
      durationMin: 15,
      pollutionLevel: "Moderate estimated pollution exposure",
      pollutionScoreCategory: "eco-moderate",
      score: 71,
      preferenceMatch: "Time First",
      whyRecommended: "Shortest physical route and lowest travel duration, but travels along heavy traffic roads with elevated PM2.5 concentrations.",
      coordinates: [
        [22.9868, 88.4485],
        [22.9820, 88.4445],
        [22.9780, 88.4390],
        [22.9753, 88.4340]
      ],
      color: "#7c3aed"
    }
  ];

  const demoAirQuality = {
    aqi: 82,
    status: "Moderate",
    summary: "Air quality is acceptable; however, sensitive travelers may experience mild respiratory irritation along major roads.",
    pm25: "28 µg/m³",
    pm10: "44 µg/m³",
    no2: "18 ppb",
    co: "0.6 ppm",
    categoryClass: "aqi-moderate",
    isDemo: true
  };

  const demoWeather = {
    temperature: "28°C",
    condition: "Partly Cloudy",
    icon: "⛅",
    humidity: "72%",
    wind: "12 km/h SSE",
    uvIndex: 4,
    visibility: "8 km",
    isDemo: true
  };

  const demoRecommendation = {
    recommendedRouteId: "route-1",
    routeName: "Eco-Balanced Route",
    title: "CleanRoute AI Recommendation",
    reasoning: "Route 1 is recommended because it avoids the high-density vehicular corridors of the Central Commercial Boulevard, yielding an estimated 38% reduction in particulate exposure while adding less than 2 minutes of travel time under current 12 km/h SSE wind conditions.",
    factors: [
      { label: "Pollution Exposure", value: "Significantly Reduced", icon: "shield" },
      { label: "Travel Time Cost", value: "+2.1 mins vs fastest", icon: "clock" },
      { label: "Active Mode Preference", value: "Dedicated cycle path", icon: "bike" },
      { label: "Micro-Climate", value: "45% canopy coverage", icon: "tree" }
    ],
    selectedPreference: "Balanced",
    environmentalContext: "Moderate regional AQI (82) with steady wind dispersion favors green corridor deflection."
  };

  // =========================================================================
  // Live Django REST API Client Methods
  // =========================================================================

  /**
   * Check backend service and live PostgreSQL database connectivity.
   * GET http://127.0.0.1:8000/api/health/
   */
  async function checkHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health/`, {
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.warn("CleanRoute AI backend health check unreachable:", err.message);
      return {
        success: false,
        message: "Unable to connect to CleanRoute AI server. Please make sure the backend is running.",
        database: "disconnected"
      };
    }
  }

  /**
   * Fetch search-as-you-type location suggestions via Django (backed by Komoot Photon)
   * with direct Photon fallback for resilience.
   * GET /api/geocoding/suggestions/?q=<query>&limit=5
   */
  async function getLocationSuggestions(query) {
    if (!query || query.trim().length < 2) return [];
    const clean = query.trim();

    // 1. Primary: Query Django REST API suggestions endpoint
    try {
      const resp = await fetch(`${API_BASE_URL}/geocoding/suggestions/?q=${encodeURIComponent(clean)}&limit=5`, {
        headers: { 'Accept': 'application/json' }
      });
      if (resp.ok) {
        const json = await resp.json();
        if (json && json.success && Array.isArray(json.data) && json.data.length > 0) {
          return json.data;
        }
      }
    } catch (err) {
      console.warn("Backend suggestions unreachable, attempting direct Photon query:", err.message);
    }

    // 2. Secondary fallback: Direct Photon OpenStreetMap API
    try {
      const pResp = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(clean)}&limit=5`, {
        headers: { 'Accept': 'application/json' }
      });
      if (pResp.ok) {
        const pJson = await pResp.json();
        const features = pJson.features || [];
        return features.map(f => {
          const p = f.properties || {};
          const c = f.geometry ? f.geometry.coordinates : [];
          const name = p.name || p.street || clean;
          const city = p.city || p.district || p.locality;
          const state = p.state;
          const country = p.country;
          const sub = [city, state, country].filter(x => x && x.toLowerCase() !== name.toLowerCase()).join(", ");
          return {
            name: name,
            city: city || "",
            state: state || "",
            country: country || "",
            display_name: sub ? `${name}, ${sub}` : name,
            latitude: c.length >= 2 ? c[1] : null,
            longitude: c.length >= 2 ? c[0] : null
          };
        });
      }
    } catch (pErr) {
      console.warn("Direct Photon fallback failed:", pErr.message);
    }

    return [];
  }

  /**
   * Save route search request to PostgreSQL via Django REST API.
   * POST http://127.0.0.1:8000/api/routes/search/
   */
  async function saveRouteSearch(searchParams) {
    const prefMap = {
      'health first': 'health_first',
      'health_first': 'health_first',
      'balanced': 'balanced',
      'time first': 'time_first',
      'time_first': 'time_first'
    };

    const modeMap = {
      'walking': 'walking',
      'walk': 'walking',
      'cycling': 'cycling',
      'cycle': 'cycling',
      'bike': 'cycling',
      'driving': 'driving',
      'drive': 'driving'
    };

    const rawPref = (searchParams.preference || 'balanced').toLowerCase();
    const rawMode = (searchParams.mode || 'cycling').toLowerCase();

    const originName = typeof searchParams.origin === 'object' && searchParams.origin
      ? searchParams.origin.name
      : (searchParams.origin || searchParams.origin_name || '');

    const destName = typeof searchParams.destination === 'object' && searchParams.destination
      ? searchParams.destination.name
      : (searchParams.destination || searchParams.destination_name || '');

    const payload = {
      origin_name: originName.trim(),
      destination_name: destName.trim(),
      travel_mode: modeMap[rawMode] || 'cycling',
      route_preference: prefMap[rawPref] || 'balanced'
    };

    // Extract coordinate overrides if provided
    const origLat = searchParams.origin_lat ?? (searchParams.origin && typeof searchParams.origin === 'object' ? searchParams.origin.latitude : null);
    const origLon = searchParams.origin_lon ?? (searchParams.origin && typeof searchParams.origin === 'object' ? searchParams.origin.longitude : null);
    const destLat = searchParams.dest_lat ?? (searchParams.destination && typeof searchParams.destination === 'object' ? searchParams.destination.latitude : null);
    const destLon = searchParams.dest_lon ?? (searchParams.destination && typeof searchParams.destination === 'object' ? searchParams.destination.longitude : null);

    if (origLat != null && origLon != null) {
      payload.origin_latitude = parseFloat(origLat);
      payload.origin_longitude = parseFloat(origLon);
    }
    if (destLat != null && destLon != null) {
      payload.destination_latitude = parseFloat(destLat);
      payload.destination_longitude = parseFloat(destLon);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/routes/search/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || { message: `Request failed with status ${response.status}` }
        };
      }

      return data;
    } catch (err) {
      console.warn("Failed to reach Django backend:", err.message);
      return {
        success: false,
        error: {
          message: "Unable to connect to CleanRoute AI server. Please make sure the backend is running."
        }
      };
    }
  }

  // =========================================================================
  // Route & Environmental Data Services
  // =========================================================================

  async function getRoutes(params = {}) {
    const originQuery = (params.origin || params.from || '').trim();
    const destQuery = (params.destination || params.to || '').trim();
    const modeQuery = params.mode || 'cycling';
    const prefQuery = params.preference || 'Balanced';

    if (!originQuery || !destQuery) {
      return {
        success: false,
        error: { message: "Please specify both departure and destination locations." },
        origin: originQuery,
        destination: destQuery,
        routes: [],
        locations: null
      };
    }

    // 1. Check for stored search matching exact origin/destination
    let apiData = null;
    try {
      const stored = sessionStorage.getItem('cleanroute_last_search');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (
          parsed &&
          parsed.origin &&
          parsed.destination &&
          parsed.origin.name &&
          parsed.origin.name.toLowerCase() === originQuery.toLowerCase() &&
          parsed.destination.name.toLowerCase() === destQuery.toLowerCase() &&
          parsed.routes &&
          parsed.routes.length > 0
        ) {
          apiData = parsed;
        }
      }
    } catch (_) {}

    // 2. Query Django backend
    if (!apiData) {
      const result = await saveRouteSearch({
        origin: originQuery,
        destination: destQuery,
        origin_lat: params.from_lat || params.origin_lat,
        origin_lon: params.from_lon || params.origin_lon,
        dest_lat: params.to_lat || params.dest_lat,
        dest_lon: params.to_lon || params.dest_lon,
        mode: modeQuery,
        preference: prefQuery
      });

      if (result && result.success && result.data && result.data.routes && result.data.routes.length > 0) {
        apiData = result.data;
      } else if (result && !result.success) {
        return {
          success: false,
          error: result.error || { message: "Could not calculate routes for given locations." },
          origin: originQuery,
          destination: destQuery,
          routes: [],
          locations: null
        };
      }
    }

    if (apiData && apiData.routes && apiData.routes.length > 0) {
      const mappedRoutes = apiData.routes.map((r, idx) => {
        const isRec = r.is_recommended !== undefined ? r.is_recommended : (idx === 0);
        const aq = r.air_quality || {};

        // Real AQI handling - NO fake fallback numbers!
        const aqiVal = (aq.average_aqi !== undefined && aq.average_aqi !== null)
          ? Math.round(Number(aq.average_aqi))
          : (aq.european_aqi !== undefined && aq.european_aqi !== null ? Math.round(Number(aq.european_aqi)) : null);

        const aqiCat = aq.aqi_category || (aqiVal !== null
          ? (aqiVal <= 50 ? 'Good' : aqiVal <= 100 ? 'Moderate' : aqiVal <= 150 ? 'Unhealthy for Sensitive Groups' : 'Unhealthy')
          : 'Unavailable');

        const aqiDisp = aqiVal !== null ? `AQI ${aqiVal}` : 'AQI unavailable';

        // Estimated pollution exposure description
        const exposureDesc = aq.estimated_pollution_exposure
          || (aqiVal !== null
            ? (aqiVal <= 50 ? 'Low estimated pollution exposure' : (aqiVal <= 100 ? 'Moderate estimated pollution exposure' : 'Elevated estimated pollution exposure'))
            : 'Estimated exposure unavailable');

        const catClass = aqiVal !== null ? (aqiVal <= 50 ? "eco-better" : (aqiVal <= 100 ? "eco-moderate" : "eco-worse")) : "eco-moderate";
        const calcScore = r.score !== undefined ? r.score : (r.scores ? r.scores.final_score : 85);

        return {
          id: `route-${r.id || idx + 1}`,
          rawId: r.id || idx + 1,
          name: r.name || `Route ${idx + 1}`,
          tagline: r.tagline || `Via OpenRouteService`,
          isRecommended: isRec,
          rank: r.rank || (idx + 1),
          mode: r.travel_mode || modeQuery,
          distanceKm: r.distance_km,
          durationMin: r.duration_minutes,
          distance_km: r.distance_km,
          duration_minutes: r.duration_minutes,
          aqi: aqiVal,
          aqiCategory: aqiCat,
          aqiDisplay: aqiDisp,
          pollutionLevel: exposureDesc,
          pollutionScoreCategory: catClass,
          score: calcScore,
          scores: r.scores || null,
          air_quality: aq,
          preferenceMatch: prefQuery,
          whyRecommended: r.why_recommended || (
            isRec
              ? (prefQuery.toLowerCase().includes('health')
                  ? "Recommended for Health First because this route has lower estimated pollution exposure under the selected priority."
                  : (prefQuery.toLowerCase().includes('time')
                      ? "Recommended for Time First because it provides the fastest available navigable route under the selected priority."
                      : "Recommended for Balanced priority because it provides a balance between estimated pollution exposure, travel time, and distance."))
              : `Alternative route (Route Match: ${calcScore}/100, ${r.duration_minutes} mins, ${r.distance_km} km).`
          ),
          coordinates: r.geometry,
          geometry: r.geometry,
          color: r.color || (idx === 0 ? "#059669" : (idx === 1 ? "#0284c7" : "#7c3aed")),
          isLive: true
        };
      });

      return {
        success: true,
        origin: apiData.origin ? apiData.origin.name : originQuery,
        origin_display: apiData.origin ? apiData.origin.display_name : originQuery,
        destination: apiData.destination ? apiData.destination.name : destQuery,
        destination_display: apiData.destination ? apiData.destination.display_name : destQuery,
        mode: apiData.travel_mode || modeQuery,
        preference: apiData.route_preference || prefQuery,
        routes: mappedRoutes,
        locations: {
          origin: {
            name: apiData.origin ? apiData.origin.name : originQuery,
            coords: [apiData.origin.latitude, apiData.origin.longitude]
          },
          destination: {
            name: apiData.destination ? apiData.destination.name : destQuery,
            coords: [apiData.destination.latitude, apiData.destination.longitude]
          }
        },
        weather: apiData.weather,
        isDemo: false,
        isLive: true
      };
    }

    return {
      success: false,
      error: { message: "No route options found for the specified points." },
      origin: originQuery,
      destination: destQuery,
      routes: [],
      locations: null
    };
  }

  async function getAirQuality(coords = null) {
    if (coords && Array.isArray(coords) && coords.length >= 2) {
      try {
        const response = await fetch(`${API_BASE_URL}/air-quality/?latitude=${coords[0]}&longitude=${coords[1]}`, {
          headers: { 'Accept': 'application/json' }
        });
        if (response.ok) {
          const res = await response.json();
          if (res && res.success && res.data) {
            return {
              aqi: res.data.aqi,
              status: res.data.aqi_category || "Moderate",
              summary: `${res.data.aqi_category || 'Moderate'} regional air quality (${res.data.aqi} AQI) based on available atmospheric data.`,
              pm25: `${res.data.pm25} µg/m³`,
              pm10: `${res.data.pm10} µg/m³`,
              no2: `${res.data.no2} µg/m³`,
              ozone: `${res.data.ozone} µg/m³`,
              categoryClass: res.data.aqi <= 50 ? 'aqi-good' : (res.data.aqi <= 100 ? 'aqi-moderate' : 'aqi-sensitive'),
              isDemo: false,
              isLive: true
            };
          }
        }
      } catch (err) {
        console.warn("Live air quality fetch failed, using fallback:", err.message);
      }
    }
    return demoAirQuality;
  }

  /**
   * Fetch point-specific air quality for map hover evaluations.
   * Queries Django backend with direct Open-Meteo fallback for resilience.
   * Strictly avoids mock numbers if atmospheric service is unreachable.
   */
  async function fetchHoverAirQuality(lat, lon) {
    if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) {
      return { isAvailable: false, error: "Invalid coordinates" };
    }

    const cleanLat = parseFloat(Number(lat).toFixed(4));
    const cleanLon = parseFloat(Number(lon).toFixed(4));

    // 1. Primary: Django REST API
    try {
      const response = await fetch(`${API_BASE_URL}/air-quality/?latitude=${cleanLat}&longitude=${cleanLon}`, {
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const res = await response.json();
        if (res && res.success && res.data) {
          const d = res.data;
          return {
            isAvailable: true,
            latitude: cleanLat,
            longitude: cleanLon,
            aqi: d.aqi != null ? Math.round(Number(d.aqi)) : null,
            pm25: d.pm25 != null ? parseFloat(Number(d.pm25).toFixed(1)) : null,
            pm10: d.pm10 != null ? parseFloat(Number(d.pm10).toFixed(1)) : null,
            no2: d.no2 != null ? parseFloat(Number(d.no2).toFixed(1)) : null,
            ozone: d.ozone != null ? parseFloat(Number(d.ozone).toFixed(1)) : null,
            status: d.aqi_category || (d.aqi != null ? getAqiCategoryName(d.aqi) : "Moderate"),
            source: "Open-Meteo",
            timestamp: Date.now()
          };
        }
      }
    } catch (apiErr) {
      console.warn("Backend hover AQI unreachable, falling back to direct Open-Meteo:", apiErr.message);
    }

    // 2. Secondary fallback: Direct Open-Meteo Air Quality API
    try {
      const directUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${cleanLat}&longitude=${cleanLon}&current=us_aqi,pm2_5,pm10,nitrogen_dioxide,ozone`;
      const dResp = await fetch(directUrl, { headers: { 'Accept': 'application/json' } });
      if (dResp.ok) {
        const dJson = await dResp.json();
        const cur = dJson.current || {};
        const rawAqi = cur.us_aqi != null ? Number(cur.us_aqi) : (cur.pm2_5 != null ? Math.min(500, Number(cur.pm2_5) * 2.1) : null);
        const aqi = rawAqi != null ? Math.round(rawAqi) : null;
        return {
          isAvailable: true,
          latitude: cleanLat,
          longitude: cleanLon,
          aqi: aqi,
          pm25: cur.pm2_5 != null ? parseFloat(Number(cur.pm2_5).toFixed(1)) : null,
          pm10: cur.pm10 != null ? parseFloat(Number(cur.pm10).toFixed(1)) : null,
          no2: cur.nitrogen_dioxide != null ? parseFloat(Number(cur.nitrogen_dioxide).toFixed(1)) : null,
          ozone: cur.ozone != null ? parseFloat(Number(cur.ozone).toFixed(1)) : null,
          status: aqi != null ? getAqiCategoryName(aqi) : "Moderate",
          source: "Open-Meteo",
          timestamp: Date.now()
        };
      }
    } catch (directErr) {
      console.warn("Direct Open-Meteo fallback unreachable:", directErr.message);
    }

    return {
      isAvailable: false,
      latitude: cleanLat,
      longitude: cleanLon,
      error: "Air-quality data temporarily unavailable",
      source: "Open-Meteo"
    };
  }

  function getAqiCategoryName(aqi) {
    if (aqi == null) return "Moderate";
    if (aqi <= 50) return "Good";
    if (aqi <= 100) return "Moderate";
    if (aqi <= 150) return "Unhealthy for Sensitive Groups";
    if (aqi <= 200) return "Unhealthy";
    if (aqi <= 300) return "Very Unhealthy";
    return "Hazardous";
  }

  // WMO Weather code to description and icon mapping (standard Open-Meteo table)
  const WMO_WEATHER_TABLE = {
    0: { desc: "Clear sky", icon: "☀️" },
    1: { desc: "Mainly clear", icon: "🌤️" },
    2: { desc: "Partly cloudy", icon: "⛅" },
    3: { desc: "Overcast", icon: "☁️" },
    45: { desc: "Fog", icon: "🌫️" },
    48: { desc: "Depositing rime fog", icon: "🌫️" },
    51: { desc: "Light drizzle", icon: "🌦️" },
    53: { desc: "Moderate drizzle", icon: "🌧️" },
    55: { desc: "Dense drizzle", icon: "🌧️" },
    56: { desc: "Light freezing drizzle", icon: "🌧️" },
    57: { desc: "Dense freezing drizzle", icon: "🌧️" },
    61: { desc: "Slight rain", icon: "🌦️" },
    63: { desc: "Moderate rain", icon: "🌧️" },
    65: { desc: "Heavy rain", icon: "🌧️" },
    66: { desc: "Light freezing rain", icon: "🌧️" },
    67: { desc: "Heavy freezing rain", icon: "🌧️" },
    71: { desc: "Slight snow fall", icon: "🌨️" },
    73: { desc: "Moderate snow fall", icon: "🌨️" },
    75: { desc: "Heavy snow fall", icon: "❄️" },
    77: { desc: "Snow grains", icon: "❄️" },
    80: { desc: "Slight rain showers", icon: "🌦️" },
    81: { desc: "Moderate rain showers", icon: "🌧️" },
    82: { desc: "Violent rain showers", icon: "⛈️" },
    85: { desc: "Slight snow showers", icon: "🌨️" },
    86: { desc: "Heavy snow showers", icon: "❄️" },
    95: { desc: "Thunderstorm", icon: "⛈️" },
    96: { desc: "Thunderstorm with slight hail", icon: "⛈️" },
    99: { desc: "Thunderstorm with heavy hail", icon: "⛈️" }
  };

  /**
   * Fetch point-specific weather for map hover evaluations.
   * Queries Django backend with direct Open-Meteo fallback for resilience.
   * Strictly avoids mock numbers if weather service is unreachable.
   */
  async function fetchHoverWeather(lat, lon) {
    if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) {
      return { isAvailable: false, error: "Invalid coordinates" };
    }

    const cleanLat = parseFloat(Number(lat).toFixed(4));
    const cleanLon = parseFloat(Number(lon).toFixed(4));

    // 1. Primary: Django REST API
    try {
      const response = await fetch(`${API_BASE_URL}/weather/?latitude=${cleanLat}&longitude=${cleanLon}`, {
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const res = await response.json();
        if (res && res.success && res.data) {
          const d = res.data;
          const code = d.weather_code != null ? Number(d.weather_code) : 0;
          const wmoMeta = WMO_WEATHER_TABLE[code] || { desc: d.description || "Current atmospheric conditions", icon: d.icon || "⛅" };
          return {
            isAvailable: true,
            latitude: cleanLat,
            longitude: cleanLon,
            temperature: typeof d.temperature === 'number' ? parseFloat(d.temperature.toFixed(1)) : parseFloat(Number(d.temperature).toFixed(1)),
            humidity: d.humidity != null ? Math.round(Number(d.humidity)) : null,
            windSpeed: d.wind_speed != null ? parseFloat(Number(d.wind_speed).toFixed(1)) : null,
            weatherCode: code,
            description: d.description || wmoMeta.desc,
            icon: d.icon || wmoMeta.icon,
            source: "Open-Meteo",
            timestamp: Date.now()
          };
        }
      }
    } catch (apiErr) {
      console.warn("Backend hover weather unreachable, falling back to direct Open-Meteo:", apiErr.message);
    }

    // 2. Secondary fallback: Direct Open-Meteo Forecast API
    try {
      const directUrl = `https://api.open-meteo.com/v1/forecast?latitude=${cleanLat}&longitude=${cleanLon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&wind_speed_unit=kmh&timezone=auto`;
      const dResp = await fetch(directUrl, { headers: { 'Accept': 'application/json' } });
      if (dResp.ok) {
        const dJson = await dResp.json();
        const cur = dJson.current || {};
        const code = cur.weather_code != null ? Number(cur.weather_code) : 0;
        const wmoMeta = WMO_WEATHER_TABLE[code] || { desc: "Current atmospheric conditions", icon: "⛅" };
        return {
          isAvailable: true,
          latitude: cleanLat,
          longitude: cleanLon,
          temperature: cur.temperature_2m != null ? parseFloat(Number(cur.temperature_2m).toFixed(1)) : null,
          humidity: cur.relative_humidity_2m != null ? Math.round(Number(cur.relative_humidity_2m)) : null,
          windSpeed: cur.wind_speed_10m != null ? parseFloat(Number(cur.wind_speed_10m).toFixed(1)) : null,
          weatherCode: code,
          description: wmoMeta.desc,
          icon: wmoMeta.icon,
          source: "Open-Meteo",
          timestamp: Date.now()
        };
      }
    } catch (directErr) {
      console.warn("Direct Open-Meteo weather fallback unreachable:", directErr.message);
    }

    return {
      isAvailable: false,
      latitude: cleanLat,
      longitude: cleanLon,
      error: "Weather temporarily unavailable",
      source: "Open-Meteo"
    };
  }

  /**
   * Fetch both Air Quality and Weather concurrently for the exact hovered coordinate.
   */
  async function fetchHoverEnvironmentalData(lat, lon) {
    const [aqiData, weatherData] = await Promise.all([
      fetchHoverAirQuality(lat, lon),
      fetchHoverWeather(lat, lon)
    ]);
    return { aqiData, weatherData };
  }

  async function getWeather(coords = null) {
    if (coords && Array.isArray(coords) && coords.length >= 2) {
      try {
        const response = await fetch(`${API_BASE_URL}/weather/?latitude=${coords[0]}&longitude=${coords[1]}`, {
          headers: { 'Accept': 'application/json' }
        });
        if (response.ok) {
          const res = await response.json();
          if (res && res.success && res.data) {
            return res.data;
          }
        }
      } catch (err) {
        console.warn("Live weather fetch failed, using fallback:", err.message);
      }
    }
    return demoWeather;
  }

  async function getRecommendation(routes = [], preference = "Balanced") {
    if (routes && routes.length > 0) {
      const recRoute = routes.find(r => r.isRecommended) || routes[0];
      const isLive = !!recRoute.isLive;
      const aq = recRoute.air_quality || {};
      const aqiDisplay = recRoute.aqiDisplay || (recRoute.aqi !== null && recRoute.aqi !== undefined ? `AQI ${recRoute.aqi}` : 'AQI unavailable');
      const aqiCat = recRoute.aqiCategory || (recRoute.aqi ? 'Moderate' : 'Unavailable');
      const exposure = recRoute.pollutionLevel || 'Moderate estimated pollution exposure';

      return {
        recommendedRouteId: recRoute.id,
        routeName: recRoute.name,
        title: "CleanRoute AI Recommendation",
        reasoning: recRoute.whyRecommended || (
          preference.toLowerCase().includes('health')
            ? "Recommended for Health First because this route has lower estimated pollution exposure under the selected priority."
            : (preference.toLowerCase().includes('time')
                ? "Recommended for Time First because it provides the fastest available navigable route under the selected priority."
                : "Recommended for Balanced priority because it provides a balance between estimated pollution exposure, travel time, and distance.")
        ),
        selectedPreference: preference,
        routeMatch: `${recRoute.score} / 100`,
        aqiDisplay: aqiDisplay,
        aqiCategory: aqiCat,
        estimatedExposure: exposure,
        travelTime: `${recRoute.durationMin} mins`,
        distance: `${recRoute.distanceKm} km`,
        factors: [
          { label: "Selected Priority", value: preference, icon: "target" },
          { label: "Route Match", value: `${recRoute.score} / 100`, icon: "shield" },
          { label: "Air Quality", value: aqiDisplay !== 'AQI unavailable' ? `${aqiDisplay} (${aqiCat})` : 'AQI unavailable', icon: "activity" },
          { label: "Estimated Exposure", value: exposure, icon: "activity" },
          { label: "Travel Time", value: `${recRoute.durationMin} mins`, icon: "clock" },
          { label: "Distance", value: `${recRoute.distanceKm} km`, icon: "route" }
        ],
        environmentalContext: aqiDisplay !== 'AQI unavailable'
          ? `Calculated from Open-Meteo live atmospheric criteria air pollutants and OpenRouteService road networks.`
          : "Calculated from OpenRouteService road networks and Open-Meteo atmospheric monitoring.",
        isDemo: !isLive
      };
    }

    return demoRecommendation;
  }

  /**
   * Deterministically re-score existing routes without re-fetching from OpenRouteService.
   */
  async function reScoreRoutes(routes, preference = "balanced") {
    if (!routes || routes.length === 0) return routes;

    const normPref = String(preference).toLowerCase().replace(/[\s-]/g, '_');
    const prefKey = normPref.includes('health') ? 'health_first' : (normPref.includes('time') ? 'time_first' : 'balanced');
    const prefDisplayName = prefKey === 'health_first' ? 'Health First' : (prefKey === 'time_first' ? 'Time First' : 'Balanced');

    // 1. Query Django recommendation scoring endpoint
    try {
      const resp = await fetch(`${API_BASE_URL}/recommendation/score/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          routes: routes.map(r => ({
            id: r.rawId || (typeof r.id === 'string' && r.id.startsWith('route-') ? parseInt(r.id.replace('route-', '')) : r.id),
            name: r.name,
            tagline: r.tagline,
            distance_km: r.distanceKm,
            duration_minutes: r.durationMin,
            geometry: r.geometry || r.coordinates,
            air_quality: r.air_quality,
            travel_mode: r.mode
          })),
          preference: prefKey
        })
      });

      if (resp.ok) {
        const json = await resp.json();
        if (json && json.success && json.data && Array.isArray(json.data.routes)) {
          const backendScored = json.data.routes;
          return routes.map(orig => {
            const rawId = orig.rawId || (typeof orig.id === 'string' && orig.id.startsWith('route-') ? parseInt(orig.id.replace('route-', '')) : orig.id);
            const found = backendScored.find(b => b.id === rawId);
            if (!found) return orig;
            return {
              ...orig,
              score: found.score,
              scores: found.scores,
              isRecommended: found.is_recommended,
              rank: found.rank,
              whyRecommended: found.why_recommended,
              preferenceMatch: prefDisplayName
            };
          });
        }
      }
    } catch (err) {
      console.warn("Backend reScoreRoutes API unavailable, applying client deterministic scoring:", err.message);
    }

    // 2. Client-side deterministic calculation fallback
    return scoreRoutesLocally(routes, prefKey, prefDisplayName);
  }

  function scoreRoutesLocally(routes, prefKey, prefDisplayName) {
    const weightsMap = {
      health_first: { pollution: 0.60, time: 0.20, distance: 0.20 },
      balanced: { pollution: 0.40, time: 0.30, distance: 0.30 },
      time_first: { pollution: 0.20, time: 0.60, distance: 0.20 }
    };
    const weights = weightsMap[prefKey] || weightsMap.balanced;

    const durations = routes.map(r => Number(r.durationMin || 0));
    const distances = routes.map(r => Number(r.distanceKm || 0));
    const pollutions = routes.map(r => {
      const aq = r.air_quality || {};
      return Number(aq.average_aqi !== undefined && aq.average_aqi !== null ? aq.average_aqi : (r.aqi || 50));
    });

    function normMinBetter(vals) {
      const minV = Math.min(...vals);
      const maxV = Math.max(...vals);
      if (maxV === minV) return vals.map(() => 100.0);
      return vals.map(v => Math.round((100.0 * (maxV - v) / (maxV - minV)) * 10) / 10);
    }

    const nTime = normMinBetter(durations);
    const nDist = normMinBetter(distances);
    const nPoll = normMinBetter(pollutions);

    const scored = routes.map((r, i) => {
      const sTime = nTime[i];
      const sDist = nDist[i];
      const sPoll = nPoll[i];
      const rawScore = (weights.pollution * sPoll) + (weights.time * sTime) + (weights.distance * sDist);
      const bounded = Math.round(Math.max(10.0, Math.min(99.0, rawScore)) * 10) / 10;
      return {
        ...r,
        score: bounded,
        scores: {
          pollution_score: sPoll,
          time_score: sTime,
          distance_score: sDist,
          final_score: bounded
        },
        preferenceMatch: prefDisplayName
      };
    });

    // Deterministic sort: highest score, lowest duration, lowest distance
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (a.durationMin !== b.durationMin) return a.durationMin - b.durationMin;
      return a.distanceKm - b.distanceKm;
    });

    return scored.map((r, rank) => {
      const isRec = rank === 0;
      let why = "";
      if (isRec) {
        if (prefKey === "health_first") {
          why = "Recommended for Health First because this route has lower estimated pollution exposure under the selected priority.";
        } else if (prefKey === "time_first") {
          why = "Recommended for Time First because it provides the fastest available navigable route under the selected priority.";
        } else {
          why = "Recommended for Balanced priority because it provides a balance between estimated pollution exposure, travel time, and distance.";
        }
      } else {
        why = `Alternative route (rank #${rank + 1}, Route Match: ${r.score}/100). Covers ${r.distanceKm} km in ${r.durationMin} mins.`;
      }
      return {
        ...r,
        rank: rank + 1,
        isRecommended: isRec,
        whyRecommended: why
      };
    });
  }

  async function sendChatMessage(userMessage, routeContext = null) {
    // 1. If routeContext is not passed explicitly, attempt to read the last active search from sessionStorage
    let activeContext = routeContext;
    if (!activeContext) {
      try {
        const stored = sessionStorage.getItem('cleanroute_last_search');
        if (stored) {
          activeContext = JSON.parse(stored);
        }
      } catch (_) {}
    }

    // 2. Attempt call to Django REST API
    try {
      const response = await fetch(`${API_BASE_URL}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage,
          route_context: activeContext || null
        })
      });

      if (response.ok) {
        const resJson = await response.json();
        const data = (resJson && resJson.data) ? resJson.data : resJson;
        const sourceList = Array.isArray(data.sources)
          ? data.sources.map(s => (typeof s === 'object' && s !== null ? (s.source || s.title) : String(s)))
          : [];

        return {
          reply: data.reply || data.answer || "No response generated.",
          disclaimer: data.disclaimer || "CleanRoute AI provides modeled, informational estimates and does not offer medical advice or guarantee safety.",
          sources: sourceList,
          timestamp: data.timestamp ? (String(data.timestamp).includes(':') && String(data.timestamp).length <= 8 ? String(data.timestamp) : new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          hasRouteContext: !!data.has_route_context,
          isDemo: false
        };
      }
    } catch (netErr) {
      console.warn("Backend chat API call failed, falling back:", netErr.message);
    }

    // 3. Graceful offline fallback
    return {
      reply: "CleanRoute AI evaluates real road network geometries alongside atmospheric air quality metrics. (Note: Backend server at " + API_BASE_URL + " could not be reached directly; please ensure the Django backend is running).",
      disclaimer: "CleanRoute AI provides modeled, informational estimates and does not offer medical advice or guarantee safety.",
      sources: ["aqi.md"],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      hasRouteContext: false,
      isDemo: true
    };
  }

  return {
    API_BASE_URL,
    checkHealth,
    getLocationSuggestions,
    saveRouteSearch,
    getRoutes,
    getAirQuality,
    fetchHoverAirQuality,
    fetchHoverWeather,
    fetchHoverEnvironmentalData,
    getWeather,
    getRecommendation,
    reScoreRoutes,
    sendChatMessage
  };
})();

// Attach to window object for global script access
window.CleanRouteAPI = CleanRouteAPI;
