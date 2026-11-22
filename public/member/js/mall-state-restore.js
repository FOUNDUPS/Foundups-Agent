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
  var selectedVideoScope = null;
  var RETURN_KEY = 'pfmall_product_return_v1';
  var RETURN_TTL_MS = 15 * 60 * 1000;
  var FILTER_KEYS = ['q', 'country', 'prefecture', 'city', 'locality', 'max', 'land', 'sort', 'group', 'large', 'tour'];
  var SCROLL_DEBOUNCE_MS = 300;
  // Reuse the ordinary Mall history contract from the existing restoration
  // owner. These entries reference a live page-local player, never resources.
  var BROWSE_HISTORY = 'pfmallMallBrowse';
  var VIEW_HISTORY = 'pfmallMallView';
  var restoringHistory = false;

  function browseWrapper() {
    // The property template also contains a wrapper; retain the active Mall's position.
    return document.querySelector('#mallTileField')?.parentElement ||
      document.querySelector('.mall-tile-field-wrapper');
  }
  var scrollTimer = null;
  var initialized = false;

  // Valid projection values for state validation
  var VALID_PROJECTIONS = ['default', 'alpha', 'readiness', 'category'];

  function storageKey() {
    if (selectedVideoScope) return 'pfmall_video_scope_' + selectedVideoScope + '_v1';
    return selectedProduct ? PRODUCT_KEYS[selectedProduct] : STORAGE_KEY;
  }

  function stateStorage() {
    return selectedVideoScope ? sessionStorage : localStorage;
  }

  function selectVideoScope(scope) {
    if (selectedProduct || typeof scope !== 'string' || !/^[a-z][a-z0-9_]{2,49}$/.test(scope)) return false;
    clearTimeout(scrollTimer);
    scrollTimer = null;
    selectedVideoScope = scope;
    return true;
  }

  function selectProduct(product) {
    if (selectedVideoScope || (product !== null && (typeof product !== 'string' || !Object.prototype.hasOwnProperty.call(PRODUCT_KEYS, product)))) return false;
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

  function storeProductReturn(product, filters) {
    sessionStorage.setItem(RETURN_KEY, JSON.stringify({ product_id: product, created_at: Date.now(), filters: filters }));
    return true;
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
      return storeProductReturn(product, filters);
    } catch (e) { return false; }
  }

  /** Remember a requested member video or FoundUp entry view through sign-in redirect. */
  function rememberMemberVideoReturn() {
    try {
      var scope = window.mallVideoProjection?.resolveMember(window.location);
      if (scope) return storeProductReturn(scope, {});
      var entryId = window.mallVideoProjection?.resolveMemberEntry?.(window.location);
      return !!entryId && storeProductReturn('enter', { enter: entryId });
    } catch (e) { return false; }
  }

  /** Called only by the existing admitted member path, after its actual gate. */
  function consumeProductReturn() {
    try {
      var raw = sessionStorage.getItem(RETURN_KEY);
      sessionStorage.removeItem(RETURN_KEY);
      if (!raw || raw.length > 4096) return null;
      var record = JSON.parse(raw);
      if (!record ||
          Object.keys(record).some(function(key) { return ['product_id', 'created_at', 'filters'].indexOf(key) === -1; }) ||
          !Number.isFinite(record.created_at) || Date.now() < record.created_at || Date.now() - record.created_at > RETURN_TTL_MS ||
          !record.filters || typeof record.filters !== 'object' || Array.isArray(record.filters)) return null;
      if (record.product_id === 'enter') {
        var filterKeys = Object.keys(record.filters);
        if (filterKeys.length !== 1 || filterKeys[0] !== 'enter') return null;
        return window.mallVideoProjection?.memberEntryPath?.(record.filters.enter) || null;
      }
      if (record.product_id !== 'move2japan') {
        if (Object.keys(record.filters).length) return null;
        return window.mallVideoProjection?.memberPath(record.product_id) || null;
      }
      if (Object.keys(record.filters).some(function(key) { return FILTER_KEYS.indexOf(key) === -1; })) return null;
      var query = new URLSearchParams({ foundup: 'move2japan' });
      FILTER_KEYS.forEach(function(key) {
        var value = safeFilter(key, record.filters[key]);
        if (value) query.set(key, value);
      });
      return '/member/?' + query.toString() + '#account';
    } catch (e) { return null; }
  }

  // Admission intent is navigation context only. It never grants membership,
  // editor capability or permission to submit. Browse state stays with save().
  var ADMISSION_KEY = 'pfmall_admission_intent_v1';
  var VIDEO_OPTIONS_KEY = 'pfmall_video_options_v1';
  var admissionStorageFailed = false;
  var videoOptionsMemory = defaultVideoOptions();
  var videoOptionsStorageFailed = false;
  var videoOptionSubscribers = [];

  function ownDataRecord(value, keys) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    var prototype = Object.getPrototypeOf(value);
    if (prototype !== null) {
      var constructor = Object.getOwnPropertyDescriptor(prototype, 'constructor');
      if (Object.getPrototypeOf(prototype) !== null || !constructor ||
          !Object.prototype.hasOwnProperty.call(constructor, 'value') ||
          typeof constructor.value !== 'function' ||
          Function.prototype.toString.call(constructor.value) !== Function.prototype.toString.call(Object) ||
          constructor.value.prototype !== prototype) return false;
    }
    return Reflect.ownKeys(value).every(function(key) {
      var descriptor = Object.getOwnPropertyDescriptor(value, key);
      return typeof key === 'string' && keys.indexOf(key) !== -1 && descriptor &&
        Object.prototype.hasOwnProperty.call(descriptor, 'value') && descriptor.enumerable;
    });
  }

  function safeIntentFoundUp(value) {
    return typeof value === 'string' && /^[a-z][a-z0-9_-]{0,63}$/.test(value) &&
      ['__proto__', 'constructor', 'prototype'].indexOf(value) === -1;
  }

  function safeAdmissionPath(value) {
    if (typeof value !== 'string' || value.length > 512 || /[\\\u0000-\u0020\u007f]/.test(value) ||
        !/^\/member(?:\/|\/index\.html)?(?:[?#]|$)/.test(value)) return null;
    try {
      var url = new URL(value, window.location.origin);
      if (url.origin !== window.location.origin ||
          ['/member', '/member/', '/member/index.html'].indexOf(url.pathname) === -1 ||
          ['','#account','#red-dog'].indexOf(url.hash) === -1) return null;
      var keys = Array.from(url.searchParams.keys());
      if (keys.length > 1 || keys.some(function(key) { return key !== 'foundup' && key !== 'creator'; })) return null;
      if (keys.length) {
        var key = keys[0];
        var target = url.searchParams.get(key);
        if (!safeIntentFoundUp(target) || (key === 'creator' && target !== 'move2japan')) return null;
      }
      return url.pathname + url.search + url.hash;
    } catch (error) { return null; }
  }

  function validAdmissionRecord(record) {
    if (!ownDataRecord(record, ['version', 'createdAt', 'action', 'foundupId', 'videoId', 'returnPath']) ||
        !['version', 'createdAt', 'action', 'returnPath'].every(function(key) { return Object.prototype.hasOwnProperty.call(record, key); }) ||
        record.version !== 1 || !Number.isSafeInteger(record.createdAt) || record.createdAt < 0 ||
        Date.now() < record.createdAt || Date.now() - record.createdAt >= RETURN_TTL_MS ||
        ['add-foundup', 'add-video', 'account'].indexOf(record.action) === -1 ||
        typeof record.returnPath !== 'string' || safeAdmissionPath(record.returnPath) !== record.returnPath) return false;
    if (Object.prototype.hasOwnProperty.call(record, 'foundupId') && !safeIntentFoundUp(record.foundupId)) return false;
    if (record.action === 'add-video' && !safeIntentFoundUp(record.foundupId)) return false;
    if (Object.prototype.hasOwnProperty.call(record, 'videoId') &&
        (!record.foundupId || typeof record.videoId !== 'string' || !/^[A-Za-z0-9_-]{11}$/.test(record.videoId))) return false;
    var scope = new URL(record.returnPath, window.location.origin).searchParams.get('foundup');
    return !scope || !record.foundupId || scope === record.foundupId;
  }

  function copyAdmission(record) {
    return record ? JSON.parse(JSON.stringify(record)) : null;
  }

  function rememberAdmissionIntent(input) {
    try { save(); } catch (error) { /* Discovery storage is optional. */ }
    try {
      if (!ownDataRecord(input, ['action', 'foundupId', 'videoId', 'returnPath']) ||
          !Object.prototype.hasOwnProperty.call(input, 'action')) return false;
      var path = Object.prototype.hasOwnProperty.call(input, 'returnPath') ? input.returnPath :
        window.location.pathname + window.location.search + window.location.hash;
      var record = { version: 1, createdAt: Date.now(), action: input.action, returnPath: safeAdmissionPath(path) };
      ['foundupId', 'videoId'].forEach(function(key) {
        if (Object.prototype.hasOwnProperty.call(input, key)) record[key] = input[key];
      });
      if (!validAdmissionRecord(record)) return false;
      try {
        sessionStorage.setItem(ADMISSION_KEY, JSON.stringify(record));
        admissionStorageFailed = false;
      } catch (error) {
        admissionStorageFailed = true;
        try { sessionStorage.removeItem(ADMISSION_KEY); } catch (removeError) { /* Failed handoff stays blocked. */ }
        return false;
      }
      return true;
    } catch (error) { return false; }
  }

  function peekAdmissionIntent() {
    if (admissionStorageFailed) return null;
    var raw;
    try { raw = sessionStorage.getItem(ADMISSION_KEY); }
    catch (error) { return null; }
    if (!raw || raw.length > 2048) return null;
    try {
      var record = JSON.parse(raw);
      return validAdmissionRecord(record) ? copyAdmission(record) : null;
    } catch (error) { return null; }
  }

  function consumeAdmissionIntent() {
    var record = peekAdmissionIntent();
    if (!admissionStorageFailed) {
      try { sessionStorage.removeItem(ADMISSION_KEY); }
      catch (error) { admissionStorageFailed = true; return null; }
    }
    return record;
  }

  function defaultVideoOptions() {
    return { autoplayNext: true, frameDestination: 'wikitube', collapseDestination: 'mall', revealSelectedPlayer: true,
      tileTapDestination: 'floating' };
  }

  function validVideoOptions(options, partial) {
    var legacyKeys = ['autoplayNext', 'frameDestination', 'collapseDestination', 'revealSelectedPlayer'];
    if (!ownDataRecord(options, legacyKeys.concat('tileTapDestination'))) return false;
    if (!partial && !legacyKeys.every(function(key) { return Object.prototype.hasOwnProperty.call(options, key); })) return false;
    return Object.keys(options).every(function(key) {
      if (key === 'autoplayNext' || key === 'revealSelectedPlayer') return typeof options[key] === 'boolean';
      if (key === 'tileTapDestination') return ['floating', 'wikitube', 'full-video'].indexOf(options[key]) !== -1;
      return (key === 'frameDestination' ? ['wikitube', 'full-video'] : ['wikitube', 'mall']).indexOf(options[key]) !== -1;
    });
  }

  function decodeVideoOptions(raw) {
    if (typeof raw !== 'string' || raw.length > 1024) return null;
    try {
      var record = JSON.parse(raw);
      if (!ownDataRecord(record, ['version', 'options']) || Object.keys(record).length !== 2 || record.version !== 1 ||
          !ownDataRecord(record.options, ['autoplayNext', 'frameDestination', 'collapseDestination', 'revealSelectedPlayer', 'tileTapDestination'])) return null;
      var options = Object.assign({}, record.options);
      // Old frame/collapse settings describe different actions. Reading a v1
      // record supplies only the confirmed tile default, without writing it.
      if (['floating', 'wikitube', 'full-video'].indexOf(options.tileTapDestination) === -1) options.tileTapDestination = 'floating';
      return validVideoOptions(options, false) ? options : null;
    } catch (error) { return null; }
  }

  function getVideoOptions() {
    if (videoOptionsStorageFailed) return Object.assign({}, videoOptionsMemory);
    try {
      var raw = localStorage.getItem(VIDEO_OPTIONS_KEY);
      var options = raw === null ? defaultVideoOptions() : decodeVideoOptions(raw);
      if (options) videoOptionsMemory = Object.assign({}, options);
    } catch (error) { videoOptionsStorageFailed = true; }
    return Object.assign({}, videoOptionsMemory);
  }

  function notifyVideoOptions() {
    videoOptionSubscribers.slice().forEach(function(subscriber) {
      try { subscriber.callback(Object.assign({}, videoOptionsMemory)); } catch (error) { /* Isolate consumers. */ }
    });
  }

  function setVideoOptions(patch) {
    try {
      if (!validVideoOptions(patch, true)) return false;
      var before = getVideoOptions();
      var next = Object.assign({}, before, patch);
      videoOptionsMemory = next;
      try {
        localStorage.setItem(VIDEO_OPTIONS_KEY, JSON.stringify({ version: 1, options: next }));
        videoOptionsStorageFailed = false;
      } catch (error) { videoOptionsStorageFailed = true; }
      if (Object.keys(next).some(function(key) { return next[key] !== before[key]; })) notifyVideoOptions();
      return true;
    } catch (error) { return false; }
  }

  function subscribeVideoOptions(callback) {
    if (typeof callback !== 'function') return null;
    var subscriber = { callback: callback };
    videoOptionSubscribers.push(subscriber);
    return function() {
      var index = videoOptionSubscribers.indexOf(subscriber);
      if (index !== -1) videoOptionSubscribers.splice(index, 1);
    };
  }

  window.addEventListener('storage', function(event) {
    if (event.key !== VIDEO_OPTIONS_KEY) return;
    var options = event.newValue === null ? defaultVideoOptions() : decodeVideoOptions(event.newValue);
    if (!options) return;
    videoOptionsMemory = Object.assign({}, options);
    videoOptionsStorageFailed = false;
    notifyVideoOptions();
  });

  // ─── Storage Helpers ───

  function loadState() {
    try {
      var raw = stateStorage().getItem(storageKey());
      if (raw && raw.length > 131072) return null;
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveState(state) {
    try {
      stateStorage().setItem(storageKey(), JSON.stringify(state));
    } catch (e) {
      // Private mode or quota — fail silently
    }
  }

  // ─── Capture Current State ───

  function captureState() {
    var state = {};
    var tf = window.mallTileField;
    if (!tf) return selectedProduct ? null : state;

    var wrapper = browseWrapper();
    if (selectedVideoScope) {
      return tf.getVideoGridState?.() ||
        (wrapper ? { scrollTop: wrapper.scrollTop, scrollLeft: wrapper.scrollLeft } : null);
    }

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
    if (wrapper) {
      state.scrollTop = wrapper.scrollTop;
      state.scrollLeft = wrapper.scrollLeft;
    }

    // Active video playback continuity (ordinary Mall only; never touches HPC sessionStorage)
    if (typeof tf.getActiveVideo === 'function') {
      var activeVideo = tf.getActiveVideo();
      if (activeVideo) {
        state.activeVideo = activeVideo;
      }
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
    if (selectedVideoScope) {
      var keys = Object.keys(state).filter(function(key) { return key !== 'theater' && key !== 'phoneQuery'; });
      if ('phoneQuery' in state && (typeof state.phoneQuery !== 'string' || state.phoneQuery.length > 300)) return false;
      if ('theater' in state) {
        var theater = state.theater;
        if (!theater || typeof theater !== 'object' || Object.keys(theater).length !== 2 ||
            typeof theater.videoId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(theater.videoId) ||
            typeof theater.query !== 'string' || theater.query.length > 300) return false;
      }
      if (![state.scrollTop, state.scrollLeft].every(function(value) { return Number.isFinite(value) && value >= 0; })) return false;
      if (keys.length === 2) return true; // legacy scoped positions
      return keys.length === 4 && typeof state.anchorVideoId === 'string' &&
        /^[A-Za-z0-9_-]{1,128}$/.test(state.anchorVideoId) && Number.isFinite(state.anchorOffset);
    }
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
    // Validate optional activeVideo shape for ordinary Mall reload continuity
    if (state.activeVideo !== undefined && state.activeVideo !== null) {
      var av = state.activeVideo;
      if (typeof av !== 'object' || Array.isArray(av) ||
          Object.keys(av).some(function(key) { return ['foundupId', 'videoId', 'queueQuery'].indexOf(key) === -1; }) ||
          typeof av.foundupId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(av.foundupId) ||
          typeof av.videoId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(av.videoId) ||
          (av.queueQuery !== undefined && (typeof av.queueQuery !== 'string' || av.queueQuery.length > 300))) {
        return false;
      }
    }
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

    if (selectedVideoScope) {
      var scope = selectedVideoScope;
      requestAnimationFrame(function() {
        if (selectedVideoScope !== scope || tf.restoreVideoGridState?.(state)) return;
        var wrapper = browseWrapper();
        if (wrapper) {
          wrapper.scrollTop = state.scrollTop;
          wrapper.scrollLeft = state.scrollLeft;
        }
      });
      return true;
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
        if (tf.restoreBrowsePosition?.(state.scrollTop || 0, state.scrollLeft || 0)) return;
        var wrapper = browseWrapper();
        if (wrapper) {
          if (state.scrollTop) wrapper.scrollTop = state.scrollTop;
          if (state.scrollLeft) wrapper.scrollLeft = state.scrollLeft;
        }
      });
      restored = true;
    }

    // Restore active video playback (ordinary Mall only; deferred to next frame)
    if (state.activeVideo && typeof tf.restoreActiveVideo === 'function') {
      requestAnimationFrame(function() {
        if (selectedProduct || selectedVideoScope) return;
        tf.restoreActiveVideo(state.activeVideo);
      });
      restored = true;
    }

    return restored;
  }

  // ─── Clear (Public) ───

  function clear() {
    try {
      stateStorage().removeItem(storageKey());
    } catch (e) {
      // fail silently
    }
  }

  // ─── Auto-Save Binding ───

  function openView(view, caller) {
    if (selectedProduct || selectedVideoScope || restoringHistory || view?.retainedPlayer !== true ||
        view.type !== 'video' || typeof view.foundupId !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(view.foundupId) ||
        !window.history?.pushState) return;
    var prior = window.history.state || {};
    var browse = prior[VIEW_HISTORY] ? prior[BROWSE_HISTORY] : captureState();
    if (!browse) return;
    browse = { ...browse };
    delete browse.activeVideo;
    if (caller && Number.isFinite(caller.scrollTop)) {
      browse.scrollTop = caller.scrollTop;
      browse.scrollLeft = caller.scrollLeft;
    }
    if (!prior[VIEW_HISTORY]) window.history.replaceState({ ...prior, [BROWSE_HISTORY]: browse }, '');
    var next = { ...window.history.state, [BROWSE_HISTORY]: browse, [VIEW_HISTORY]: view };
    if (prior[VIEW_HISTORY]?.retainedPlayer) window.history.replaceState(next, '');
    else window.history.pushState(next, '');
  }

  function closeView(type) {
    if (selectedProduct || selectedVideoScope || restoringHistory) return;
    var view = window.history?.state?.[VIEW_HISTORY];
    if (view?.retainedPlayer && view.type === type) window.history.back();
  }

  function restoreHistory() {
    if (selectedProduct || selectedVideoScope) return;
    var entry = window.history.state || {};
    var view = entry[VIEW_HISTORY];
    if (view && !view.retainedPlayer) return;
    if (!entry[BROWSE_HISTORY] && !view?.retainedPlayer) return;
    var player = window.mallVideoPlayer;
    restoringHistory = true;
    try {
      if (view?.retainedPlayer && player?.isMallHidden?.() && player.getFoundUpId() === view.foundupId) {
        if (player.resumeFromMall({ fromHistory: true, autoplay: false }) !== false) return;
      } else if (!view?.retainedPlayer && player?.isOpen?.() && !player.isMallHidden?.()) {
        player.returnToMall({ fromHistory: true });
        return;
      } else if (view?.retainedPlayer && player?.isOpen?.() &&
                 player.getFoundUpId() === view.foundupId && !player.isMallHidden?.()) return;
      // Reload, an explicitly closed session, or a removed caller cannot replay
      // a retained iframe. Remove only our marker; never navigate to another ID.
      if (view?.retainedPlayer) {
        var surviving = { ...entry };
        delete surviving[VIEW_HISTORY];
        window.history.replaceState(surviving, '');
      }
    } finally { restoringHistory = false; }
  }

  function bindAutoSave() {
    if (initialized) return;
    initialized = true;
    window.addEventListener('popstate', restoreHistory);
    // A reload does not reconstruct a hidden live session.
    if (window.history?.state?.[VIEW_HISTORY]?.retainedPlayer) restoreHistory();

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
    var wrapper = browseWrapper();
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

    // Save on active video playback lifecycle in ordinary Mall (never in HPC/product)
    ['videoPlayerOpen', 'videoPlayerNavigate', 'videoPlayerModeChange', 'videoPlayerClose'].forEach(function(eventName) {
      window.addEventListener(eventName, function(event) {
        if (selectedVideoScope || selectedProduct) return;
        if (eventName === 'videoPlayerClose' && event.detail?.restore !== false) closeView('video');
        setTimeout(save, 50);
      });
    });

    // Save on beforeunload (navigation away)
    window.addEventListener('beforeunload', save);
  }

  // ─── Public API ───

  window.mallStateRestore = {
    /** Keep a fixed video field's scroll in its own browser tab. */
    selectVideoScope: selectVideoScope,

    /** Select a registered product namespace before loading its catalog. */
    selectProduct: selectProduct,

    /** Remember this product's filters for an explicit account handoff. */
    rememberProductReturn: rememberProductReturn,
    rememberMemberVideoReturn: rememberMemberVideoReturn,
    rememberAdmissionIntent: rememberAdmissionIntent,
    peekAdmissionIntent: peekAdmissionIntent,
    consumeAdmissionIntent: consumeAdmissionIntent,
    getVideoOptions: getVideoOptions,
    setVideoOptions: setVideoOptions,
    subscribeVideoOptions: subscribeVideoOptions,
    openView: openView,
    closeView: closeView,

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
