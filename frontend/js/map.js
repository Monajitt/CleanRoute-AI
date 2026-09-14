/**
 * CleanRoute AI — Modular Leaflet Map Controller
 * 
 * ARCHITECTURAL NOTICE:
 * This module isolates all Leaflet.js and OpenStreetMap mapping logic.
 * Currently it renders demo routes using local coordinate arrays.
 * When connected to the Django REST API in Phase 2, this module will consume
 * GeoJSON / polyline geometry returned by Django/OpenRouteService.
 */

const CleanRouteMap = (() => {
  'use strict';

  let mapInstance = null;
  let originMarker = null;
  let destinationMarker = null;
  const routePolylines = new Map();
  let featureGroup = null;

  // Interactive AQI + Weather Hover Subsystem State
  let hoverPopup = null;
  let hoverPointer = null;
  const envCache = new Map(); // Grid cache keyed by "lat.toFixed(2),lon.toFixed(2)"
  let hoverTimer = null;
  let lastRequestTime = 0;
  const THROTTLE_INTERVAL_MS = 2500; // Throttle: at most 1 network call per 2.5 seconds
  const DEBOUNCE_DELAY_MS = 600;     // Debounce: 600ms steady hover before requesting new grid cell

  // US EPA AQI Visual Brackets
  function getAqiVisualMeta(aqi) {
    if (aqi == null || isNaN(aqi)) {
      return {
        label: 'Unavailable',
        displayAqi: '--',
        color: '#64748b',
        bgRgba: 'rgba(100, 116, 139, 0.12)',
        catClass: 'hover-cat-unavailable'
      };
    }
    const num = Math.round(Number(aqi));
    if (num <= 50) {
      return { label: 'Good', displayAqi: String(num), color: '#10b981', bgRgba: 'rgba(16, 185, 129, 0.12)', catClass: 'hover-cat-good' };
    } else if (num <= 100) {
      return { label: 'Moderate', displayAqi: String(num), color: '#f59e0b', bgRgba: 'rgba(245, 158, 11, 0.12)', catClass: 'hover-cat-moderate' };
    } else if (num <= 150) {
      return { label: 'Unhealthy for Sensitive Groups', displayAqi: String(num), color: '#f97316', bgRgba: 'rgba(249, 115, 22, 0.12)', catClass: 'hover-cat-sensitive' };
    } else if (num <= 200) {
      return { label: 'Unhealthy', displayAqi: String(num), color: '#ef4444', bgRgba: 'rgba(239, 68, 68, 0.12)', catClass: 'hover-cat-unhealthy' };
    } else if (num <= 300) {
      return { label: 'Very Unhealthy', displayAqi: String(num), color: '#8b5cf6', bgRgba: 'rgba(139, 92, 246, 0.12)', catClass: 'hover-cat-very-unhealthy' };
    } else {
      return { label: 'Hazardous', displayAqi: num > 500 ? '>500' : String(num), color: '#7f1d1d', bgRgba: 'rgba(127, 29, 29, 0.18)', catClass: 'hover-cat-hazardous' };
    }
  }

  // Update or instantiate single temporary hover pointer marker
  function updateHoverPointer(latlng) {
    if (!mapInstance) return;
    if (!hoverPointer) {
      hoverPointer = L.circleMarker(latlng, {
        radius: 6,
        color: '#059669',
        weight: 2,
        fillColor: '#10b981',
        fillOpacity: 0.85,
        interactive: false,
        pane: 'markerPane'
      }).addTo(mapInstance);
    } else {
      hoverPointer.setLatLng(latlng);
      if (!mapInstance.hasLayer(hoverPointer)) {
        hoverPointer.addTo(mapInstance);
      }
    }
  }

  // Render Unified Compact Hover Popup HTML (AQI + Weather)
  function renderHoverPopupHtml(lat, lon, aqiData, weatherData, isLoading = false) {
    const latStr = Math.abs(lat).toFixed(2) + (lat >= 0 ? '° N' : '° S');
    const lonStr = Math.abs(lon).toFixed(2) + (lon >= 0 ? '° E' : '° W');

    if (isLoading) {
      return `
        <div class="cleanroute-hover-card">
          <div class="hover-card-header">
            <span class="hover-card-title"><span class="hover-pin-icon">📍</span> MAP LOCATION</span>
            <span class="hover-card-coords">${latStr}, ${lonStr}</span>
          </div>
          <div class="hover-loading-state">
            <div class="hover-spinner"></div>
            <span>Loading environmental data...</span>
          </div>
          <div class="hover-card-footer">
            <span>Source: Open-Meteo</span>
            <span>Fetching model estimate...</span>
          </div>
        </div>
      `;
    }

    const hasAqi = aqiData && aqiData.isAvailable !== false && aqiData.aqi != null;
    const hasWeather = weatherData && weatherData.isAvailable !== false && weatherData.temperature != null;

    if (!hasAqi && !hasWeather) {
      return `
        <div class="cleanroute-hover-card">
          <div class="hover-card-header">
            <span class="hover-card-title"><span class="hover-pin-icon">📍</span> MAP LOCATION</span>
            <span class="hover-card-coords">${latStr}, ${lonStr}</span>
          </div>
          <div class="hover-unavailable-state">
            <strong style="color: #0f172a; font-size: 0.85rem;">Environmental data temporarily unavailable.</strong>
            <span class="text-xs text-muted" style="margin-top: 2px;">Air-quality and weather services temporarily unreachable</span>
          </div>
          <div class="hover-card-footer">
            <span>Source: Open-Meteo</span>
            <span>Current/latest available estimate</span>
          </div>
        </div>
      `;
    }

    // Format AQI data
    let aqiSectionHtml = '';
    if (hasAqi) {
      const meta = getAqiVisualMeta(aqiData.aqi);
      const pm25Str = aqiData.pm25 != null ? `${aqiData.pm25} µg/m³` : '--';
      const pm10Str = aqiData.pm10 != null ? `${aqiData.pm10} µg/m³` : '--';
      const no2Str = aqiData.no2 != null ? `${aqiData.no2} µg/m³` : '--';
      const o3Str = aqiData.ozone != null ? `${aqiData.ozone} µg/m³` : '--';

      aqiSectionHtml = `
        <div class="hover-section">
          <div class="hover-section-header">AIR QUALITY</div>
          <div class="hover-main-display">
            <div class="hover-aqi-badge ${meta.catClass}" style="border-color: ${meta.color}; background: ${meta.bgRgba}; color: ${meta.color};">
              <span class="hover-aqi-val">${meta.displayAqi}</span>
              <span class="hover-aqi-sub">AQI</span>
            </div>
            <div class="hover-status-wrap">
              <span class="hover-status-label" style="color: ${meta.color};">${meta.label}</span>
              <span class="hover-status-desc">Current AQI estimate</span>
            </div>
          </div>
          <div class="hover-pollutants-grid">
            <div class="hover-p-item">
              <span class="p-label">PM2.5</span>
              <span class="p-val">${pm25Str}</span>
            </div>
            <div class="hover-p-item">
              <span class="p-label">PM10</span>
              <span class="p-val">${pm10Str}</span>
            </div>
            <div class="hover-p-item">
              <span class="p-label">NO₂</span>
              <span class="p-val">${no2Str}</span>
            </div>
            <div class="hover-p-item">
              <span class="p-label">O₃</span>
              <span class="p-val">${o3Str}</span>
            </div>
          </div>
        </div>
      `;
    } else {
      aqiSectionHtml = `
        <div class="hover-section">
          <div class="hover-section-header">AIR QUALITY</div>
          <div class="hover-partial-unavailable">Air quality temporarily unavailable.</div>
        </div>
      `;
    }

    // Format Weather data
    let weatherSectionHtml = '';
    if (hasWeather) {
      const tempStr = typeof weatherData.temperature === 'number' ? `${weatherData.temperature.toFixed(1)}°C` : `${weatherData.temperature}°C`;
      const descStr = weatherData.description || 'Current weather';
      const iconStr = weatherData.icon || '⛅';
      const humidStr = weatherData.humidity != null ? `${weatherData.humidity}%` : '--%';
      const windStr = weatherData.windSpeed != null ? `${weatherData.windSpeed} km/h` : '-- km/h';

      weatherSectionHtml = `
        <div class="hover-section">
          <div class="hover-section-header">WEATHER</div>
          <div class="hover-weather-display">
            <div class="hover-weather-main">
              <span class="hover-weather-icon">${iconStr}</span>
              <div class="hover-weather-info">
                <span class="hover-temp-val">${tempStr}</span>
                <span class="hover-weather-desc">${descStr}</span>
              </div>
            </div>
            <div class="hover-weather-metrics">
              <div class="hover-w-item">
                <span class="w-label">Humidity</span>
                <span class="w-val">${humidStr}</span>
              </div>
              <div class="hover-w-item">
                <span class="w-label">Wind</span>
                <span class="w-val">${windStr}</span>
              </div>
            </div>
          </div>
        </div>
      `;
    } else {
      weatherSectionHtml = `
        <div class="hover-section">
          <div class="hover-section-header">WEATHER</div>
          <div class="hover-partial-unavailable">Weather temporarily unavailable.</div>
        </div>
      `;
    }

    return `
      <div class="cleanroute-hover-card">
        <div class="hover-card-header">
          <span class="hover-card-title"><span class="hover-pin-icon">📍</span> MAP LOCATION</span>
          <span class="hover-card-coords">${latStr}, ${lonStr}</span>
        </div>
        ${aqiSectionHtml}
        ${weatherSectionHtml}
        <div class="hover-card-footer">
          <span>Source: Open-Meteo</span>
          <span>Current/latest available estimate</span>
        </div>
        <div class="hover-disclaimer">Air-quality values are model-based estimates and may differ from roadside measurements.</div>
      </div>
    `;
  }

  // Handle map mouse move with smooth tracking and debounced/cached queries
  function handleMapMouseMove(e) {
    if (!mapInstance || !e.latlng) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    updateHoverPointer(e.latlng);

    const key = `${lat.toFixed(2)},${lon.toFixed(2)}`;

    // 1. If key is already in memory cache, show instantly!
    if (envCache.has(key)) {
      const cached = envCache.get(key);
      if (!hoverPopup) {
        hoverPopup = L.popup({
          className: 'cleanroute-hover-aqi-popup',
          closeButton: false,
          autoPan: false,
          closeOnClick: false,
          offset: [0, -12]
        });
      }
      hoverPopup
        .setLatLng(e.latlng)
        .setContent(renderHoverPopupHtml(lat, lon, cached.aqiData, cached.weatherData, false));
      if (!mapInstance.hasLayer(hoverPopup)) {
        hoverPopup.openOn(mapInstance);
      }
      return;
    }

    // 2. If not cached, update popup position with loading state
    if (!hoverPopup) {
      hoverPopup = L.popup({
        className: 'cleanroute-hover-aqi-popup',
        closeButton: false,
        autoPan: false,
        closeOnClick: false,
        offset: [0, -12]
      });
    }
    hoverPopup
      .setLatLng(e.latlng)
      .setContent(renderHoverPopupHtml(lat, lon, null, null, true));
    if (!mapInstance.hasLayer(hoverPopup)) {
      hoverPopup.openOn(mapInstance);
    }

    // 3. Debounced & throttled fetch
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(async () => {
      const now = Date.now();
      const elapsed = now - lastRequestTime;
      const delay = Math.max(0, THROTTLE_INTERVAL_MS - elapsed);

      setTimeout(async () => {
        // Double check cache in case resolved in interim
        if (envCache.has(key)) {
          const data = envCache.get(key);
          if (hoverPopup && mapInstance && mapInstance.hasLayer(hoverPopup)) {
            hoverPopup.setContent(renderHoverPopupHtml(lat, lon, data.aqiData, data.weatherData, false));
          }
          return;
        }

        lastRequestTime = Date.now();

        let envResult = null;
        try {
          if (window.CleanRouteAPI && typeof window.CleanRouteAPI.fetchHoverEnvironmentalData === 'function') {
            envResult = await window.CleanRouteAPI.fetchHoverEnvironmentalData(lat, lon);
          } else if (window.CleanRouteAPI && typeof window.CleanRouteAPI.fetchHoverAirQuality === 'function') {
            const aqiRes = await window.CleanRouteAPI.fetchHoverAirQuality(lat, lon);
            envResult = { aqiData: aqiRes, weatherData: { isAvailable: false } };
          } else {
            envResult = { aqiData: { isAvailable: false }, weatherData: { isAvailable: false } };
          }
        } catch (_) {
          envResult = { aqiData: { isAvailable: false }, weatherData: { isAvailable: false } };
        }

        envCache.set(key, envResult);

        // Update popup if still active on map
        if (hoverPopup && mapInstance && mapInstance.hasLayer(hoverPopup)) {
          hoverPopup.setContent(renderHoverPopupHtml(lat, lon, envResult.aqiData, envResult.weatherData, false));
        }
      }, delay);
    }, DEBOUNCE_DELAY_MS);
  }

  // Handle map mouse leave
  function handleMapMouseLeave() {
    if (hoverTimer) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
    if (hoverPopup && mapInstance) {
      mapInstance.closePopup(hoverPopup);
    }
    if (hoverPointer && mapInstance) {
      mapInstance.removeLayer(hoverPointer);
      hoverPointer = null;
    }
  }

  // Reset all hover interaction and cached points
  function clearHoverState() {
    handleMapMouseLeave();
    envCache.clear();
  }

  // Custom SVG Marker Icon Factory
  function createCustomIcon(type = 'origin') {
    const isOrigin = type === 'origin';
    const color = isOrigin ? '#059669' : '#dc2626';
    const label = isOrigin ? 'A' : 'B';

    const svgHtml = `
      <div style="position: relative; width: 34px; height: 42px; display: flex; align-items: center; justify-content: center;">
        <svg width="34" height="42" viewBox="0 0 34 42" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M17 0C7.611 0 0 7.611 0 17C0 27.5 14.5 40.5 16.2 41.8C16.6 42.1 17.4 42.1 17.8 41.8C19.5 40.5 34 27.5 34 17C34 7.611 26.389 0 17 0Z" fill="${color}" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.25))"/>
          <circle cx="17" cy="16" r="11" fill="white"/>
          <text x="17" y="20.5" font-family="'Plus Jakarta Sans', sans-serif" font-size="12" font-weight="bold" fill="${color}" text-anchor="middle">${label}</text>
        </svg>
      </div>
    `;

    return L.divIcon({
      className: 'cleanroute-map-marker',
      html: svgHtml,
      iconSize: [34, 42],
      iconAnchor: [17, 42],
      popupAnchor: [0, -38]
    });
  }

  /**
   * Initialize Leaflet map in target DOM container
   */
  function initializeMap(containerId = 'map', defaultCenter = [22.9810, 88.4410], defaultZoom = 14) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.warn(`Map container #${containerId} not found.`);
      return null;
    }

    // Clean up if already initialized
    if (mapInstance) {
      clearHoverState();
      mapInstance.remove();
      mapInstance = null;
      routePolylines.clear();
    }

    // Create Leaflet map instance
    mapInstance = L.map(containerId, {
      zoomControl: true,
      scrollWheelZoom: false, // Prevents unintended scroll capture
      attributionControl: true
    }).setView(defaultCenter, defaultZoom);

    // Add OpenStreetMap Tile Layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors | CleanRoute AI'
    }).addTo(mapInstance);

    // Feature group to calculate collective bounding boxes
    featureGroup = L.featureGroup().addTo(mapInstance);

    // Allow user to enable scroll wheel zoom on click
    mapInstance.on('focus', () => { mapInstance.scrollWheelZoom.enable(); });
    mapInstance.on('blur', () => { mapInstance.scrollWheelZoom.disable(); });

    // Interactive Map AQI Hover Listeners
    mapInstance.on('mousemove', handleMapMouseMove);
    mapInstance.on('mouseout', handleMapMouseLeave);
    mapInstance.on('click', handleMapMouseMove); // Supports mobile / touch tap evaluations

    const mapDom = mapInstance.getContainer();
    if (mapDom) {
      mapDom.addEventListener('mouseleave', handleMapMouseLeave);
    }

    return mapInstance;
  }

  /**
   * Set Origin Marker on map
   */
  function setOriginMarker(latlng, title = 'Origin') {
    if (!mapInstance) return null;
    if (originMarker) {
      featureGroup.removeLayer(originMarker);
    }

    originMarker = L.marker(latlng, {
      icon: createCustomIcon('origin'),
      title: title,
      zIndexOffset: 1000
    }).bindPopup(`<strong>Origin:</strong> ${title}`);

    featureGroup.addLayer(originMarker);
    return originMarker;
  }

  /**
   * Set Destination Marker on map
   */
  function setDestinationMarker(latlng, title = 'Destination') {
    if (!mapInstance) return null;
    if (destinationMarker) {
      featureGroup.removeLayer(destinationMarker);
    }

    destinationMarker = L.marker(latlng, {
      icon: createCustomIcon('destination'),
      title: title,
      zIndexOffset: 1000
    }).bindPopup(`<strong>Destination:</strong> ${title}`);

    featureGroup.addLayer(destinationMarker);
    return destinationMarker;
  }

  /**
   * Draw a route polyline on the map.
   * [DJANGO INTEGRATION POINT]: Accepts coordinates returned by Django REST API.
   */
  function drawRoute(routeId, coordinates, styleOptions = {}, routeData = {}) {
    if (!mapInstance) return null;

    const defaultStyle = {
      color: styleOptions.color || '#059669',
      weight: styleOptions.weight || 5,
      opacity: styleOptions.opacity || 0.85,
      lineCap: 'round',
      lineJoin: 'round'
    };

    const polyline = L.polyline(coordinates, defaultStyle);

    // Route interactive popup
    const popupContent = `
      <div style="font-family: sans-serif; min-width: 170px;">
        <h4 style="margin: 0 0 4px 0; color: #0f172a; font-size: 14px;">${routeData.name || 'Route'}</h4>
        <p style="margin: 0; font-size: 12px; color: #475569;">${routeData.tagline || ''}</p>
        <div style="margin-top: 6px; font-size: 12px; display: flex; justify-content: space-between;">
          <span><strong>${routeData.distanceKm || 0} km</strong></span>
          <span><strong>${routeData.durationMin || 0} mins</strong></span>
        </div>
        <div style="margin-top: 4px; font-size: 11px; color: ${routeData.color || '#059669'}; font-weight: 600;">
          ${routeData.pollutionLevel || 'Estimated exposure'}
        </div>
      </div>
    `;

    polyline.bindPopup(popupContent);

    // Click handler on polyline
    polyline.on('click', () => {
      highlightRoute(routeId);
      if (typeof window.onRouteSelected === 'function') {
        window.onRouteSelected(routeId);
      }
    });

    // Also support hover evaluation on route polyline seamlessly
    polyline.on('mousemove', (e) => {
      handleMapMouseMove(e);
    });

    featureGroup.addLayer(polyline);
    routePolylines.set(routeId, {
      polyline,
      baseStyle: defaultStyle,
      data: routeData
    });

    return polyline;
  }

  /**
   * Highlight a selected route by increasing line weight and opacity
   */
  function highlightRoute(selectedRouteId) {
    if (!mapInstance) return;

    routePolylines.forEach((entry, routeId) => {
      const isSelected = routeId === selectedRouteId;
      entry.polyline.setStyle({
        weight: isSelected ? 7 : 4,
        opacity: isSelected ? 1.0 : 0.45
      });

      if (isSelected) {
        entry.polyline.bringToFront();
      }
    });
  }

  /**
   * Fit map viewport to include all markers and routes
   */
  function fitMapToRoutes(padding = [40, 40]) {
    if (!mapInstance || !featureGroup || featureGroup.getLayers().length === 0) return;
    mapInstance.fitBounds(featureGroup.getBounds(), { padding: padding });
  }

  /**
   * Clear all route polylines & hover states
   */
  function clearRoutes() {
    clearHoverState();
    routePolylines.forEach((entry) => {
      if (featureGroup) featureGroup.removeLayer(entry.polyline);
    });
    routePolylines.clear();
  }

  /**
   * Expose instance for edge cases
   */
  function getMapInstance() {
    return mapInstance;
  }

  return {
    initializeMap,
    setOriginMarker,
    setDestinationMarker,
    drawRoute,
    highlightRoute,
    clearRoutes,
    clearHoverState,
    fitMapToRoutes,
    getMapInstance
  };
})();

// Attach to window
window.CleanRouteMap = CleanRouteMap;
