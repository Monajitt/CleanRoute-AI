/**
 * CleanRoute AI — Main Application Controller
 * 
 * Manages global navigation, search-as-you-type location suggestions (Photon),
 * search form validation, travel mode & preference toggles, swap origins,
 * quick examples, and homepage map preview.
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // Helper to escape HTML characters in suggestion labels
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // =========================================================================
  // 1. Navigation & Mobile Drawer
  // =========================================================================
  const mobileToggle = document.getElementById('mobile-nav-toggle');
  const navMenu = document.getElementById('nav-menu');
  const header = document.querySelector('.site-header');

  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', () => {
      const isOpen = navMenu.classList.toggle('open');
      mobileToggle.setAttribute('aria-expanded', isOpen);
      mobileToggle.innerHTML = isOpen
        ? `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
        : `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
    });

    // Close on link click
    navMenu.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('open');
        mobileToggle.setAttribute('aria-expanded', 'false');
        mobileToggle.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
      });
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!navMenu.contains(e.target) && !mobileToggle.contains(e.target) && navMenu.classList.contains('open')) {
        navMenu.classList.remove('open');
        mobileToggle.setAttribute('aria-expanded', 'false');
        mobileToggle.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
      }
    });
  }

  // Active Link Highlight
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });

  // Header shadow on scroll
  window.addEventListener('scroll', () => {
    if (header) {
      if (window.scrollY > 20) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    }
  });

  // =========================================================================
  // 2. Search-as-You-Type Autocomplete (Photon Geocoder)
  // =========================================================================
  const searchForm = document.getElementById('route-search-form');
  const inputOrigin = document.getElementById('input-origin');
  const inputDest = document.getElementById('input-destination');
  const suggestionsOrigin = document.getElementById('suggestions-origin');
  const suggestionsDest = document.getElementById('suggestions-destination');
  const spinnerOrigin = document.getElementById('spinner-origin');
  const spinnerDest = document.getElementById('spinner-destination');
  const errorOrigin = document.getElementById('error-origin');
  const errorDest = document.getElementById('error-destination');
  const formAlert = document.getElementById('form-alert');
  const swapBtn = document.getElementById('btn-swap-locations');

  // Reference to preview map if on homepage
  let previewMapInstance = null;

  function setupAutocomplete(inputEl, dropdownEl, spinnerEl, isOrigin) {
    if (!inputEl || !dropdownEl) return;

    let currentFocus = -1;
    let debounceTimer = null;
    let lastQuery = '';

    function closeDropdown() {
      dropdownEl.style.display = 'none';
      dropdownEl.innerHTML = '';
      currentFocus = -1;
    }

    function setActiveItem(items) {
      if (!items || items.length === 0) return;
      items.forEach(item => item.classList.remove('active'));
      if (currentFocus >= items.length) currentFocus = 0;
      if (currentFocus < 0) currentFocus = items.length - 1;
      items[currentFocus].classList.add('active');
      items[currentFocus].scrollIntoView({ block: 'nearest' });
    }

    function selectSuggestion(suggestion) {
      inputEl.value = suggestion.display_name || suggestion.name;
      inputEl.dataset.lat = suggestion.latitude;
      inputEl.dataset.lon = suggestion.longitude;
      inputEl.dataset.name = suggestion.name;

      inputEl.classList.remove('input-error');
      const errEl = isOrigin ? errorOrigin : errorDest;
      if (errEl) errEl.textContent = '';
      if (formAlert) formAlert.classList.remove('show');

      closeDropdown();

      // Update marker on home preview map if present
      if (window.CleanRouteMap && suggestion.latitude && suggestion.longitude) {
        if (isOrigin) {
          window.CleanRouteMap.setOriginMarker([suggestion.latitude, suggestion.longitude], suggestion.name);
        } else {
          window.CleanRouteMap.setDestinationMarker([suggestion.latitude, suggestion.longitude], suggestion.name);
        }
        window.CleanRouteMap.fitMapToRoutes();
      }
    }

    // Handle user typing
    inputEl.addEventListener('input', () => {
      const query = inputEl.value.trim();

      // User modified text: invalidate stored coordinates so manual edit is re-geocoded
      delete inputEl.dataset.lat;
      delete inputEl.dataset.lon;
      delete inputEl.dataset.name;

      // Clear input error
      inputEl.classList.remove('input-error');
      const errEl = isOrigin ? errorOrigin : errorDest;
      if (errEl) errEl.textContent = '';
      if (formAlert) formAlert.classList.remove('show');

      if (query.length < 2) {
        if (spinnerEl) spinnerEl.style.display = 'none';
        closeDropdown();
        return;
      }

      if (spinnerEl) spinnerEl.style.display = 'block';
      clearTimeout(debounceTimer);

      debounceTimer = setTimeout(async () => {
        lastQuery = query;
        try {
          const suggestions = await window.CleanRouteAPI.getLocationSuggestions(query, 5);

          // Check if user has since cleared or changed the input
          if (inputEl.value.trim() !== query) return;

          dropdownEl.innerHTML = '';

          if (!suggestions || suggestions.length === 0) {
            dropdownEl.innerHTML = `<div class="suggestion-empty">No locations found. Try a different city or place name.</div>`;
            dropdownEl.style.display = 'block';
            return;
          }

          suggestions.forEach((s, idx) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.setAttribute('role', 'option');
            item.setAttribute('data-index', idx);

            // Subtitle formatting: City, State, Country
            const subParts = [s.city, s.state, s.country].filter(x => x && x.toLowerCase() !== (s.name || '').toLowerCase());
            const subtitle = subParts.join(', ');

            item.innerHTML = `
              <div class="suggestion-name">${escapeHtml(s.name)}</div>
              ${subtitle ? `<div class="suggestion-subtitle">${escapeHtml(subtitle)}</div>` : ''}
            `;

            // Use mousedown instead of click to prevent blur before selection
            item.addEventListener('mousedown', (e) => {
              e.preventDefault();
              selectSuggestion(s);
            });

            dropdownEl.appendChild(item);
          });

          dropdownEl.style.display = 'block';
          currentFocus = -1;
        } catch (err) {
          console.warn("Autocomplete error:", err);
          dropdownEl.innerHTML = `<div class="suggestion-empty">Error fetching suggestions</div>`;
          dropdownEl.style.display = 'block';
        } finally {
          if (spinnerEl) spinnerEl.style.display = 'none';
        }
      }, 250);
    });

    // Keyboard navigation (Arrow keys, Enter, Escape)
    inputEl.addEventListener('keydown', (e) => {
      const items = dropdownEl.querySelectorAll('.suggestion-item');

      if (dropdownEl.style.display !== 'none' && items.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          currentFocus++;
          setActiveItem(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          currentFocus--;
          setActiveItem(items);
        } else if (e.key === 'Enter') {
          if (currentFocus > -1 && items[currentFocus]) {
            e.preventDefault();
            items[currentFocus].dispatchEvent(new MouseEvent('mousedown'));
          }
        } else if (e.key === 'Escape') {
          closeDropdown();
        }
      }
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
        closeDropdown();
        if (spinnerEl) spinnerEl.style.display = 'none';
      }
    });

    // Reopen dropdown on focus if suggestions already present
    inputEl.addEventListener('focus', () => {
      if (inputEl.value.trim().length >= 2 && dropdownEl.children.length > 0) {
        dropdownEl.style.display = 'block';
      }
    });
  }

  // Initialize Autocomplete for both Origin and Destination
  setupAutocomplete(inputOrigin, suggestionsOrigin, spinnerOrigin, true);
  setupAutocomplete(inputDest, suggestionsDest, spinnerDest, false);

  // =========================================================================
  // 3. Swap Locations Button
  // =========================================================================
  if (swapBtn && inputOrigin && inputDest) {
    swapBtn.addEventListener('click', (e) => {
      e.preventDefault();

      // Swap values
      const tempVal = inputOrigin.value;
      inputOrigin.value = inputDest.value;
      inputDest.value = tempVal;

      // Swap datasets
      const tempLat = inputOrigin.dataset.lat;
      const tempLon = inputOrigin.dataset.lon;
      const tempName = inputOrigin.dataset.name;

      if (inputDest.dataset.lat) inputOrigin.dataset.lat = inputDest.dataset.lat; else delete inputOrigin.dataset.lat;
      if (inputDest.dataset.lon) inputOrigin.dataset.lon = inputDest.dataset.lon; else delete inputOrigin.dataset.lon;
      if (inputDest.dataset.name) inputOrigin.dataset.name = inputDest.dataset.name; else delete inputOrigin.dataset.name;

      if (tempLat) inputDest.dataset.lat = tempLat; else delete inputDest.dataset.lat;
      if (tempLon) inputDest.dataset.lon = tempLon; else delete inputDest.dataset.lon;
      if (tempName) inputDest.dataset.name = tempName; else delete inputDest.dataset.name;

      // Animate rotation
      swapBtn.style.transform = 'rotate(180deg)';
      setTimeout(() => {
        swapBtn.style.transform = '';
      }, 300);
    });
  }

  // Mode Selector (Walking, Cycling, Driving)
  const modeButtons = document.querySelectorAll('[data-mode]');
  const hiddenModeInput = document.getElementById('selected-mode');
  modeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      modeButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const selectedMode = btn.getAttribute('data-mode');
      if (hiddenModeInput) hiddenModeInput.value = selectedMode;
    });
  });

  // Preference Selector (Health First, Balanced, Time First)
  const prefButtons = document.querySelectorAll('[data-preference]');
  const hiddenPrefInput = document.getElementById('selected-preference');
  prefButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      prefButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const selectedPref = btn.getAttribute('data-preference');
      if (hiddenPrefInput) hiddenPrefInput.value = selectedPref;
    });
  });

  // Quick Examples (Delhi -> Kolkata, Kalyani -> Kolkata, Kolkata -> Delhi, Delhi -> Mumbai)
  const exampleChips = document.querySelectorAll('[data-example-from]');
  exampleChips.forEach(chip => {
    chip.addEventListener('click', (e) => {
      e.preventDefault();
      const fromVal = chip.getAttribute('data-example-from');
      const toVal = chip.getAttribute('data-example-to');

      if (inputOrigin) {
        inputOrigin.value = fromVal;
        delete inputOrigin.dataset.lat;
        delete inputOrigin.dataset.lon;
        delete inputOrigin.dataset.name;
        inputOrigin.classList.remove('input-error');
      }
      if (inputDest) {
        inputDest.value = toVal;
        delete inputDest.dataset.lat;
        delete inputDest.dataset.lon;
        delete inputDest.dataset.name;
        inputDest.classList.remove('input-error');
      }

      if (errorOrigin) errorOrigin.textContent = '';
      if (errorDest) errorDest.textContent = '';
      if (formAlert) formAlert.classList.remove('show');
    });
  });

  // =========================================================================
  // 4. Form Validation & Submission
  // =========================================================================
  if (searchForm) {
    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      let hasError = false;
      const originVal = inputOrigin ? inputOrigin.value.trim() : '';
      const destVal = inputDest ? inputDest.value.trim() : '';
      const mode = hiddenModeInput ? hiddenModeInput.value : 'cycling';
      const pref = hiddenPrefInput ? hiddenPrefInput.value : 'Balanced';

      // 1. Empty Origin
      if (!originVal) {
        if (inputOrigin) inputOrigin.classList.add('input-error');
        if (errorOrigin) errorOrigin.textContent = 'Please enter a departure location';
        hasError = true;
      }

      // 2. Empty Destination
      if (!destVal) {
        if (inputDest) inputDest.classList.add('input-error');
        if (errorDest) errorDest.textContent = 'Please enter a destination';
        hasError = true;
      }

      // 3. Same Origin and Destination
      if (originVal && destVal && originVal.toLowerCase() === destVal.toLowerCase()) {
        if (inputDest) inputDest.classList.add('input-error');
        if (formAlert) {
          formAlert.textContent = 'Origin and destination cannot be identical. Please select different points.';
          formAlert.classList.add('show');
        }
        hasError = true;
      }

      if (hasError) return;

      const submitBtn = document.getElementById('btn-submit-search');
      const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
          <span class="spinner" style="width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: #ffffff; border-radius: 50%; display: inline-block; vertical-align: middle; margin-right: 0.5rem;"></span>
          Finding Clean Routes...
        `;
      }

      // Extract coordinates from dataset if user picked from suggestions
      const originLat = inputOrigin && inputOrigin.dataset.lat ? parseFloat(inputOrigin.dataset.lat) : undefined;
      const originLon = inputOrigin && inputOrigin.dataset.lon ? parseFloat(inputOrigin.dataset.lon) : undefined;
      const destLat = inputDest && inputDest.dataset.lat ? parseFloat(inputDest.dataset.lat) : undefined;
      const destLon = inputDest && inputDest.dataset.lon ? parseFloat(inputDest.dataset.lon) : undefined;

      let searchId = null;

      // Submit search to Django REST API -> PostgreSQL
      if (window.CleanRouteAPI && typeof window.CleanRouteAPI.saveRouteSearch === 'function') {
        try {
          const apiResponse = await window.CleanRouteAPI.saveRouteSearch({
            origin: originVal,
            destination: destVal,
            origin_lat: originLat,
            origin_lon: originLon,
            dest_lat: destLat,
            dest_lon: destLon,
            mode: mode,
            preference: pref
          });

          if (apiResponse && apiResponse.success && apiResponse.data) {
            searchId = apiResponse.data.search_id || apiResponse.data.id;
            try {
              sessionStorage.setItem('cleanroute_last_search', JSON.stringify(apiResponse.data));
            } catch (_) {}
          } else if (apiResponse && !apiResponse.success) {
            // Geocoding or validation error
            const errMsg = (apiResponse.error && apiResponse.error.message) 
              || "Location not found. Please select a location from the suggestions.";
            if (formAlert) {
              formAlert.textContent = errMsg;
              formAlert.classList.add('show');
            }
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = originalBtnHtml;
            }
            return; // Stop flow; do not redirect on geocoding failure
          }
        } catch (apiErr) {
          console.warn("Backend error during search:", apiErr.message);
        }
      }

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;
      }

      // Navigate to results page with URL query parameters
      const params = new URLSearchParams({
        from: originVal,
        to: destVal,
        mode: mode,
        preference: pref
      });

      if (originLat !== undefined && originLon !== undefined) {
        params.set('from_lat', originLat);
        params.set('from_lon', originLon);
      }
      if (destLat !== undefined && destLon !== undefined) {
        params.set('to_lat', destLat);
        params.set('to_lon', destLon);
      }
      if (searchId) {
        params.set('search_id', searchId);
      }

      window.location.href = `results.html?${params.toString()}`;
    });
  }

  // =========================================================================
  // 5. Homepage Map Preview (Clean overview without hardcoded Kalyani)
  // =========================================================================
  const previewMapContainer = document.getElementById('home-preview-map');
  if (previewMapContainer && window.CleanRouteMap) {
    // Center overview on India [22.5, 82.0] at zoom 5
    previewMapInstance = window.CleanRouteMap.initializeMap('home-preview-map', [22.5, 82.0], 5);
  }
});
