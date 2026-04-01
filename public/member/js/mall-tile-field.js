/**
 * Mall Tile Field — Video-backed discovery surface
 *
 * Video Mall runtime with snapped field motion.
 * SoftProto mount point: #mallTileField[data-softproto-mount="tile-field"]
 *
 * Gestures (Mall context):
 *   - Tap tile: Play/pause video in Mall context
 *   - Double-tap tile: Enter FoundUp view directly
 *   - Pinch-out on tile: Expand into FoundUp's video field
 *   - Pinch-in (expanded): Collapse back to Mall
 *   - Swipe: Navigate snapped field (default) or glide (override)
 *
 * Motion modes:
 *   - Snap (default): discrete paging like iPhone home screens
 *   - Glide: fluid scroll for browsing
 *
 * Density presets (AI-controlled):
 *   - 2x3, 3x4, 3x5, 5x8
 */
(function() {
  'use strict';

  // Double-tap detection window (ms)
  var DOUBLE_TAP_WINDOW = 300;
  var lastTapTime = 0;
  var lastTapTarget = null;

  // DOM references (populated on init)
  var tileFieldWrapper = null;
  var tileField = null;
  var collapseHint = null;
  var mallCatalog = [];

  // Projection state
  var currentProjection = 'default';
  var originalOrder = [];  // Preserve original catalog order

  // Video Mall runtime state
  var motionMode = 'snap'; // 'snap' | 'glide'
  var currentDensity = '2x3';
  var expandedFoundUp = null; // Index of expanded FoundUp, or null
  var playingIndex = null; // Index of currently playing tile

  /**
   * Initialize tile field with catalog data
   * @param {Array} catalog - Array of FoundUp objects (with video data)
   */
  function initialize(catalog) {
    mallCatalog = catalog || [];
    originalOrder = mallCatalog.slice();  // Preserve original order
    tileField = document.getElementById('mallTileField');

    if (!tileField) {
      console.warn('[mall-tile-field] #mallTileField not found');
      return;
    }

    // Wrap tile field for scroll snapping
    tileFieldWrapper = tileField.parentElement;
    if (tileFieldWrapper && !tileFieldWrapper.classList.contains('mall-tile-field-wrapper')) {
      // Create wrapper if not already wrapped
      var wrapper = document.createElement('div');
      wrapper.className = 'mall-tile-field-wrapper';
      tileField.parentNode.insertBefore(wrapper, tileField);
      wrapper.appendChild(tileField);
      tileFieldWrapper = wrapper;
    }

    // Create collapse hint
    createCollapseHint();

    // Set initial density
    setDensity(currentDensity);

    renderTiles();
    bindInteractions();
    bindProjectionChips();
  }

  /**
   * Create collapse hint element (shown when in expanded mode)
   */
  function createCollapseHint() {
    collapseHint = document.createElement('div');
    collapseHint.className = 'mall-tile-field-collapse-hint';
    collapseHint.textContent = 'Pinch in to collapse';
    collapseHint.id = 'tileFieldCollapseHint';
    document.body.appendChild(collapseHint);
  }

  /**
   * Render tiles from catalog (video-backed)
   */
  function renderTiles() {
    var itemsToRender = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;

    if (!itemsToRender.length) {
      tileField.innerHTML = '<div class="mall-tile-field-empty"><span class="mall-tile-field-empty-icon">&#x1F6D2;</span><span>No FoundUps visible</span></div>';
      return;
    }

    tileField.innerHTML = itemsToRender.map(function(item, index) {
      var theme = escapeAttr(item.theme || 'default');
      var readiness = item.launch_readiness || 'discoverable_only';
      var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');

      // Video-backed: use poster_url as background
      var posterStyle = item.poster_url ? 'background-image: url(' + escapeAttr(item.poster_url) + ')' : '';

      // Queue count (video_count or videos array length)
      var queueCount = item.video_count || (item.videos ? item.videos.length : 0);
      var queueBadge = queueCount > 0 ? '<span class="mall-tile-queue-count">' + queueCount + ' videos</span>' : '';

      // Play indicator
      var playIndicator = '<div class="mall-tile-play-indicator"></div>';

      return '<article class="mall-tile theme-' + theme + '" data-index="' + index + '" data-foundup-id="' + escapeAttr(item.foundup_id || item.id || '') + '" tabindex="0" aria-label="' + escapeAttr(item.name || item.title || '') + '" style="' + posterStyle + '">' +
        '<span class="mall-tile-badge ' + badgeClass + '">' + escapeHtml(readiness.replace('_', ' ')) + '</span>' +
        queueBadge +
        playIndicator +
        '<div class="mall-tile-inner">' +
          '<span class="mall-tile-token">' + escapeHtml(item.token_symbol || '') + '</span>' +
          '<span class="mall-tile-hero">' + escapeHtml(item.hero_label || '') + '</span>' +
          '<p class="mall-tile-name">' + escapeHtml(item.name || item.title || '') + '</p>' +
        '</div>' +
      '</article>';
    }).join('');

    // Update expanded mode class
    tileField.classList.toggle('expanded-mode', expandedFoundUp !== null);
  }

  /**
   * Get videos for expanded FoundUp
   * @returns {Array} Video items for current expanded FoundUp
   */
  function getExpandedVideos() {
    if (expandedFoundUp === null) return [];
    var foundup = mallCatalog[expandedFoundUp];
    if (!foundup || !foundup.videos) return [];

    // Map videos to tile-compatible format
    return foundup.videos.map(function(video, idx) {
      return {
        foundup_id: foundup.foundup_id + '_video_' + idx,
        name: video.title,
        title: video.title,
        poster_url: video.poster_url || video.thumbnail_url,
        theme: foundup.theme || 'default',
        launch_readiness: foundup.launch_readiness || 'discoverable_only',
        token_symbol: foundup.token_symbol,
        hero_label: '',
        video_data: video,
        parent_foundup_index: expandedFoundUp
      };
    });
  }

  /**
   * Bind tile interactions (video Mall runtime)
   */
  function bindInteractions() {
    var tiles = tileField.querySelectorAll('.mall-tile');

    tiles.forEach(function(tile) {
      // Touch/click handling: tap = play/pause, double-tap = enter
      tile.addEventListener('click', function(e) {
        var index = Number(tile.dataset.index || 0);
        var now = Date.now();

        // Check for double-tap (second tap within window)
        if (lastTapTarget === tile && (now - lastTapTime) < DOUBLE_TAP_WINDOW) {
          // Double-tap: enter FoundUp directly
          e.preventDefault();
          lastTapTime = 0;
          lastTapTarget = null;
          enterFoundUp(index);
        } else {
          // Single tap: play/pause in Mall context
          lastTapTime = now;
          lastTapTarget = tile;
          togglePlay(index);
        }
      });

      // Keyboard support
      tile.addEventListener('keydown', function(e) {
        var index = Number(tile.dataset.index || 0);
        if (e.key === ' ') {
          e.preventDefault();
          togglePlay(index);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          enterFoundUp(index);
        }
      });

      // Pinch support via gesture engine (if available)
      if (window.gestureZone) {
        window.gestureZone(tile, {
          onPinchOut: function() {
            var index = Number(tile.dataset.index || 0);
            expandFoundUp(index);
          },
          onPinchIn: function() {
            if (expandedFoundUp !== null) {
              collapseFoundUp();
            }
          }
        });
      }
    });

    // Global escape handler - collapse expanded view
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && expandedFoundUp !== null) {
        e.stopPropagation();
        collapseFoundUp();
      }
    });
  }

  /**
   * Toggle play/pause for a tile
   * @param {number} index - Tile index
   */
  function togglePlay(index) {
    var tiles = tileField.querySelectorAll('.mall-tile');

    // Clear previous playing state
    tiles.forEach(function(t) {
      t.classList.remove('is-playing');
    });

    if (playingIndex === index) {
      // Pause: was playing this one
      playingIndex = null;
    } else {
      // Play: new tile
      playingIndex = index;
      if (tiles[index]) {
        tiles[index].classList.add('is-playing');
      }
    }

    // Notify listeners (for video player integration)
    if (window.mallVideoPlayer && typeof window.mallVideoPlayer.setPlaying === 'function') {
      var item = mallCatalog[index];
      window.mallVideoPlayer.setPlaying(playingIndex !== null ? item : null);
    }
  }

  /**
   * Expand a FoundUp into its video field
   * @param {number} index - FoundUp index in catalog
   */
  function expandFoundUp(index) {
    if (expandedFoundUp === index) return; // Already expanded

    var item = mallCatalog[index];
    if (!item || !item.videos || !item.videos.length) {
      console.warn('[mall-tile-field] Cannot expand: no videos for FoundUp', index);
      return;
    }

    expandedFoundUp = index;
    playingIndex = null;
    renderTiles();
    bindInteractions();

    // Show collapse hint
    if (collapseHint) {
      collapseHint.style.opacity = '1';
    }
  }

  /**
   * Collapse expanded video field back to Mall
   */
  function collapseFoundUp() {
    if (expandedFoundUp === null) return;

    expandedFoundUp = null;
    playingIndex = null;
    renderTiles();
    bindInteractions();

    // Hide collapse hint
    if (collapseHint) {
      collapseHint.style.opacity = '0';
    }
  }

  // ========== Motion Mode Control ==========

  /**
   * Set field motion mode
   * @param {string} mode - 'snap' | 'glide'
   */
  function setMotionMode(mode) {
    if (mode !== 'snap' && mode !== 'glide') {
      mode = 'snap';
    }
    motionMode = mode;

    if (tileFieldWrapper) {
      tileFieldWrapper.classList.toggle('motion-glide', mode === 'glide');
    }
  }

  /**
   * Get current motion mode
   * @returns {string} 'snap' | 'glide'
   */
  function getMotionMode() {
    return motionMode;
  }

  // ========== Density Control ==========

  /**
   * Set field density preset
   * @param {string} density - '2x3' | '3x4' | '3x5' | '5x8'
   */
  function setDensity(density) {
    var validDensities = ['2x3', '3x4', '3x5', '5x8'];
    if (!validDensities.includes(density)) {
      density = '2x3';
    }
    currentDensity = density;

    if (tileField) {
      tileField.dataset.density = density;
    }
  }

  /**
   * Get current density preset
   * @returns {string}
   */
  function getDensity() {
    return currentDensity;
  }

  // ========== Expanded State Queries ==========

  /**
   * Check if field is in expanded mode
   * @returns {boolean}
   */
  function isExpanded() {
    return expandedFoundUp !== null;
  }

  /**
   * Get expanded FoundUp index
   * @returns {number|null}
   */
  function getExpandedIndex() {
    return expandedFoundUp;
  }

  /**
   * Get currently playing index
   * @returns {number|null}
   */
  function getPlayingIndex() {
    return playingIndex;
  }

  /**
   * Enter FoundUp view
   * @param {number} index - Tile index
   */
  function enterFoundUp(index) {
    // If in expanded mode, enter the parent FoundUp
    var targetIndex = index;
    if (expandedFoundUp !== null) {
      var items = getExpandedVideos();
      if (items[index] && items[index].parent_foundup_index !== undefined) {
        targetIndex = items[index].parent_foundup_index;
      }
      collapseFoundUp();
    }

    if (window.mallPlanes && typeof window.mallPlanes.openFoundUp === 'function') {
      window.mallPlanes.openFoundUp(targetIndex);
    }
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

  // ========== Projection System ==========

  /**
   * Readiness priority for sorting (higher = more ready)
   */
  var READINESS_ORDER = {
    'ready': 3,
    'conditional': 2,
    'discoverable_only': 1
  };

  /**
   * Sort catalog by projection mode
   * @param {string} projection - Projection name
   * @returns {Array} Sorted catalog
   */
  function sortByProjection(projection) {
    var sorted = mallCatalog.slice();

    switch (projection) {
      case 'alpha':
        sorted.sort(function(a, b) {
          var nameA = (a.name || '').toLowerCase();
          var nameB = (b.name || '').toLowerCase();
          return nameA.localeCompare(nameB);
        });
        break;

      case 'readiness':
        sorted.sort(function(a, b) {
          var readA = READINESS_ORDER[a.launch_readiness] || 0;
          var readB = READINESS_ORDER[b.launch_readiness] || 0;
          // Higher readiness first, then alpha
          if (readB !== readA) return readB - readA;
          return (a.name || '').toLowerCase().localeCompare((b.name || '').toLowerCase());
        });
        break;

      case 'category':
        sorted.sort(function(a, b) {
          var catA = (a.category || 'zzz').toLowerCase();
          var catB = (b.category || 'zzz').toLowerCase();
          if (catA !== catB) return catA.localeCompare(catB);
          return (a.name || '').toLowerCase().localeCompare((b.name || '').toLowerCase());
        });
        break;

      default:
        // 'default' - restore original order
        sorted = originalOrder.slice();
        break;
    }

    return sorted;
  }

  /**
   * Set projection mode and re-render tiles
   * @param {string} projection - Projection name: default, alpha, readiness, category
   */
  function setProjection(projection) {
    if (!['default', 'alpha', 'readiness', 'category'].includes(projection)) {
      projection = 'default';
    }

    currentProjection = projection;
    mallCatalog = sortByProjection(projection);
    renderTiles();
    bindInteractions();
    updateProjectionChips();
  }

  /**
   * Get current projection mode
   * @returns {string}
   */
  function getProjection() {
    return currentProjection;
  }

  /**
   * Reset to default projection
   */
  function resetProjection() {
    setProjection('default');
  }

  /**
   * Update projection chip active states
   */
  function updateProjectionChips() {
    var chips = document.querySelectorAll('.mall-projection-chip');
    chips.forEach(function(chip) {
      var proj = chip.dataset.projection;
      chip.classList.toggle('active', proj === currentProjection);
    });
  }

  /**
   * Bind projection chip click handlers
   */
  function bindProjectionChips() {
    var chips = document.querySelectorAll('.mall-projection-chip');
    chips.forEach(function(chip) {
      chip.addEventListener('click', function() {
        var proj = chip.dataset.projection || 'default';
        setProjection(proj);
      });
    });
  }

  // Expose public API
  window.mallTileField = {
    // Core
    initialize: initialize,
    enterFoundUp: enterFoundUp,

    // Video runtime
    togglePlay: togglePlay,
    getPlayingIndex: getPlayingIndex,
    expandFoundUp: expandFoundUp,
    collapseFoundUp: collapseFoundUp,
    isExpanded: isExpanded,
    getExpandedIndex: getExpandedIndex,

    // Motion mode
    setMotionMode: setMotionMode,
    getMotionMode: getMotionMode,

    // Density
    setDensity: setDensity,
    getDensity: getDensity,

    // Projection
    setProjection: setProjection,
    getProjection: getProjection,
    resetProjection: resetProjection
  };

})();
