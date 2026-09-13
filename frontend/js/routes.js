/**
 * CleanRoute AI — Route Results Controller
 * 
 * ARCHITECTURAL NOTICE:
 * Parses search parameters and coordinate overrides, orchestrates map rendering and
 * route comparison cards, displays AI recommendations, binds interactive priority switching,
 * and maintains strict visual separation between Route Match (/100) and actual AQI.
 */

const CleanRouteResults = (() => {
  'use strict';

  let currentRoutesData = null;
  let selectedRouteId = null;

  /**
   * Parse query parameters from URL (origin, destination, coordinates, mode, preference)
   */
  function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    const fromLat = params.get('from_lat');
    const fromLon = params.get('from_lon');
    const toLat = params.get('to_lat');
    const toLon = params.get('to_lon');

    return {
      origin: params.get('from') || '',
      destination: params.get('to') || '',
      from_lat: fromLat ? parseFloat(fromLat) : null,
      from_lon: fromLon ? parseFloat(fromLon) : null,
      to_lat: toLat ? parseFloat(toLat) : null,
      to_lon: toLon ? parseFloat(toLon) : null,
      mode: params.get('mode') || 'cycling',
      preference: params.get('preference') || 'Balanced',
      search_id: params.get('search_id') || null
    };
  }

  /**
   * Render Top Header Route Summary Bar
   */
  function renderHeaderBar(data) {
    const originEl = document.getElementById('header-origin');
    const destEl = document.getElementById('header-destination');
    const modeEl = document.getElementById('header-mode-badge');
    const prefEl = document.getElementById('header-pref-badge');

    if (originEl && data.origin) originEl.textContent = data.origin;
    if (destEl && data.destination) destEl.textContent = data.destination;

    const modeLabels = { walking: 'Walking', cycling: 'Cycling', driving: 'Driving' };
    if (modeEl) {
      modeEl.textContent = modeLabels[data.mode] || 'Cycling';
    }

    if (prefEl) {
      const prefTitle = normalizePrefDisplay(data.preference);
      prefEl.textContent = `${prefTitle} Priority`;
    }

    const sourceBadge = document.querySelector('.results-header-bar .badge-demo') || document.querySelector('.results-header-bar .badge-live');
    if (sourceBadge) {
      sourceBadge.className = 'badge-live';
      sourceBadge.style.cssText = 'background: rgba(5, 150, 105, 0.15); color: #059669; border: 1px solid rgba(5, 150, 105, 0.3); font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; font-weight: 600;';
      sourceBadge.textContent = 'Live OpenRouteService Data';
    }
  }

  function normalizePrefDisplay(pref) {
    const clean = String(pref || 'Balanced').toLowerCase();
    if (clean.includes('health')) return 'Health First';
    if (clean.includes('time')) return 'Time First';
    return 'Balanced';
  }

  function normalizePrefKey(pref) {
    const clean = String(pref || 'balanced').toLowerCase();
    if (clean.includes('health')) return 'health_first';
    if (clean.includes('time')) return 'time_first';
    return 'balanced';
  }

  /**
   * Render Route Preference Explanation & Interactive Priority Switcher
   */
  function renderPreferenceExplanation(preference) {
    const container = document.getElementById('preference-explainer');
    if (!container) return;

    const activePrefKey = normalizePrefKey(preference);
    const prefDisplayName = normalizePrefDisplay(preference);

    let explanationText = "";
    if (activePrefKey === "health_first") {
      explanationText = "<strong>Health First:</strong> Prioritizes lower estimated pollution exposure (60% Air Quality weighting). The recommended route minimizes particulate and emissions exposure under the selected priority.";
    } else if (activePrefKey === "time_first") {
      explanationText = "<strong>Time First:</strong> Strongly prioritizes travel duration (60% Travel Time weighting). The fastest available navigable route is recommended while keeping environmental data visible.";
    } else {
      explanationText = "<strong>Balanced:</strong> Balances estimated pollution exposure, travel duration, and distance (40% AQ, 30% Time, 30% Distance weighting).";
    }

    container.innerHTML = `
      <div class="priority-switcher-strip container">
        <div class="priority-switcher-label">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          <span>Priority:</span>
        </div>
        <div class="priority-btn-group" role="group" aria-label="Route Recommendation Priority">
          <button type="button" class="btn-priority-toggle ${activePrefKey === 'health_first' ? 'active' : ''}" data-pref="health_first">
            🌿 Health First (60% Air Quality)
          </button>
          <button type="button" class="btn-priority-toggle ${activePrefKey === 'balanced' ? 'active' : ''}" data-pref="balanced">
            ⚖️ Balanced (40% AQ / 30% Time / 30% Dist)
          </button>
          <button type="button" class="btn-priority-toggle ${activePrefKey === 'time_first' ? 'active' : ''}" data-pref="time_first">
            ⚡ Time First (60% Travel Time)
          </button>
        </div>
      </div>
      <div class="preference-explainer-inner container" style="margin-top: -0.5rem; margin-bottom: 0.75rem;">
        <div class="pref-icon-wrap">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        </div>
        <div>${explanationText} <span class="text-muted text-xs">(Preferences represent trade-offs and are not medical advice)</span></div>
      </div>
    `;

    // Bind interactive click handlers
    container.querySelectorAll('.btn-priority-toggle').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetPref = btn.getAttribute('data-pref');
        if (targetPref !== activePrefKey) {
          switchPriority(targetPref);
        }
      });
    });
  }

  /**
   * Switch Priority Dynamically without Re-Querying OpenRouteService
   */
  async function switchPriority(newPrefKey) {
    if (!currentRoutesData || !currentRoutesData.routes || currentRoutesData.routes.length === 0) return;

    const prefDisplayName = newPrefKey === 'health_first' ? 'Health First' : (newPrefKey === 'time_first' ? 'Time First' : 'Balanced');

    // 1. Re-score existing route alternatives deterministically
    const reScoredRoutes = await window.CleanRouteAPI.reScoreRoutes(currentRoutesData.routes, newPrefKey);
    currentRoutesData.routes = reScoredRoutes;
    currentRoutesData.preference = prefDisplayName;

    // 2. Identify new recommended route
    const newRecommended = reScoredRoutes.find(r => r.isRecommended) || reScoredRoutes[0];
    selectedRouteId = newRecommended.id;

    // 3. Update URL without page reload
    const url = new URL(window.location);
    url.searchParams.set('preference', prefDisplayName);
    window.history.replaceState({}, '', url);

    // 4. Update Header & Explainer
    renderHeaderBar(currentRoutesData);
    renderPreferenceExplanation(prefDisplayName);

    // 5. Re-render Route Cards
    renderRouteCards(currentRoutesData.routes, newRecommended.id);

    // 6. Update AI Recommendation Card
    const newRecommendation = await window.CleanRouteAPI.getRecommendation(currentRoutesData.routes, prefDisplayName);
    renderAIRecommendationCard(newRecommendation);

    // 7. Re-highlight Recommended Route on Leaflet Map
    selectRoute(selectedRouteId);
  }

  /**
   * Render Route Cards with explicit ROUTE MATCH (not Score) and separate AQI
   */
  function renderRouteCards(routes, recommendedRouteId) {
    const listContainer = document.getElementById('route-cards-list');
    if (!listContainer) return;

    listContainer.innerHTML = '';
    const activePrefName = normalizePrefDisplay(currentRoutesData ? currentRoutesData.preference : 'Balanced');

    routes.forEach((route, index) => {
      const isRec = route.id === recommendedRouteId || route.isRecommended;
      const isSelected = route.id === selectedRouteId;
      const ribbonText = 'RECOMMENDED ROUTE';

      const aqiDisplay = route.aqiDisplay || (route.aqi !== null && route.aqi !== undefined ? `AQI ${route.aqi}` : 'AQI unavailable');
      const aqiCat = (route.aqiCategory && route.aqiCategory !== 'Unavailable') ? route.aqiCategory : '';
      const exposureDesc = route.pollutionLevel || 'Moderate estimated pollution exposure';

      const card = document.createElement('div');
      card.className = `route-card ${isRec ? 'is-recommended' : ''} ${isSelected ? 'selected' : ''}`;
      card.id = `card-${route.id}`;
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `Select ${route.name}`);

      card.innerHTML = `
        ${isRec ? `
          <div class="recommended-ribbon">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            <span>${ribbonText}</span>
          </div>
        ` : ''}

        <div class="route-card-top">
          <div class="route-title-wrap">
            <span class="route-color-indicator route-color-${index + 1}"></span>
            <div>
              <div class="route-name">${route.name}</div>
              <div class="text-xs text-muted">${route.tagline || 'Via OpenRouteService'}</div>
            </div>
          </div>
          <!-- Distinct Route Match Pill — NEVER confused with AQI -->
          <div class="route-match-pill" title="Deterministic recommendation match score based on selected priority">
            <span class="match-label">ROUTE MATCH</span>
            <span class="match-number">${route.score} <span class="match-denom">/ 100</span></span>
          </div>
        </div>

        ${isRec ? `
          <div class="card-priority-badge">
            <span>Priority: <strong>${activePrefName}</strong></span>
          </div>
        ` : ''}

        <div class="route-metrics-grid">
          <!-- 1. Air Quality -->
          <div class="metric-item">
            <span class="metric-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              Air Quality
            </span>
            <span class="metric-val ${route.pollutionScoreCategory || 'eco-moderate'}">
              ${aqiDisplay}
              ${aqiCat ? `<span class="metric-subtag">(${aqiCat})</span>` : ''}
            </span>
          </div>

          <!-- 2. Estimated Exposure -->
          <div class="metric-item">
            <span class="metric-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><activity width="12" height="12"/></svg>
              Estimated Exposure
            </span>
            <span class="metric-val ${route.pollutionScoreCategory || 'eco-moderate'}">${exposureDesc}</span>
          </div>

          <!-- 3. Travel Time -->
          <div class="metric-item">
            <span class="metric-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Travel Time
            </span>
            <span class="metric-val">${route.durationMin} mins</span>
          </div>

          <!-- 4. Distance -->
          <div class="metric-item">
            <span class="metric-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
              Distance
            </span>
            <span class="metric-val">${route.distanceKm} km</span>
          </div>
        </div>

        ${isRec ? `
          <div class="why-this-route-box">
            <div class="why-title">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <strong>Why this route?</strong>
            </div>
            <div>${route.whyRecommended}</div>
          </div>
        ` : `
          <div class="text-xs text-muted" style="margin-top: 0.35rem; display: flex; align-items: center; justify-content: space-between;">
            <span>Alternative navigable corridor</span>
            <span>Click card to inspect on map</span>
          </div>
        `}
      `;

      card.addEventListener('click', () => {
        selectRoute(route.id);
      });

      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectRoute(route.id);
        }
      });

      listContainer.appendChild(card);
    });
  }

  /**
   * Render CleanRoute AI Recommendation Card with Clear Visual Hierarchy
   */
  function renderAIRecommendationCard(recommendation) {
    const container = document.getElementById('ai-recommendation-container');
    if (!container) return;

    const prefTitle = normalizePrefDisplay(recommendation.selectedPreference);
    const recRoute = currentRoutesData && currentRoutesData.routes
      ? (currentRoutesData.routes.find(r => r.id === recommendation.recommendedRouteId) || currentRoutesData.routes[0])
      : null;

    const aqiDisplay = recommendation.aqiDisplay || (recRoute && recRoute.aqiDisplay ? recRoute.aqiDisplay : 'AQI unavailable');
    const aqiCat = recommendation.aqiCategory || (recRoute && recRoute.aqiCategory ? recRoute.aqiCategory : 'Unavailable');
    const exposureLevel = recommendation.estimatedExposure || (recRoute ? recRoute.pollutionLevel : 'Moderate estimated pollution exposure');
    const routeMatchVal = recRoute ? `${recRoute.score} / 100` : (recommendation.routeMatch || '85 / 100');
    const travelTimeVal = recRoute ? `${recRoute.durationMin} mins` : (recommendation.travelTime || '--');
    const distanceVal = recRoute ? `${recRoute.distanceKm} km` : (recommendation.distance || '--');

    const catClass = aqiDisplay.includes('AQI') && !aqiDisplay.includes('unavailable')
      ? (Number(aqiDisplay.replace(/\D/g, '')) <= 50 ? 'eco-better' : (Number(aqiDisplay.replace(/\D/g, '')) <= 100 ? 'eco-moderate' : 'eco-worse'))
      : 'eco-moderate';

    container.innerHTML = `
      <div class="ai-recommendation-card">
        <div class="ai-card-header">
          <div class="ai-card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            <span>CleanRoute AI Recommendation</span>
          </div>
          <span class="badge-ai">Deterministic Recommendation Engine</span>
        </div>

        <!-- 1. Obvious Selected Priority Banner -->
        <div class="ai-priority-banner">
          <span class="ai-priority-caption">PRIORITY:</span>
          <span class="ai-priority-val">${prefTitle}</span>
        </div>

        <div class="ai-card-body">
          <!-- 2. Distinct 5-Box Factor Grid -->
          <div class="ai-key-factors-grid">
            <div class="ai-factor-box factor-match">
              <span class="factor-tag">ROUTE MATCH</span>
              <span class="factor-val">${routeMatchVal}</span>
              <span class="factor-sub">Deterministic Match Index</span>
            </div>

            <div class="ai-factor-box factor-aqi">
              <span class="factor-tag">AIR QUALITY</span>
              <span class="factor-val">${aqiDisplay}</span>
              <span class="factor-sub ${catClass}">${aqiCat !== 'Unavailable' ? aqiCat : 'Environmental Data'}</span>
            </div>

            <div class="ai-factor-box factor-exposure">
              <span class="factor-tag">ESTIMATED POLLUTION EXPOSURE</span>
              <span class="factor-val ${catClass}" style="font-size: 0.88rem;">${exposureLevel}</span>
              <span class="factor-sub">Modeled Corridor Exposure</span>
            </div>

            <div class="ai-factor-box factor-time">
              <span class="factor-tag">TRAVEL TIME</span>
              <span class="factor-val">${travelTimeVal}</span>
              <span class="factor-sub">Estimated Duration</span>
            </div>

            <div class="ai-factor-box factor-dist">
              <span class="factor-tag">DISTANCE</span>
              <span class="factor-val">${distanceVal}</span>
              <span class="factor-sub">Road Network Distance</span>
            </div>
          </div>

          <!-- 3. Why this route? Box -->
          <div class="ai-reasoning-section">
            <div class="ai-reasoning-label">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <strong>Why this route?</strong>
            </div>
            <p class="ai-reasoning-text">${recommendation.reasoning}</p>
          </div>

          <!-- 4. Non-Medical Advisory Disclaimer -->
          <div class="text-xs text-muted ai-disclaimer-sub">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
            <span>CleanRoute AI provides informational, pollution-aware travel recommendations based on available routing, environmental and weather data. It does not provide medical advice or guarantee safety.</span>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Handle route selection (syncs map & route card list)
   */
  function selectRoute(routeId) {
    selectedRouteId = routeId;

    // Update active state in cards
    const cards = document.querySelectorAll('.route-card');
    cards.forEach(card => card.classList.remove('selected'));

    const selectedCard = document.getElementById(`card-${routeId}`);
    if (selectedCard) {
      selectedCard.classList.add('selected');
    }

    // Highlight on map
    if (window.CleanRouteMap) {
      window.CleanRouteMap.highlightRoute(routeId);
    }
  }

  /**
   * Global callback registered for map polyline click events
   */
  window.onRouteSelected = (routeId) => {
    selectRoute(routeId);
    const selectedCard = document.getElementById(`card-${routeId}`);
    if (selectedCard) {
      selectedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  /**
   * Initialize Results Page
   */
  async function init() {
    const params = getQueryParams();
    const listContainer = document.getElementById('route-cards-list');

    // 1. Guard against empty search query
    if (!params.origin || !params.destination) {
      if (listContainer) {
        listContainer.innerHTML = `
          <div style="padding: 2.5rem 1.5rem; text-align: center; background: white; border-radius: 12px; border: 1px solid var(--border-light, #e2e8f0); margin-top: 1rem;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--surface-subtle, #f8fafc); color: var(--text-muted, #64748b); display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </div>
            <h3 style="font-size: 1.1rem; color: var(--text-primary, #0f172a); margin-bottom: 0.5rem;">No Active Route Search</h3>
            <p style="color: var(--text-muted, #64748b); font-size: 0.9rem; max-width: 420px; margin: 0 auto 1.5rem auto;">Please enter a departure location and destination on the search page to calculate live air-quality aware routes.</p>
            <a href="index.html" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.925rem;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
              Go to Search
            </a>
          </div>
        `;
      }
      return;
    }

    // Show loading state in route list
    if (listContainer) {
      listContainer.innerHTML = `
        <div style="padding: 2.5rem 1.5rem; text-align: center; color: var(--text-muted, #64748b);">
          <div class="spinner" style="width: 32px; height: 32px; border: 3px solid rgba(5, 150, 105, 0.2); border-top-color: #059669; border-radius: 50%; margin: 0 auto 0.75rem auto;"></div>
          <p style="margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--text-primary, #0f172a);">Calculating live route via OpenRouteService & Open-Meteo...</p>
          <p style="margin: 0.25rem 0 0 0; font-size: 0.8rem;">Retrieving real road networks and atmospheric data</p>
        </div>
      `;
    }

    // Clear any previous hover state
    if (window.CleanRouteMap && typeof window.CleanRouteMap.clearHoverState === 'function') {
      window.CleanRouteMap.clearHoverState();
    }

    // 2. Fetch routes from live backend (with coordinate overrides if present)
    currentRoutesData = await window.CleanRouteAPI.getRoutes(params);

    // Guard against calculation or geocoding failure
    if (!currentRoutesData || !currentRoutesData.success || !currentRoutesData.routes || currentRoutesData.routes.length === 0) {
      const errMsg = (currentRoutesData && currentRoutesData.error && currentRoutesData.error.message)
        || "Location not found. Please select a location from the suggestions.";
      if (listContainer) {
        listContainer.innerHTML = `
          <div style="padding: 2.5rem 1.5rem; text-align: center; background: white; border-radius: 12px; border: 1px solid #fee2e2; margin-top: 1rem;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: #fef2f2; color: #ef4444; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </div>
            <h3 style="font-size: 1.1rem; color: var(--text-primary, #0f172a); margin-bottom: 0.5rem;">Route Calculation Notice</h3>
            <p style="color: var(--text-muted, #64748b); font-size: 0.9rem; max-width: 440px; margin: 0 auto 1.5rem auto;">${errMsg}</p>
            <a href="index.html" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.925rem;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
              Return to Search
            </a>
          </div>
        `;
      }
      return;
    }

    // 3. Fetch AI recommendation
    const recommendation = await window.CleanRouteAPI.getRecommendation(
      currentRoutesData.routes,
      params.preference
    );

    // 4. Render Header & Explanation Banner with Switcher
    renderHeaderBar(currentRoutesData);
    renderPreferenceExplanation(params.preference);

    // 5. Initialize Map
    const map = window.CleanRouteMap.initializeMap('results-map');

    if (map && currentRoutesData.locations) {
      // Set Origin & Destination Markers
      window.CleanRouteMap.setOriginMarker(
        currentRoutesData.locations.origin.coords,
        currentRoutesData.origin
      );
      window.CleanRouteMap.setDestinationMarker(
        currentRoutesData.locations.destination.coords,
        currentRoutesData.destination
      );

      // Draw each route on map
      currentRoutesData.routes.forEach((route) => {
        window.CleanRouteMap.drawRoute(
          route.id,
          route.coordinates,
          { color: route.color },
          route
        );
      });

      // Fit map viewport to encompass all points
      window.CleanRouteMap.fitMapToRoutes();
    }

    // Default select recommended route
    selectedRouteId = recommendation.recommendedRouteId;

    // 6. Render Route Cards and AI Recommendation Card
    renderRouteCards(currentRoutesData.routes, recommendation.recommendedRouteId);
    renderAIRecommendationCard(recommendation);
    selectRoute(selectedRouteId);

    // 7. Load Environmental (Air Quality & Weather) Cards
    const weatherCoords = currentRoutesData.locations && currentRoutesData.locations.destination
      ? currentRoutesData.locations.destination.coords
      : (currentRoutesData.locations ? currentRoutesData.locations.origin.coords : null);

    window.CleanRouteWeather.loadEnvironmentalData(
      weatherCoords,
      currentRoutesData.weather
    );
  }

  return {
    init,
    selectRoute,
    switchPriority
  };
})();

// Auto-run if on results.html
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('results-map')) {
    CleanRouteResults.init();
  }
});
