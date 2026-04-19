/**
 * pfMALL Control Dispatcher
 *
 * Browser-side command dispatcher for structured agent control of the
 * p.fMALL video wall. Agents (0102, RedDog, native phone agent) drive
 * the wall through this contract instead of ad hoc DOM/UI driving.
 *
 * Contract: public/member/INTERFACE.md (section "pfMALL Agent Control Contract")
 * WSP References: WSP 11 (Interface), WSP 91 (Observability), WSP 97 (Truth Signalling)
 *
 * Protocol:
 *   Request:  { type: 'pfmall_command', source, target, command, request_id, payload }
 *   Response: { type: 'pfmall_response', source, target, request_id, status, result|error }
 *   Event:    { type: 'pfmall_event', source, event, payload, timestamp }
 *
 * Status values for responses:
 *   - 'ok'       command succeeded, result payload present
 *   - 'denied'   command rejected by device policy (result payload explains)
 *   - 'error'    command malformed or runtime failure (error payload present)
 *
 * Truth-signalling:
 *   The dispatcher never claims a wall state it did not read. inspect_state
 *   reports only what the underlying mallTileField / mallPlanes / mallVideoPlayer
 *   APIs return; missing APIs are reported as `null`, not fabricated.
 *
 * Session vs catalog separation:
 *   load_videos (Layer 4) creates temporary/session wall state only. It never
 *   mutates mall-video-catalog.json. reset_session clears session overrides.
 */

(function() {
  'use strict';

  var SOURCE_ID = 'pfmall_control_dispatcher';

  var CONFIG = {
    allowedOrigins: [
      (typeof window !== 'undefined' && window.location && window.location.origin) || '',
      'http://localhost:3000',
      'http://localhost:5173',
      'http://127.0.0.1:3000',
      'http://127.0.0.1:5500',
      'http://127.0.0.1:5173'
    ],
    debug: (typeof window !== 'undefined' && window.location && window.location.search &&
            window.location.search.indexOf('debug=1') !== -1) || false
  };

  // Registered event-listener windows (for broadcasting pfmall_event).
  var eventListeners = [];

  // Known event names — Layer 2+ commands emit these.
  var KNOWN_EVENTS = {
    layout_denied: true,
    layout_applied: true,
    video_loaded: true,
    video_failed: true,
    state_changed: true,
    session_reset: true
  };

  // Session override state (populated by load_videos / reset_session in Layer 4).
  // Keeping the structure here so inspect_state can truthfully report whether a
  // session override is active even before Layer 4 wires the load path.
  var sessionState = {
    overrideActive: false,
    overrideAppliedAt: null,
    overrideVideoCount: 0
  };

  function log(level, msg, data) {
    if (!CONFIG.debug && level === 'debug') return;
    var prefix = '[pfMALLDispatcher:' + level.toUpperCase() + ']';
    if (data !== undefined) {
      console.log(prefix, msg, data);
    } else {
      console.log(prefix, msg);
    }
  }

  function isAllowedOrigin(origin) {
    if (!origin) return false;
    if (typeof window !== 'undefined' && window.location && origin === window.location.origin) {
      return true;
    }
    return CONFIG.allowedOrigins.indexOf(origin) !== -1;
  }

  function nowIso() {
    try {
      return new Date().toISOString();
    } catch (_e) {
      return null;
    }
  }

  // ---------- Safe reads from underlying APIs ----------
  // Every reader returns null if the underlying API is missing or throws.
  // Truth-signalling: we never invent state that wasn't read.

  function safeCall(fn) {
    try {
      return fn();
    } catch (_e) {
      return null;
    }
  }

  function readTileFieldState() {
    var tf = (typeof window !== 'undefined') ? window.mallTileField : null;
    if (!tf) return null;
    return {
      density: safeCall(function() { return typeof tf.getDensity === 'function' ? tf.getDensity() : null; }),
      device_policy: safeCall(function() { return typeof tf.getDevicePolicy === 'function' ? tf.getDevicePolicy() : null; }),
      expanded: safeCall(function() { return typeof tf.isExpanded === 'function' ? tf.isExpanded() : null; }),
      expanded_index: safeCall(function() { return typeof tf.getExpandedIndex === 'function' ? tf.getExpandedIndex() : null; }),
      playing_index: safeCall(function() { return typeof tf.getPlayingIndex === 'function' ? tf.getPlayingIndex() : null; }),
      motion_mode: safeCall(function() { return typeof tf.getMotionMode === 'function' ? tf.getMotionMode() : null; }),
      projection: safeCall(function() { return typeof tf.getProjection === 'function' ? tf.getProjection() : null; }),
      field_scope: safeCall(function() { return typeof tf.getFieldScope === 'function' ? tf.getFieldScope() : null; }),
      catalog_length: safeCall(function() {
        if (typeof tf.getCatalog !== 'function') return null;
        var c = tf.getCatalog();
        return (c && typeof c.length === 'number') ? c.length : null;
      })
    };
  }

  function readPlanesState() {
    var mp = (typeof window !== 'undefined') ? window.mallPlanes : null;
    if (!mp) return null;
    return {
      open: safeCall(function() { return typeof mp.isOpen === 'function' ? mp.isOpen() : null; }),
      active_index: safeCall(function() { return typeof mp.getActiveIndex === 'function' ? mp.getActiveIndex() : null; })
    };
  }

  function readVideoPlayerState() {
    var vp = (typeof window !== 'undefined') ? window.mallVideoPlayer : null;
    if (!vp) return null;
    return {
      open: safeCall(function() { return typeof vp.isOpen === 'function' ? vp.isOpen() : null; }),
      foundup_id: safeCall(function() { return typeof vp.getFoundUpId === 'function' ? vp.getFoundUpId() : null; }),
      current_index: safeCall(function() { return typeof vp.getCurrentIndex === 'function' ? vp.getCurrentIndex() : null; }),
      queue_length: safeCall(function() { return typeof vp.getQueueLength === 'function' ? vp.getQueueLength() : null; })
    };
  }

  // ---------- Command handlers ----------

  function cmdInspectState(_payload) {
    return {
      status: 'ok',
      result: {
        tile_field: readTileFieldState(),
        planes: readPlanesState(),
        video_player: readVideoPlayerState(),
        session: {
          override_active: sessionState.overrideActive,
          override_applied_at: sessionState.overrideAppliedAt,
          override_video_count: sessionState.overrideVideoCount
        }
      }
    };
  }

  // Layer 2: set_layout — delegates density change to mallTileField.requestDensity,
  // which enforces the existing device policy (phones cannot force desktop presets).
  // On policy rejection the dispatcher returns status='denied' (distinct from 'error'
  // so agents can tell "policy said no" from "command was malformed or API absent").
  function cmdSetLayout(payload) {
    payload = payload || {};
    var preset = payload.preset;
    var source = (typeof payload.source === 'string' && payload.source) ? payload.source : 'pfmall_command';

    if (typeof preset !== 'string' || !preset) {
      return {
        status: 'error',
        error: {
          code: 'invalid_payload',
          message: 'set_layout requires payload.preset as a non-empty string'
        }
      };
    }

    var tf = (typeof window !== 'undefined') ? window.mallTileField : null;
    if (!tf || typeof tf.requestDensity !== 'function') {
      return {
        status: 'error',
        error: {
          code: 'api_unavailable',
          message: 'mallTileField.requestDensity not available'
        }
      };
    }

    var outcome = safeCall(function() {
      return tf.requestDensity(preset, { source: source });
    });

    if (!outcome || typeof outcome !== 'object' || typeof outcome.applied !== 'boolean') {
      return {
        status: 'error',
        error: {
          code: 'runtime_failure',
          message: 'requestDensity returned no valid outcome'
        }
      };
    }

    var policy = safeCall(function() {
      return typeof tf.getDevicePolicy === 'function' ? tf.getDevicePolicy() : null;
    });
    var deviceClass = (outcome.deviceClass !== undefined && outcome.deviceClass !== null)
      ? outcome.deviceClass
      : (policy && policy.deviceClass) || null;

    if (outcome.applied === true) {
      emitEvent('layout_applied', {
        preset: outcome.preset || preset,
        source: source,
        device_class: deviceClass
      });
      emitEvent('state_changed', {
        change: 'layout',
        preset: outcome.preset || preset
      });
      return {
        status: 'ok',
        result: {
          applied: true,
          preset: outcome.preset || preset,
          source: source,
          device_class: deviceClass
        }
      };
    }

    // Policy denial — distinct from 'error' so agents can branch on this cleanly.
    emitEvent('layout_denied', {
      preset: preset,
      source: source,
      reason: outcome.reason || 'policy_denied',
      device_class: deviceClass,
      allowed: (policy && policy.allowed) || null
    });
    return {
      status: 'denied',
      result: {
        applied: false,
        preset: preset,
        reason: outcome.reason || 'policy_denied',
        device_class: deviceClass,
        allowed: (policy && policy.allowed) || null
      }
    };
  }

  // Layer 3+ commands — registered but return not_implemented until wired.
  // Keeping the surface stable lets tests exercise rejection shape early.
  function cmdNotImplemented(command) {
    return {
      status: 'error',
      error: {
        code: 'not_implemented',
        message: 'Command not yet implemented in current layer: ' + command
      }
    };
  }

  var HANDLERS = {
    inspect_state: cmdInspectState,
    set_layout: cmdSetLayout,
    load_videos: function(p) { return cmdNotImplemented('load_videos'); },
    play_tile: function(p) { return cmdNotImplemented('play_tile'); },
    expand_tile: function(p) { return cmdNotImplemented('expand_tile'); },
    collapse_tile: function(p) { return cmdNotImplemented('collapse_tile'); },
    reset_session: function(p) { return cmdNotImplemented('reset_session'); }
  };

  function executeCommand(command, payload) {
    if (typeof command !== 'string' || !command) {
      return {
        status: 'error',
        error: { code: 'invalid_command', message: 'command must be a non-empty string' }
      };
    }
    var handler = HANDLERS[command];
    if (!handler) {
      return {
        status: 'error',
        error: { code: 'unknown_command', message: 'Unknown command: ' + command }
      };
    }
    try {
      var out = handler(payload || {});
      // Handlers must return { status, result? , error? }.
      if (!out || typeof out !== 'object' || typeof out.status !== 'string') {
        return {
          status: 'error',
          error: { code: 'handler_contract_violation', message: 'handler did not return a valid response object' }
        };
      }
      return out;
    } catch (e) {
      return {
        status: 'error',
        error: { code: 'handler_exception', message: String(e && e.message ? e.message : e) }
      };
    }
  }

  function buildResponse(request, handlerResult) {
    var resp = {
      type: 'pfmall_response',
      source: SOURCE_ID,
      target: request && request.source ? request.source : null,
      request_id: request && request.request_id ? request.request_id : null,
      status: handlerResult.status
    };
    if (handlerResult.status === 'error') {
      resp.error = handlerResult.error;
    } else {
      resp.result = handlerResult.result;
    }
    return resp;
  }

  // ---------- Event emission ----------

  function emitEvent(eventName, payload) {
    if (!KNOWN_EVENTS[eventName]) {
      log('warn', 'Emitting unknown event name', eventName);
    }
    var envelope = {
      type: 'pfmall_event',
      source: SOURCE_ID,
      event: eventName,
      payload: payload || {},
      timestamp: nowIso()
    };
    // Broadcast to registered listener windows (postMessage).
    for (var i = 0; i < eventListeners.length; i++) {
      try {
        var listener = eventListeners[i];
        if (listener && typeof listener.postMessage === 'function') {
          listener.postMessage(envelope, listener._origin || '*');
        }
      } catch (_e) {
        // non-fatal; continue broadcasting
      }
    }
    // Also dispatch a CustomEvent so same-origin shell code can subscribe.
    try {
      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function' &&
          typeof CustomEvent === 'function') {
        window.dispatchEvent(new CustomEvent('pfmall:' + eventName, { detail: envelope }));
      }
    } catch (_e) {
      // Some sandboxes lack CustomEvent — non-fatal.
    }
    return envelope;
  }

  // ---------- Message handling ----------

  function handleMessage(event) {
    if (!event) return;
    if (!isAllowedOrigin(event.origin)) {
      log('debug', 'Ignored message from disallowed origin', event.origin);
      return;
    }
    var data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type !== 'pfmall_command') return;

    log('info', 'Received pfmall_command', { command: data.command, request_id: data.request_id });

    var handlerResult = executeCommand(data.command, data.payload);
    var response = buildResponse(data, handlerResult);

    if (event.source && typeof event.source.postMessage === 'function') {
      try {
        event.source.postMessage(response, event.origin);
      } catch (_e) {
        // non-fatal
      }
    }
  }

  // ---------- Public API ----------

  function registerEventListener(targetWindow, opts) {
    if (!targetWindow || typeof targetWindow.postMessage !== 'function') {
      return { ok: false, error: 'targetWindow must expose postMessage' };
    }
    targetWindow._origin = (opts && opts.origin) ? String(opts.origin) : '*';
    if (eventListeners.indexOf(targetWindow) === -1) {
      eventListeners.push(targetWindow);
    }
    return { ok: true, count: eventListeners.length };
  }

  function clearEventListeners() {
    eventListeners.length = 0;
  }

  function dispatchLocal(command, payload) {
    // Programmatic entry for same-origin shell code and tests.
    // Bypasses postMessage envelope but shares the same executor.
    return executeCommand(command, payload);
  }

  function addAllowedOrigin(origin) {
    if (typeof origin === 'string' && CONFIG.allowedOrigins.indexOf(origin) === -1) {
      CONFIG.allowedOrigins.push(origin);
    }
  }

  function getConfig() {
    return {
      allowedOrigins: CONFIG.allowedOrigins.slice(),
      debug: CONFIG.debug,
      knownEvents: Object.keys(KNOWN_EVENTS),
      commands: Object.keys(HANDLERS)
    };
  }

  // Exposed for Layer 2+ to mutate session state and for tests.
  function _setSessionOverride(active, videoCount) {
    sessionState.overrideActive = !!active;
    sessionState.overrideVideoCount = active ? (videoCount || 0) : 0;
    sessionState.overrideAppliedAt = active ? nowIso() : null;
  }

  function init() {
    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('message', handleMessage, false);
    }
    log('info', 'pfMALL Control Dispatcher initialized');

    if (typeof window !== 'undefined') {
      window.pfmallControlDispatcher = {
        dispatch: dispatchLocal,
        emitEvent: emitEvent,
        registerEventListener: registerEventListener,
        clearEventListeners: clearEventListeners,
        addAllowedOrigin: addAllowedOrigin,
        getConfig: getConfig,
        _setSessionOverride: _setSessionOverride,
        _handleMessage: handleMessage  // exposed for tests
      };
    }
  }

  if (typeof document !== 'undefined' && document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
