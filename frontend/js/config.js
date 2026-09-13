/**
 * CleanRoute AI — Client Configuration
 * 
 * Provides a single configurable API base URL for communicating with the Django REST backend.
 * 
 * LOCAL DEVELOPMENT:
 * Defaults to http://127.0.0.1:8000/api when served from localhost, 127.0.0.1, or local files.
 * 
 * PRODUCTION (Render):
 * When deployed to Render or another remote host, it can be configured via:
 * 1. window.CLEANROUTE_API_URL (injected via script or hosting platform)
 * 2. localStorage.getItem('CLEANROUTE_API_BASE_URL') (runtime testing / debugging)
 * 3. Default fallback for production: https://cleanroute-backend.onrender.com/api
 */
(function() {
  'use strict';

  const PRODUCTION_BACKEND_URL = 'https://cleanroute-backend.onrender.com/api';
  const LOCAL_BACKEND_URL = 'http://127.0.0.1:8000/api';

  window.CLEANROUTE_CONFIG = {
    getApiBaseUrl: function() {
      // 1. Explicit localStorage override (useful for live frontend testing against custom/staging backends)
      if (typeof localStorage !== 'undefined') {
        const stored = localStorage.getItem('CLEANROUTE_API_BASE_URL');
        if (stored && stored.trim()) return stored.trim();
      }

      // 2. Global window override
      if (typeof window.CLEANROUTE_API_URL === 'string' && window.CLEANROUTE_API_URL.trim()) {
        return window.CLEANROUTE_API_URL.trim();
      }

      // 3. Localhost / 127.0.0.1 / file: protocol automatic detection
      const hostname = window.location.hostname;
      const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '' || window.location.protocol === 'file:';
      if (isLocal) {
        return LOCAL_BACKEND_URL;
      }

      // 4. Production default
      return PRODUCTION_BACKEND_URL;
    }
  };
})();
