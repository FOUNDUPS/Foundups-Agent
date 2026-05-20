/**
 * Shell Bridge Interceptor
 *
 * p.fMALL is an AI interaction space for engaging with everything — video,
 * documents, community, FoundUps. Video is the default catalog layer; the same
 * interaction paradigm (pinch, zoom, navigate) extends to any content type,
 * with AI mediating all engagement.
 *
 * p.fMALL shell-side postMessage listener for external FoundUp iframes.
 * Intercepts `agent_request` events and dispatches to backend, then
 * posts `agent_response` back to the origin iframe.
 *
 * Contract: EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md
 * WSP References: WSP 11 (Interface), WSP 97 (Execution Discipline)
 *
 * Backend seam:
 * - Without registration: explicit stub responses (`data.stub === true` where applicable).
 * - With registration: `window.shellBridgeBackend` must expose `search`, `wspLookup`, `health`
 *   (Promises). Use `shellBridgeInterceptor.registerShellBridgeBackend(obj, { label })` — local,
 *   explicit, bounded. No automatic fetch to HoloIndex core from the browser.
 *
 * @module shell-bridge-interceptor
 */

(function() {
  'use strict';

  // ---- Configuration ----
  var CONFIG = {
    backendUrl: '/api/agent/request',
    allowedOrigins: [
      window.location.origin,
      'http://localhost:3000',
      'http://localhost:5173',
      'http://127.0.0.1:3000',
      'http://127.0.0.1:5173'
    ],
    debug: window.location.search.indexOf('debug=1') !== -1
  };

  /** @typedef {{ mode: 'stub'|'registered', registered: boolean, label: string|null }} BackendStatus */
  var backendRegistration = {
    mode: 'stub',
    label: null
  };

  function validateShellBackend(backend) {
    if (!backend || typeof backend !== 'object') {
      return 'backend must be a non-null object';
    }
    if (typeof backend.search !== 'function') {
      return 'backend.search must be a function';
    }
    if (typeof backend.wspLookup !== 'function') {
      return 'backend.wspLookup must be a function';
    }
    if (typeof backend.health !== 'function') {
      return 'backend.health must be a function';
    }
    return null;
  }

  /**
   * Normalize backend payload to bridge contract data shape (results + quantum_coherence).
   * Does not claim full "live" search — only shapes the envelope.
   */
  function normalizeAgentData(raw) {
    if (!raw || typeof raw !== 'object') {
      return { results: [], quantum_coherence: 0.5 };
    }
    if (Array.isArray(raw.results)) {
      var out = {
        results: raw.results,
        quantum_coherence: typeof raw.quantum_coherence === 'number' ? raw.quantum_coherence : 0.618
      };
      if (raw.stub === true) out.stub = true;
      return out;
    }
    // Single protocol-style object → one row in results
    if (raw.protocol !== undefined || raw.title !== undefined || raw.path) {
      return {
        results: [{
          content: raw.content || '',
          path: raw.path || '',
          relevance: typeof raw.relevance === 'number' ? raw.relevance : 1.0,
          protocol: raw.protocol,
          title: raw.title,
          status: raw.status
        }],
        quantum_coherence: typeof raw.quantum_coherence === 'number' ? raw.quantum_coherence : 0.8
      };
    }
    return { results: [], quantum_coherence: 0.5 };
  }

  function hasRegisteredBackend() {
    return (
      backendRegistration.mode === 'registered' &&
      window.shellBridgeBackend &&
      typeof window.shellBridgeBackend.search === 'function' &&
      typeof window.shellBridgeBackend.wspLookup === 'function' &&
      typeof window.shellBridgeBackend.health === 'function'
    );
  }

  // ---- Logging ----
  function log(level, msg, data) {
    if (!CONFIG.debug && level === 'debug') return;
    var prefix = '[ShellBridge:' + level.toUpperCase() + ']';
    if (data !== undefined) {
      console.log(prefix, msg, data);
    } else {
      console.log(prefix, msg);
    }
  }

  function isAllowedOrigin(origin) {
    if (origin === window.location.origin) return true;
    return CONFIG.allowedOrigins.indexOf(origin) !== -1;
  }

  // Route → service identifier for FoundUp iframe response filtering.
  // Each route maps to the foundup_id that owns it, so connector iframes
  // can filter responses by `event.data.service === '<their_foundup_id>'`.
  var ROUTE_SERVICE_MAP = {
    'openclaw_search': 'holoindex'
  };

  var handlers = {
    openclaw_search: function(payload, callback) {
      var action = payload.action;

      if (action === 'semantic_search') {
        handleSemanticSearch(payload, callback);
      } else if (action === 'wsp_lookup') {
        handleWspLookup(payload, callback);
      } else if (action === 'health') {
        handleHealthCheck(payload, callback);
      } else {
        callback({
          type: 'agent_response',
          status: 'error',
          data: { error: 'unknown_action', action: action }
        });
      }
    }
  };

  function handleSemanticSearch(payload, callback) {
    var query = payload.query || '';
    var limit = payload.limit || 5;

    log('debug', 'Semantic search request', { query: query, limit: limit });

    if (hasRegisteredBackend()) {
      window.shellBridgeBackend.search(query, limit)
        .then(function(resultsEnvelope) {
          var data = normalizeAgentData(resultsEnvelope);
          callback({
            type: 'agent_response',
            status: 'success',
            data: data
          });
        })
        .catch(function(err) {
          callback({
            type: 'agent_response',
            status: 'error',
            data: { error: 'backend_error', message: String(err) }
          });
        });
    } else {
      setTimeout(function() {
        callback({
          type: 'agent_response',
          status: 'success',
          data: {
            results: [
              {
                content: '[Stub] Simulated search result for: ' + query,
                path: 'o:/Foundups-Agent/stub/result.md',
                relevance: 0.85
              }
            ],
            quantum_coherence: 0.618,
            stub: true
          }
        });
      }, 100);
    }
  }

  function handleWspLookup(payload, callback) {
    var protocolNumber = payload.protocol_number || '';

    log('debug', 'WSP lookup request', { protocol_number: protocolNumber });

    if (hasRegisteredBackend()) {
      window.shellBridgeBackend.wspLookup(protocolNumber)
        .then(function(result) {
          var data = normalizeAgentData(result);
          callback({
            type: 'agent_response',
            status: 'success',
            data: data
          });
        })
        .catch(function(err) {
          callback({
            type: 'agent_response',
            status: 'error',
            data: { error: 'backend_error', message: String(err) }
          });
        });
    } else {
      setTimeout(function() {
        callback({
          type: 'agent_response',
          status: 'success',
          data: {
            protocol: 'WSP ' + protocolNumber,
            title: '[Stub] Protocol ' + protocolNumber,
            status: 'stub',
            stub: true,
            results: [
              {
                content: '[Stub] Protocol ' + protocolNumber,
                path: 'WSP_framework/stub/WSP_' + protocolNumber + '.md',
                relevance: 0.5
              }
            ],
            quantum_coherence: 0.5
          }
        });
      }, 50);
    }
  }

  function handleHealthCheck(payload, callback) {
    log('debug', 'Health check request');

    if (hasRegisteredBackend()) {
      window.shellBridgeBackend.health()
        .then(function(result) {
          var data = normalizeAgentData(result);
          callback({
            type: 'agent_response',
            status: 'success',
            data: data
          });
        })
        .catch(function(err) {
          callback({
            type: 'agent_response',
            status: 'error',
            data: { error: 'backend_error', message: String(err) }
          });
        });
    } else {
      var startTime = performance.now();
      setTimeout(function() {
        var latency = Math.round(performance.now() - startTime);
        callback({
          type: 'agent_response',
          status: 'success',
          data: {
            results: [{
              content: JSON.stringify({
                status: 'healthy',
                backend: 'stub',
                latency_ms: latency
              }),
              path: '/f/holoindex/status',
              relevance: 1.0
            }],
            quantum_coherence: 0.5,
            stub: true
          }
        });
      }, 10);
    }
  }

  function dispatchRequest(request, sourceWindow, origin) {
    var route = request.route;
    var payload = request.payload || {};

    if (!handlers[route]) {
      log('warn', 'Unknown route', route);
      sourceWindow.postMessage({
        type: 'agent_response',
        status: 'error',
        data: { error: 'unknown_route', route: route }
      }, origin);
      return;
    }

    handlers[route](payload, function(response) {
      // Tag response with service identifier so FoundUp iframes can filter
      if (ROUTE_SERVICE_MAP[route]) {
        response.service = ROUTE_SERVICE_MAP[route];
      }
      log('debug', 'Sending response', response);
      sourceWindow.postMessage(response, origin);
    });
  }

  function handleMessage(event) {
    if (!isAllowedOrigin(event.origin)) {
      log('debug', 'Ignored message from disallowed origin', event.origin);
      return;
    }

    var data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type !== 'agent_request') return;

    log('info', 'Received agent_request', { route: data.route, origin: event.origin });

    dispatchRequest(data, event.source, event.origin);
  }

  function registerShellBridgeBackend(backend, options) {
    var err = validateShellBackend(backend);
    if (err) {
      log('warn', 'Backend registration rejected', err);
      return { ok: false, error: err };
    }
    window.shellBridgeBackend = backend;
    backendRegistration.mode = 'registered';
    backendRegistration.label = (options && options.label) ? String(options.label) : null;
    log('info', 'Shell bridge backend registered (explicit, local seam)', {
      label: backendRegistration.label
    });
    return { ok: true };
  }

  function clearShellBridgeBackend() {
    window.shellBridgeBackend = null;
    backendRegistration.mode = 'stub';
    backendRegistration.label = null;
    log('info', 'Shell bridge backend cleared — stub mode');
  }

  function getShellBridgeBackendStatus() {
    return {
      mode: backendRegistration.mode,
      registered: hasRegisteredBackend(),
      label: backendRegistration.label
    };
  }

  function init() {
    window.addEventListener('message', handleMessage, false);
    log('info', 'Shell Bridge Interceptor initialized');

    window.shellBridgeInterceptor = {
      addAllowedOrigin: function(origin) {
        if (CONFIG.allowedOrigins.indexOf(origin) === -1) {
          CONFIG.allowedOrigins.push(origin);
          log('info', 'Added allowed origin', origin);
        }
      },
      /** @deprecated Prefer registerShellBridgeBackend — setBackend is a thin alias */
      setBackend: function(backend) {
        return registerShellBridgeBackend(backend, { label: 'legacy-setBackend' });
      },
      registerShellBridgeBackend: registerShellBridgeBackend,
      clearShellBridgeBackend: clearShellBridgeBackend,
      getShellBridgeBackendStatus: getShellBridgeBackendStatus,
      getConfig: function() {
        return Object.assign({}, CONFIG);
      }
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
