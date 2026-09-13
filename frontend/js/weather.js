/**
 * CleanRoute AI — Weather & Air Quality UI Controller
 * 
 * ARCHITECTURAL NOTICE:
 * Renders environmental metrics and atmospheric conditions.
 * Communicates with CleanRouteAPI to retrieve data and handles DOM presentation.
 */

const CleanRouteWeather = (() => {
  'use strict';

  /**
   * Determine styling and descriptive class for AQI levels
   */
  function getAqiMetadata(aqi) {
    if (aqi <= 50) {
      return { label: "Good", colorClass: "aqi-good", text: "Air quality is satisfactory; air pollution poses little or no risk." };
    } else if (aqi <= 100) {
      return { label: "Moderate", colorClass: "aqi-moderate", text: "Air quality is acceptable; sensitive groups should consider reducing outdoor exertion." };
    } else if (aqi <= 150) {
      return { label: "Unhealthy for Sensitive Groups", colorClass: "aqi-sensitive", text: "Members of sensitive groups may experience health effects." };
    } else {
      return { label: "Unhealthy", colorClass: "aqi-unhealthy", text: "Everyone may begin to experience health effects." };
    }
  }

  /**
   * Render Air Quality Card
   */
  function renderAirQuality(aqiData, containerId = 'air-quality-container') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const meta = getAqiMetadata(aqiData.aqi);

    container.innerHTML = `
      <div class="env-card">
        <div class="env-card-header">
          <div class="env-card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            <span>Air Quality Index</span>
          </div>
          <span class="badge-live"><svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg> Open-Meteo Air Quality</span>
        </div>

        <div class="aqi-main-display">
          <div class="aqi-circle-badge ${meta.colorClass}">
            <span class="aqi-circle-val">${aqiData.aqi}</span>
            <span class="aqi-circle-sub">AQI</span>
          </div>
          <div class="aqi-status-text">
            <span class="aqi-level-name">${meta.label}</span>
            <span class="aqi-level-desc">${aqiData.summary || meta.text}</span>
          </div>
        </div>

        <div class="pollutants-list">
          <div class="pollutant-box">
            <div class="pollutant-label">PM2.5</div>
            <div class="pollutant-value">${aqiData.pm25}</div>
          </div>
          <div class="pollutant-box">
            <div class="pollutant-label">PM10</div>
            <div class="pollutant-value">${aqiData.pm10}</div>
          </div>
          <div class="pollutant-box">
            <div class="pollutant-label">NO2</div>
            <div class="pollutant-value">${aqiData.no2}</div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Render Weather Card
   */
  function renderWeather(weatherData, containerId = 'weather-container') {
    const container = document.getElementById(containerId);
    if (!container || !weatherData) return;

    const isLive = weatherData.source === 'Open-Meteo' || (!weatherData.isDemo && weatherData.wind_speed !== undefined);

    // Format temperature
    const tempDisplay = typeof weatherData.temperature === 'number'
      ? `${weatherData.temperature.toFixed(1)}°C`
      : (weatherData.temperature || '--°C');

    // Format condition & icon
    const conditionDisplay = weatherData.description || weatherData.condition || 'Atmospheric conditions';
    const iconDisplay = weatherData.icon || '⛅';

    // Format humidity
    const humidityDisplay = typeof weatherData.humidity === 'number'
      ? `${Math.round(weatherData.humidity)}%`
      : (weatherData.humidity || '--%');

    // Format wind
    const windDisplay = weatherData.wind_speed !== undefined
      ? `${weatherData.wind_speed} km/h`
      : (weatherData.wind || '-- km/h');

    const badgeHtml = isLive
      ? `<span class="badge-live" style="background: rgba(5, 150, 105, 0.12); color: #059669; border: 1px solid rgba(5, 150, 105, 0.3); font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; font-weight: 600;">Source: Open-Meteo</span>`
      : `<span class="badge-live">Live Environmental Data</span>`;

    container.innerHTML = `
      <div class="env-card">
        <div class="env-card-header">
          <div class="env-card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
            <span>Weather Conditions</span>
          </div>
          ${badgeHtml}
        </div>

        <div class="weather-main-display">
          <div class="weather-temp-wrap">
            <span class="weather-icon-large">${iconDisplay}</span>
            <div>
              <div class="weather-temp-num">${tempDisplay}</div>
              <div class="weather-condition-text">${conditionDisplay}</div>
            </div>
          </div>
        </div>

        <div class="weather-details-grid">
          <div class="weather-detail-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>
            <span>Humidity: <strong>${humidityDisplay}</strong></span>
          </div>
          <div class="weather-detail-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></svg>
            <span>Wind: <strong>${windDisplay}</strong></span>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Load and render environmental conditions in one operation
   */
  async function loadEnvironmentalData(coords = null, preloadedWeather = null) {
    try {
      const aqiPromise = window.CleanRouteAPI.getAirQuality(coords);
      const weatherPromise = preloadedWeather
        ? Promise.resolve(preloadedWeather)
        : window.CleanRouteAPI.getWeather(coords);

      const [aqiData, weatherData] = await Promise.all([aqiPromise, weatherPromise]);

      renderAirQuality(aqiData);
      renderWeather(weatherData);
    } catch (err) {
      console.error("Failed to load environmental conditions:", err);
    }
  }

  return {
    renderAirQuality,
    renderWeather,
    loadEnvironmentalData
  };
})();

// Attach to window
window.CleanRouteWeather = CleanRouteWeather;
