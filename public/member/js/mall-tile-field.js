/**
 * Mall Tile Field — Low-chrome discovery surface
 *
 * Replaces carousel with square tile grid.
 * SoftProto mount point: #mallTileField[data-softproto-mount="tile-field"]
 *
 * Gestures:
 *   - Tap tile: Show inspector overlay (preview)
 *   - Double-tap tile: Enter FoundUp view directly
 *   - Tap outside inspector: Close inspector
 *   - Escape: Close inspector
 */
(function() {
  'use strict';

  var DOUBLE_TAP_DELAY = 300;
  var inspectorVisible = false;
  var inspectingIndex = null;
  var lastTapTime = 0;
  var lastTapTarget = null;

  // DOM references (populated on init)
  var tileField = null;
  var inspectorScrim = null;
  var inspector = null;
  var mallCatalog = [];

  /**
   * Initialize tile field with catalog data
   * @param {Array} catalog - Array of FoundUp objects
   */
  function initialize(catalog) {
    mallCatalog = catalog || [];
    tileField = document.getElementById('mallTileField');

    if (!tileField) {
      console.warn('[mall-tile-field] #mallTileField not found');
      return;
    }

    createInspector();
    renderTiles();
    bindInteractions();
  }

  /**
   * Create inspector overlay elements
   */
  function createInspector() {
    // Scrim
    inspectorScrim = document.createElement('div');
    inspectorScrim.className = 'tile-inspector-scrim';
    inspectorScrim.id = 'tileInspectorScrim';

    // Inspector panel
    inspector = document.createElement('div');
    inspector.className = 'tile-inspector';
    inspector.id = 'tileInspector';
    inspector.setAttribute('role', 'dialog');
    inspector.setAttribute('aria-modal', 'true');
    inspector.setAttribute('aria-label', 'FoundUp preview');

    document.body.appendChild(inspectorScrim);
    document.body.appendChild(inspector);

    // Close on scrim tap
    inspectorScrim.addEventListener('click', closeInspector);
  }

  /**
   * Render tiles from catalog
   */
  function renderTiles() {
    if (!mallCatalog.length) {
      tileField.innerHTML = '<div class="mall-tile-field-empty"><span class="mall-tile-field-empty-icon">&#x1F6D2;</span><span>No FoundUps visible</span></div>';
      return;
    }

    tileField.innerHTML = mallCatalog.map(function(item, index) {
      var theme = escapeAttr(item.theme || 'default');
      var readiness = item.launch_readiness || 'discoverable_only';
      var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');

      return '<article class="mall-tile theme-' + theme + '" data-index="' + index + '" data-foundup-id="' + escapeAttr(item.id || '') + '" tabindex="0" aria-label="' + escapeAttr(item.name) + '">' +
        '<span class="mall-tile-badge ' + badgeClass + '">' + escapeHtml(readiness.replace('_', ' ')) + '</span>' +
        '<div class="mall-tile-inner">' +
          '<span class="mall-tile-token">' + escapeHtml(item.token_symbol || '') + '</span>' +
          '<span class="mall-tile-hero">' + escapeHtml(item.hero_label || '') + '</span>' +
          '<p class="mall-tile-name">' + escapeHtml(item.name || '') + '</p>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  /**
   * Bind tile interactions
   */
  function bindInteractions() {
    var tiles = tileField.querySelectorAll('.mall-tile');

    tiles.forEach(function(tile) {
      // Touch/click handling for tap vs double-tap
      tile.addEventListener('click', function(e) {
        var index = Number(tile.dataset.index || 0);
        var now = Date.now();

        // Check for double-tap
        if (lastTapTarget === tile && (now - lastTapTime) < DOUBLE_TAP_DELAY) {
          // Double-tap: enter FoundUp directly
          e.preventDefault();
          lastTapTime = 0;
          lastTapTarget = null;
          enterFoundUp(index);
        } else {
          // Single tap: show inspector (with delay to detect double-tap)
          lastTapTime = now;
          lastTapTarget = tile;

          setTimeout(function() {
            if (lastTapTarget === tile && (Date.now() - lastTapTime) >= DOUBLE_TAP_DELAY) {
              openInspector(index);
            }
          }, DOUBLE_TAP_DELAY + 10);
        }
      });

      // Keyboard support
      tile.addEventListener('keydown', function(e) {
        var index = Number(tile.dataset.index || 0);
        if (e.key === 'Enter') {
          e.preventDefault();
          openInspector(index);
        } else if (e.key === ' ') {
          e.preventDefault();
          enterFoundUp(index);
        }
      });
    });

    // Global escape handler
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && inspectorVisible) {
        e.stopPropagation();
        closeInspector();
      }
    });
  }

  /**
   * Open inspector overlay for a tile
   * @param {number} index - Tile index
   */
  function openInspector(index) {
    var item = mallCatalog[index];
    if (!item) return;

    inspectingIndex = index;

    // Update tile visual state
    var tiles = tileField.querySelectorAll('.mall-tile');
    tiles.forEach(function(t, i) {
      t.classList.toggle('is-inspecting', i === index);
    });

    // Build inspector content
    var readiness = item.launch_readiness || 'discoverable_only';
    var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');

    inspector.innerHTML =
      '<div class="tile-inspector-header">' +
        '<div class="tile-inspector-badges">' +
          '<span class="tile-inspector-badge ' + badgeClass + '">' + escapeHtml(readiness.replace('_', ' ')) + '</span>' +
          '<span class="tile-inspector-badge">' + escapeHtml(item.category || 'FoundUp') + '</span>' +
        '</div>' +
      '</div>' +
      '<h2 class="tile-inspector-name">' + escapeHtml(item.name || '') + '</h2>' +
      '<p class="tile-inspector-tagline">' + escapeHtml(item.description || item.tagline || '') + '</p>' +
      '<div class="tile-inspector-grid">' +
        '<div class="tile-inspector-field">' +
          '<span class="tile-inspector-label">Token</span>' +
          '<span class="tile-inspector-value">' + escapeHtml(item.token_symbol || '-') + '</span>' +
        '</div>' +
        '<div class="tile-inspector-field">' +
          '<span class="tile-inspector-label">Tier</span>' +
          '<span class="tile-inspector-value">' + escapeHtml(item.tier || '-') + '</span>' +
        '</div>' +
        '<div class="tile-inspector-field">' +
          '<span class="tile-inspector-label">Route</span>' +
          '<span class="tile-inspector-value">' + escapeHtml(item.routing_prefix || '-') + '</span>' +
        '</div>' +
        '<div class="tile-inspector-field">' +
          '<span class="tile-inspector-label">Stage</span>' +
          '<span class="tile-inspector-value">' + escapeHtml(item.lifecycle_stage || '-') + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="tile-inspector-actions">' +
        '<button class="tile-inspector-enter" id="inspectorEnterBtn">Enter FoundUp</button>' +
      '</div>' +
      '<p class="tile-inspector-hint">Double-tap tile to enter directly</p>';

    // Bind enter button
    var enterBtn = document.getElementById('inspectorEnterBtn');
    if (enterBtn) {
      enterBtn.addEventListener('click', function() {
        closeInspector();
        enterFoundUp(index);
      });
    }

    // Show inspector
    inspectorScrim.classList.add('visible');
    inspector.classList.add('visible');
    inspectorVisible = true;

    // Update Red Dog context
    if (window.agentFoundupName) {
      window.agentFoundupName.textContent = item.name || '';
    }
    if (window.agentFoundupHint) {
      window.agentFoundupHint.textContent = item.hero_mood || '';
    }
  }

  /**
   * Close inspector overlay
   */
  function closeInspector() {
    if (!inspectorVisible) return;

    inspectorScrim.classList.remove('visible');
    inspector.classList.remove('visible');
    inspectorVisible = false;

    // Clear tile visual state
    var tiles = tileField.querySelectorAll('.mall-tile');
    tiles.forEach(function(t) {
      t.classList.remove('is-inspecting');
    });

    inspectingIndex = null;
  }

  /**
   * Enter FoundUp view
   * @param {number} index - Tile index
   */
  function enterFoundUp(index) {
    closeInspector();

    if (window.mallPlanes && typeof window.mallPlanes.openFoundUp === 'function') {
      window.mallPlanes.openFoundUp(index);
    }
  }

  /**
   * Get current inspecting index
   * @returns {number|null}
   */
  function getInspectingIndex() {
    return inspectingIndex;
  }

  /**
   * Check if inspector is open
   * @returns {boolean}
   */
  function isInspectorOpen() {
    return inspectorVisible;
  }

  // Utility: escape HTML
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Utility: escape attribute
  function escapeAttr(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Expose public API
  window.mallTileField = {
    initialize: initialize,
    openInspector: openInspector,
    closeInspector: closeInspector,
    enterFoundUp: enterFoundUp,
    getInspectingIndex: getInspectingIndex,
    isInspectorOpen: isInspectorOpen
  };

})();
