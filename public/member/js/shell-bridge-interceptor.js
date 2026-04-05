/**
 * Shell Bridge Interceptor
 *
 * p.fMALL shell-side postMessage listener for external FoundUp iframes.
 * Intercepts `agent_request` events and dispatches to backend, then
 * posts `agent_response` back to the origin iframe.
 *
 * Contract: EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md
 * WSP References: WSP 11 (Interface), WSP 97 (Execution Discipline)
 *
 * @module shell-bridge-interceptor
 */

(function() {
  'use strict';

  // ---- Configuration ----
  var CONFIG = {
    // Backend endpoint for agent requests (Phase 2: real endpoint)
    backendUrl: '/api/agent/request',
    // Allowed origins for external FoundUp iframes (Phase 2: registry-driven)
    allowedOrigins: [
      window.location.origin,
      'http://localhost:3000',
      'http://localhost:5173',
      'http://127.0.0.1:3000',
      'http://127.0.0.1:5173'
    ],
    // Debug mode
    debug: window.location.search.indexOf('debug=1') !== -1
  };

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

  // ---- Origin Validation ----
  function isAllowedOrigin(origin) {
    // Allow same-origin always
    if (origin === window.location.origin) return true;
    // Check allowlist
    return CONFIG.allowedOrigins.indexOf(origin) !== -1;
  }

  // ---- Request Handlers ----
  var handlers = {
    /**
     * Handle openclaw_search route requests
     * Actions: semantic_search, wsp_lookup, health
     */
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

  // ---- Semantic Search Handler ----
  function handleSemanticSearch(payload, callback) {
    var query = payload.query || '';
    var limit = payload.limit || 5;

    log('debug', 'Semantic search request', { query: query, limit: limit });

    // Phase 1: Stub response (simulates backend)
    // Phase 2: Real fetch to CONFIG.backendUrl
    if (window.shellBridgeBackend && typeof window.shellBridgeBackend.search === 'function') {
      // Real backend available
      window.shellBridgeBackend.search(query, limit)
        .then(function(results) {
          callback({
            type: 'agent_response',
            status: 'success',
            data: {
              results: results,
              quantum_coherence: 0.8
            }
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
      // Stub response for Phase 1
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

  // ---- WSP Lookup Handler ----
  function handleWspLookup(payload, callback) {
    var protocolNumber = payload.protocol_number || '';

    log('debug', 'WSP lookup request', { protocol_number: protocolNumber });

    // Phase 1: Stub response
    // Phase 2: Real fetch
    if (window.shellBridgeBackend && typeof window.shellBridgeBackend.wspLookup === 'function') {
      window.shellBridgeBackend.wspLookup(protocolNumber)
        .then(function(result) {
          callback({
            type: 'agent_response',
            status: 'success',
            data: result
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
      // Stub response
      setTimeout(function() {
        callback({
          type: 'agent_response',
          status: 'success',
          data: {
            protocol: 'WSP ' + protocolNumber,
            title: '[Stub] Protocol ' + protocolNumber,
            status: 'stub',
            stub: true
          }
        });
      }, 50);
    }
  }

  // ---- Health Check Handler ----
  function handleHealthCheck(payload, callback) {
    log('debug', 'Health check request');

    // Phase 1: Stub response
    // Phase 2: Real backend health check
    if (window.shellBridgeBackend && typeof window.shellBridgeBackend.health === 'function') {
      window.shellBridgeBackend.health()
        .then(function(result) {
          callback({
            type: 'agent_response',
            status: 'success',
            data: result
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
      // Stub response - report interceptor health
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

  // ---- Message Dispatcher ----
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
      log('debug', 'Sending response', response);
      sourceWindow.postMessage(response, origin);
    });
  }

  // ---- Main Message Listener ----
  function handleMessage(event) {
    // Validate origin
    if (!isAllowedOrigin(event.origin)) {
      log('debug', 'Ignored message from disallowed origin', event.origin);
      return;
    }

    // Validate message structure
    var data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type !== 'agent_request') return;

    log('info', 'Received agent_request', { route: data.route, origin: event.origin });

    // Dispatch to handler
    dispatchRequest(data, event.source, event.origin);
  }

  // ---- Initialization ----
  function init() {
    window.addEventListener('message', handleMessage, false);
    log('info', 'Shell Bridge Interceptor initialized');

    // Expose API for shell integration
    window.shellBridgeInterceptor = {
      // Allow shell to configure allowed origins at runtime
      addAllowedOrigin: function(origin) {
        if (CONFIG.allowedOrigins.indexOf(origin) === -1) {
          CONFIG.allowedOrigins.push(origin);
          log('info', 'Added allowed origin', origin);
        }
      },
      // Allow shell to register a real backend
      setBackend: function(backend) {
        window.shellBridgeBackend = backend;
        log('info', 'Backend registered');
      },
      // Get current config (for debugging)
      getConfig: function() {
        return Object.assign({}, CONFIG);
      }
    };
  }

  // Auto-init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
