/**
 * Mall State Restore — Lightweight persistence for mall interaction state.
 *
 * Persists and restores:
 *   - Projection mode (default, alpha, readiness, category)
 *   - Field scope (personal, creator, category, tag + query)
 *   - Scroll position (tile field wrapper scroll offset)
 *
 * Storage: localStorage only. Fails silently if unavailable.
 * Does NOT touch mall-tile-field.js internals — only reads/writes via
 * the public window.mallTileField API.
 *
 * Usage:
 *   // After mallTileField.initialize(catalog):
 *   window.mallStateRestore.restore();
 *
 *   // The helper auto-saves on projection/scope/scroll changes.
 *   // Or call explicitly:
 *   window.mallStateRestore.save();
 */
(function() {
  'use strict';

  var STORAGE_KEY = 'pfmall_mall_state';
  var SCROLL_DEBOUNCE_MS = 300;
  var scrollTimer = null;
  var initialized = false;

  // ─── Storage Helpers ───

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      // Private mode or quota — fail silently
    }
  }

  // ─── Capture Current State ───

  function captureState() {
    var state = {};
    var tf = window.mallTileField;
    if (!tf) return state;

    // Projection
    if (typeof tf.getProjection === 'function') {
      state.projection = tf.getProjection();
    }

    // Field scope
    if (typeof tf.getFieldScope === 'function') {
      var scope = tf.getFieldScope();
      if (scope) {
        state.fieldScope = scope;
      }
    }

    // Scroll position (from tile field wrapper)
    var wrapper = document.querySelector('.mall-tile-field-wrapper');
    if (wrapper) {
      state.scrollTop = wrapper.scrollTop;
      state.scrollLeft = wrapper.scrollLeft;
    }

    return state;
  }

  // ─── Save (Public) ───

  function save() {
    var state = captureState();
    saveState(state);
  }

  // ─── Restore (Public) ───

  function restore() {
    var state = loadState();
    if (!state) return false;

    var tf = window.mallTileField;
    if (!tf) return false;

    var restored = false;

    // Restore field scope first (it resets projection to default)
    if (state.fieldScope && typeof tf.setFieldScope === 'function') {
      tf.setFieldScope(state.fieldScope);
      restored = true;
    }

    // Restore projection (after scope, since scope resets it)
    if (state.projection && state.projection !== 'default' && typeof tf.setProjection === 'function') {
      // Only restore non-default if scope didn't just reset it
      if (!state.fieldScope) {
        tf.setProjection(state.projection);
        restored = true;
      }
    }

    // Restore scroll position (deferred to next frame for layout)
    if (state.scrollTop || state.scrollLeft) {
      requestAnimationFrame(function() {
        var wrapper = document.querySelector('.mall-tile-field-wrapper');
        if (wrapper) {
          if (state.scrollTop) wrapper.scrollTop = state.scrollTop;
          if (state.scrollLeft) wrapper.scrollLeft = state.scrollLeft;
        }
      });
      restored = true;
    }

    return restored;
  }

  // ─── Clear (Public) ───

  function clear() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      // fail silently
    }
  }

  // ─── Auto-Save Binding ───

  function bindAutoSave() {
    if (initialized) return;
    initialized = true;

    // Save on projection chip clicks
    document.addEventListener('click', function(e) {
      if (e.target.closest && e.target.closest('.mall-projection-chip')) {
        // Defer save to allow mallTileField to update state first
        setTimeout(save, 50);
      }
    });

    // Save on scroll (debounced)
    var wrapper = document.querySelector('.mall-tile-field-wrapper');
    if (wrapper) {
      wrapper.addEventListener('scroll', function() {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(save, SCROLL_DEBOUNCE_MS);
      }, { passive: true });
    }

    // Save on visibility change (user leaves tab or locks phone)
    document.addEventListener('visibilitychange', function() {
      if (document.visibilityState === 'hidden') {
        save();
      }
    });

    // Save on beforeunload (navigation away)
    window.addEventListener('beforeunload', save);
  }

  // ─── Public API ───

  window.mallStateRestore = {
    /** Save current mall state to localStorage. */
    save: save,

    /** Restore mall state from localStorage. Returns true if state was applied. */
    restore: restore,

    /** Clear saved mall state. */
    clear: clear,

    /** Bind auto-save listeners. Called once after mall initialization. */
    bindAutoSave: bindAutoSave,

    /** Get stored state without applying it (for inspection/testing). */
    peek: loadState
  };

})();
