/**
 * Mall State Restore — Lightweight persistence for mall interaction state.
 *
 * Persists and restores:
 *   - Projection mode (default, alpha, readiness, category)
 *   - Field scope (personal, creator, category, tag, catalog query)
 *   - Ordinary Mall layout and independent category row positions
 *   - Scroll position (tile field wrapper scroll offset)
 *
 * Video and registered product views use separate localStorage namespaces.
 * Explicit account handoff uses a bounded, single-use sessionStorage record.
 * Storage failure never blocks discovery or admission.
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

  var STORAGE_KEY = 'pfmall_mall_state_v1';
  var PRODUCT_KEYS = { move2japan: 'pfmall_product_move2japan_state_v1' };
  var selectedProduct = null;
  var RETURN_KEY = 'pfmall_product_return_v1';
  var RETURN_TTL_MS = 15 * 60 * 1000;
  var FILTER_KEYS = ['q', 'country', 'prefecture', 'city', 'locality', 'max', 'land', 'sort', 'group', 'large', 'tour'];
  var SCROLL_DEBOUNCE_MS = 300;
  var scrollTimer = null;
  var initialized = false;

  // Valid projection values for state validation
  var VALID_PROJECTIONS = ['default', 'alpha', 'readiness', 'category'];

  function storageKey() {
    return selectedProduct ? PRODUCT_KEYS[selectedProduct] : STORAGE_KEY;
  }

  function selectProduct(product) {
    if (product !== null && (typeof product !== 'string' || !Object.prototype.hasOwnProperty.call(PRODUCT_KEYS, product))) return false;
    clearTimeout(scrollTimer);
    scrollTimer = null;
    selectedProduct = product;
    return true;
  }

  function safeFilter(key, value) {
    if (typeof value !== 'string') return '';
    value = value.replace(/[\u0000-\u001f\u007f]/g, ' ').trim();
    if (['q', 'prefecture', 'city', 'locality'].indexOf(key) !== -1) return value.slice(0, 80);
    if (key === 'country') return /^[a-z]{2}$/i.test(value) ? value.toUpperCase() : '';
    if (key === 'max') {
      var amount = Number(value);
      return value && Number.isFinite(amount) && amount >= 0 && amount <= 1e12 ? String(amount) : '';
    }
    var allowed = {
      land: ['with_land', 'no_land', 'unknown'],
      sort: ['price_asc', 'price_desc', 'land_desc', 'town'],
      group: ['city', 'locality'], large: ['1'], tour: ['1']
    };
    return allowed[key] && allowed[key].indexOf(value) !== -1 ? value : '';
  }

  /** Capture filters from this actual product view, never a caller-supplied URL. */
  function rememberProductReturn(product) {
    if (product !== 'move2japan' || selectedProduct !== product) return false;
    try {
      var url = new URL(window.location.href);
      if ((url.pathname !== '/member/' && url.pathname !== '/member/index.html') ||
          url.searchParams.getAll('foundup').length !== 1 || url.searchParams.get('foundup') !== product) return false;
      var filters = {};
      FILTER_KEYS.forEach(function(key) {
        var values = url.searchParams.getAll(key);
        if (key === 'city' && !values.length) values = url.searchParams.getAll('area');
        var value = values.length === 1 ? safeFilter(key, values[0]) : '';
        if (value) filters[key] = value;
      });
      sessionStorage.setItem(RETURN_KEY, JSON.stringify({ product_id: product, created_at: Date.now(), filters: filters }));
      return true;
    } catch (e) { return false; }
  }

  /** Called only by the existing admitted member path, after its actual gate. */
  function consumeProductReturn() {
    try {
      var raw = sessionStorage.getItem(RETURN_KEY);
      sessionStorage.removeItem(RETURN_KEY);
      if (!raw || raw.length > 4096) return null;
      var record = JSON.parse(raw);
      if (!record || record.product_id !== 'move2japan' ||
          Object.keys(record).some(function(key) { return ['product_id', 'created_at', 'filters'].indexOf(key) === -1; }) ||
          !Number.isFinite(record.created_at) || Date.now() < record.created_at || Date.now() - record.created_at > RETURN_TTL_MS ||
          !record.filters || typeof record.filters !== 'object' || Array.isArray(record.filters) ||
          Object.keys(record.filters).some(function(key) { return FILTER_KEYS.indexOf(key) === -1; })) return null;
      var query = new URLSearchParams({ foundup: 'move2japan' });
      FILTER_KEYS.forEach(function(key) {
        var value = safeFilter(key, record.filters[key]);
        if (value) query.set(key, value);
      });
      return '/member/?' + query.toString() + '#account';
    } catch (e) { return null; }
  }

  // ─── Storage Helpers ───

  function loadState() {
    try {
      var raw = localStorage.getItem(storageKey());
      if (raw && raw.length > 131072) return null;
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(storageKey(), JSON.stringify(state));
    } catch (e) {
      // Private mode or quota — fail silently
    }
  }

  // ─── Capture Current State ───

  function captureState() {
    var state = {};
    var tf = window.mallTileField;
    if (!tf) return selectedProduct ? null : state;

    if (selectedProduct) {
      var geographic = typeof tf.getGeographicState === 'function' ? tf.getGeographicState() : null;
      // Do not erase a saved product position before its public catalog loads.
      if (!geographic || geographic.foundup_id !== selectedProduct) return null;
      return { schema_version: 'pfmall_product_state.v1', product_id: selectedProduct, geographic: geographic };
    }

    // Projection
    if (typeof tf.getProjection === 'function') {
      state.projection = tf.getProjection();
    }

    if (typeof tf.getLayoutMode === 'function') state.layoutMode = tf.getLayoutMode();
    if (typeof tf.getRowOffsets === 'function') state.rowOffsets = tf.getRowOffsets();

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
    if (state) saveState(state);
  }

  // ─── Restore (Public) ───

  function isValidState(state) {
    if (!state || typeof state !== 'object') return false;
    if (selectedProduct) {
      return !Array.isArray(state) && state.schema_version === 'pfmall_product_state.v1' &&
        state.product_id === selectedProduct && state.geographic && typeof state.geographic === 'object' &&
        state.geographic.foundup_id === selectedProduct &&
        Object.keys(state).every(function(key) { return ['schema_version', 'product_id', 'geographic'].indexOf(key) !== -1; });
    }
    // Reject if projection is present but not a known value
    if (state.projection && VALID_PROJECTIONS.indexOf(state.projection) === -1) return false;
    // Reject if fieldScope is present but not an object
    if (state.fieldScope && typeof state.fieldScope !== 'object') return false;
    // Reject if scroll values are non-numeric
    if (state.scrollTop !== undefined && typeof state.scrollTop !== 'number') return false;
    if (state.scrollLeft !== undefined && typeof state.scrollLeft !== 'number') return false;
    return true;
  }

  function restore() {
    var state = loadState();
    if (!state) return false;

    // Validate stored state shape — clear and bail if corrupt
    if (!isValidState(state)) {
      clear();
      return false;
    }

    var tf = window.mallTileField;
    if (!tf) return false;

    if (selectedProduct) {
      return typeof tf.restoreGeographicState === 'function' && tf.restoreGeographicState(state.geographic) === true;
    }

    var restored = false;
    if (state.layoutMode && typeof tf.setLayoutMode === 'function') tf.setLayoutMode(state.layoutMode);
    if (state.rowOffsets && typeof tf.restoreRowOffsets === 'function') {
      requestAnimationFrame(function() {
        if (!selectedProduct) tf.restoreRowOffsets(state.rowOffsets);
      });
    }

    // Restore field scope first (it resets projection to default)
    if (state.fieldScope && typeof tf.setFieldScope === 'function') {
      tf.setFieldScope(state.fieldScope);
      restored = true;
    } else if (!state.fieldScope && typeof tf.clearFieldScope === 'function') {
      tf.clearFieldScope();
    }

    // Restore projection (after scope, since scope may reset it to default)
    if (state.projection && state.projection !== 'default' && typeof tf.setProjection === 'function') {
      tf.setProjection(state.projection);
      restored = true;
    }

    // Restore scroll position (deferred to next frame for layout)
    if (state.scrollTop || state.scrollLeft) {
      requestAnimationFrame(function() {
        // A product selection can occur before this deferred video restoration.
        if (selectedProduct) return;
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
      localStorage.removeItem(storageKey());
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
      if (!e.target.closest) return;
      if (e.target.closest('.mall-projection-chip')) {
        // Defer save to allow mallTileField to update state first
        setTimeout(save, 50);
      }
      // Save on Red Dog scope mutations (personal mall, category, tag, search)
      if (e.target.closest('[data-reddog-populate-mall]') ||
          e.target.closest('[data-reddog-personal-mall]') ||
          e.target.closest('[data-reddog-category]') ||
          e.target.closest('[data-reddog-search-clear]')) {
        setTimeout(save, 50);
      }
    });

    // Save on Red Dog tag select changes (delegated — element injected later by account-concierge)
    document.addEventListener('change', function(e) {
      if (e.target.matches && e.target.matches('[data-reddog-tag-select]')) {
        setTimeout(save, 50);
      }
    });

    // Save on Red Dog search input (delegated + debounced — element injected later)
    document.addEventListener('input', function(e) {
      if (e.target.matches && e.target.matches('[data-reddog-search-input]')) {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(save, SCROLL_DEBOUNCE_MS);
      }
    });

    // Save on scroll (debounced)
    var wrapper = document.querySelector('.mall-tile-field-wrapper');
    if (wrapper) {
      wrapper.addEventListener('scroll', function() {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(save, SCROLL_DEBOUNCE_MS);
      }, { passive: true, capture: true });
    }

    // Native horizontal row scroll does not bubble. Capture just the shared
    // product tracks so dynamic row replacement keeps the same one listener.
    document.addEventListener('scroll', function(e) {
      if (!selectedProduct || !e.target.matches || !e.target.matches('.mall-field-group-track')) return;
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(save, SCROLL_DEBOUNCE_MS);
    }, { capture: true, passive: true });

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
    /** Select a registered product namespace before loading its catalog. */
    selectProduct: selectProduct,

    /** Remember this product's filters for an explicit account handoff. */
    rememberProductReturn: rememberProductReturn,

    /** Consume a safe, short-lived product return after real member admission. */
    consumeProductReturn: consumeProductReturn,

    /** Save current mall state to localStorage. */
    save: save,

    /** Restore mall state from localStorage. Returns true if state was applied. */
    restore: restore,

    /** Clear saved mall state. */
    clear: clear,

    /** Bind auto-save listeners. Called once after mall initialization. */
    bindAutoSave: bindAutoSave,

    /** Get stored state without applying it (for inspection/testing). */
    peek: loadState,

    /** Validate a state object shape (for testing). */
    isValid: isValidState
  };

})();
