/**
 * Mall Tile Field — shared video and property discovery surface
 *
 * Portrait-first 9:16 video wall (Shorts-style)
 * SoftProto mount point: #mallTileField[data-softproto-mount="tile-field"]
 *
 * Gestures (Mall context):
 *   - Tap tile: Start lane autoplay through FoundUp's video queue (Shorts-style)
 *   - Enter button: Navigate to /f/{foundup_id} (WSP 104 canonical)
 *   - Pinch-out on tile: Expand into FoundUp's video field
 *   - Pinch-in (expanded): Collapse back to Mall
 *   - Swipe: Navigate snapped field (default) or glide (override)
 *
 * Motion modes:
 *   - Snap (default): discrete paging like iPhone home screens
 *   - Glide: fluid scroll for browsing
 *
 * Density presets (AI-controlled or viewport-adaptive):
 *   - 3x4, 3x5, 4x6, 5x8 (portrait-first dense walls)
 *   - 6x3 (desktop wide viewport - auto-selected for fine-pointer + landscape)
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
  var layoutMode = 'rows';
  var desktopPosterBrowsing = false;
  var desktopInlineTile = null;
  var rowOffsets = Object.create(null);
  var escapeBound = false;
  var originalOrder = [];  // Preserve original catalog order

  // Field scope state (filter before projection)
  var currentFieldScope = null;  // null = all, 'personal' = 012 lanes only
  var fullCatalog = [];  // Unscoped catalog reference

  // Optional spatial projection. The catalog still has one owner; rows contain
  // stable listing IDs, never independent Mall instances or synthetic FoundUps.
  var groupDefinitions = null;
  var visibleGroups = [];
  var groupPositions = Object.create(null);
  var activeGroupKey = null;
  var groupScrollTop = 0;
  var groupScrollOffset = 0;
  var restoringGroups = false;

  // Category → theme fallback (used when item.theme and item.foundup_id have no CSS match)
  var CATEGORY_THEME = {
    'travel': 'cat-travel',
    'music': 'cat-music',
    'startup': 'cat-startup',
    'media': 'cat-media',
    'thought-leadership': 'cat-thought-leadership',
    'ai-education': 'cat-ai-education',
    'ai-research': 'cat-ai-research',
    'infrastructure': 'cat-infrastructure',
    'civic': 'cat-civic',
    'trading': 'cat-trading',
    'games': 'cat-games',
    'community': 'cat-community',
    'science': 'cat-science',
    'marketplace': 'cat-marketplace'
  };

  // Video Mall runtime state
  var motionMode = 'snap'; // 'snap' | 'glide'
  var currentDensity = '3x5';
  var densityManuallySet = false; // Whether user has manually overridden density
  var expandedFoundUp = null; // Index of expanded FoundUp, or null
  var fixedVideoField = false; // Public projection starts and stays inside one lane.
  var entityPortraitField = false; // Opt-in public FoundUp grid; never an expanded video lane.
  var entityRenderedCount = 0;
  var catalogPager = null;
  var catalogLoad = null;
  var catalogEpoch = 0;
  var catalogRefreshPending = false;
  var catalogError = '';
  var videoPager = null;
  var videoRecord = null;
  var videoLoad = null;
  var selectionController = null;
  var selectionEpoch = 0;
  var pendingEntityId = null;
  var pendingSelection = null;
  var selectedControls = null;
  var selectedLogo = null;
  var selectedLogoOriginal = null;
  var discoveryError = '';
  var selectedNotice = '';
  var selectedVideoIndex = 0;
  var playerCaller = null;
  var retainedLane = null;
  var catalogLifetimeBound = false;

  var FIXED_VIDEO_COLUMNS = 3;
  var FIXED_VIDEO_BATCH = 6;
  var PHONE_PATCH_BATCH = 9;
  var HOVER_FLIP_DELAY_MS = 650;
  var HOLD_FLIP_DELAY_MS = 450;
  var activeFlippedTile = null;
  var desktopBlockNav = null;
  var fixedRenderedCount = 0;
  var fixedTailObserver = null;
  var fixedBrowsePosition = null;
  var scopedTheaterRequested = false;
  var scopedPlaybackDismissed = false;
  var scopedTheaterState = null;
  var scopedPlaybackPosition = null;
  var scopedPhoneQuery = '';
  var scopedPhoneIndices = null;
  var scopedPhonePlaybackIndices = null;
  var scopedRenderedIndices = null;
  var SCOPED_PLAYER_HISTORY = 'pfmallScopedPlayer';
  var browseScrollTop = 0;
  var expandSourceIndex = null; // Original tile index for collapse animation
  var expandSourceVisual = null; // { bgImage, bgColor } for collapse continuity
  var playingIndex = null; // Index of currently playing tile

  // Inline preview state
  var previewPaused = false;       // Whether current preview is paused
  var previewMuted = true;         // Whether current preview audio is muted
  var inlineYTPlayer = null;       // YouTube IFrame API player instance
  var inlineHTML5Video = null;     // HTML5 <video> element reference
  var ytAPIReady = false;          // Whether YouTube IFrame API is loaded
  var ytAPILoading = false;        // Prevent duplicate script injection
  var previewGeneration = 0;       // Guard against stale callbacks
  var tapGuardActive = false;      // Prevent double-fire on audio button tap

  // Lane autoplay state (Shorts-style queue traversal)
  var currentLaneFoundupIndex = null;  // Which FoundUp lane is playing (catalog index)
  var laneVideoIndex = 0;              // Current position in lane's videos[] queue
  var laneAutoplayEnabled = true;      // Whether to auto-advance on video end

  // ========== Intelligent Grid Loading (PFM11B) ==========
  // WSP 97 TRUTH BOUNDARIES:
  //   - Viewport-aware loading only
  //   - No content trust filtering in this slice
  //   - No verification claims (verified/safe/authentic are reserved)
  //   - No adaptive network/device routing claims

  // Load policy configuration (matches ContentLoadPolicy schema)
  var loadPolicy = {
    viewportMarginPx: 200,         // Extra margin around viewport for pre-loading
    loadBatchSize: 6,              // Number of tiles to load per batch
    debounceMs: 100,               // Debounce time for scroll events
    thumbnailInitialQuality: 'low',  // Start with low-quality thumbnails
    thumbnailUpgradeQuality: 'high', // Upgrade to high-quality when visible
    enableViewportLazyLoad: true   // Enable IntersectionObserver-based loading
  };

  // Tile load state tracking: index -> state
  // States: 'pending' | 'visible' | 'loading' | 'loaded' | 'failed' | 'placeholder'
  var tileLoadStates = {};

  // IntersectionObserver for viewport detection
  var tileObserver = null;

  /**
   * Initialize IntersectionObserver for viewport-aware tile loading.
   * Fallback to eager loading if IntersectionObserver is unavailable.
   */
  function initTileObserver() {
    if (!loadPolicy.enableViewportLazyLoad) return;

    // Fallback for browsers without IntersectionObserver
    if (typeof IntersectionObserver === 'undefined') {
      console.warn('[mall-tile-field] IntersectionObserver unavailable, using eager load');
      markAllTilesLoaded();
      return;
    }

    // Clean up previous observer
    if (tileObserver) {
      tileObserver.disconnect();
      tileObserver = null;
    }

    tileObserver = new IntersectionObserver(handleTileIntersection, {
      root: tileFieldWrapper || null,
      rootMargin: loadPolicy.viewportMarginPx + 'px',
      threshold: 0.01  // Trigger when any part enters viewport
    });

    observeTiles(tileField ? tileField.querySelectorAll('.mall-tile') : []);
  }

  function isPhonePatchViewport() {
    if (!loadPolicy.enableViewportLazyLoad || typeof IntersectionObserver === 'undefined') return false;
    if (desktopPosterBrowsing) return false;
    return !!(window.matchMedia && window.matchMedia('(max-width: 899px), (pointer: coarse)').matches);
  }

  function usesProgressivePatchGrid() {
    if (fixedVideoField) return true;
    if (!isPhonePatchViewport() || groupDefinitions !== null) return false;
    return expandedFoundUp !== null || layoutMode === 'grid';
  }

  function activePatchBatchSize() {
    return fixedVideoField || entityPortraitField ? FIXED_VIDEO_BATCH : PHONE_PATCH_BATCH;
  }

  function hydrateTilePoster(tile) {
    if (!tile) return;
    var deferredUrl = tile.dataset.posterUrl || '';
    if (deferredUrl && (!tile.style.backgroundImage || tile.style.backgroundImage === 'none')) {
      tile.style.backgroundImage = 'url(' + deferredUrl.replace(/["\\]/g, '\\$&') + ')';
    }
    var bgImage = tile.style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
      var urlMatch = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
      if (urlMatch && urlMatch[1]) {
        if (typeof Image !== 'undefined') {
          var img = new Image();
          img.onload = function() { tile.classList.add('thumb-loaded'); };
          img.onerror = function() { tile.classList.add('thumb-loaded'); };
          img.src = urlMatch[1];
        } else {
          tile.classList.add('thumb-loaded');
        }
        return;
      }
    }
    tile.classList.add('thumb-loaded');
  }

  function setTileFlipped(tile, flipped, options) {
    if (!tile) return false;
    var next = typeof flipped === 'boolean' ? flipped : !tile.classList.contains('is-card-flipped');
    return setCardFlipped(tile, next, options);
  }

  function observeTiles(tiles) {
    tiles.forEach(function(tile) {
      var index = Number(tile.dataset.index);
      tile.dataset.tileIndex = index;
      var alreadyHydrated = !tile.dataset.posterUrl || (tile.style.backgroundImage && tile.style.backgroundImage !== 'none');
      tileLoadStates[index] = tileObserver ? (alreadyHydrated ? 'loaded' : 'pending') : 'loaded';
      if (alreadyHydrated) hydrateTilePoster(tile);
      else if (tileObserver) tileObserver.observe(tile);
      else hydrateTilePoster(tile);
    });
  }

  /**
   * Handle IntersectionObserver entries for tile visibility.
   * @param {IntersectionObserverEntry[]} entries
   */
  function handleTileIntersection(entries) {
    entries.forEach(function(entry) {
      var tile = entry.target;
      var index = parseInt(tile.dataset.tileIndex, 10);
      if (isNaN(index)) return;

      if (entry.isIntersecting) {
        // Tile entered viewport
        var currentState = tileLoadStates[index];
        if (currentState === 'pending') {
          tileLoadStates[index] = 'visible';
          // Trigger load (hydrate deferred poster thumbnail)
          loadTileContent(index, tile);
        }
        if (tileObserver) tileObserver.unobserve(tile);
      }
      // Note: We don't downgrade state when leaving viewport
    });
  }

  /**
   * Load content for a single tile.
   * @param {number} index - Tile index
   * @param {HTMLElement} tile - Tile DOM element
   */
  function loadTileContent(index, tile) {
    if (tileLoadStates[index] === 'loaded' || tileLoadStates[index] === 'loading') {
      return;
    }
    tileLoadStates[index] = 'loading';
    hydrateTilePoster(tile);
    tileLoadStates[index] = 'loaded';
  }

  /**
   * Mark all tiles as loaded (fallback for no IntersectionObserver).
   */
  function markAllTilesLoaded() {
    var tiles = tileField ? tileField.querySelectorAll('.mall-tile') : [];
    tiles.forEach(function(tile, index) {
      index = Number(tile.dataset.index);
      tile.dataset.tileIndex = index;
      hydrateTilePoster(tile);
      tileLoadStates[index] = 'loaded';
    });
  }

  /**
   * Get load state for a single tile.
   * @param {number} index - Tile index
   * @returns {string|null} Load state or null if not tracked
   */
  function getTileLoadState(index) {
    return tileLoadStates.hasOwnProperty(index) ? tileLoadStates[index] : null;
  }

  /**
   * Get all tile load states.
   * @returns {Object} Map of index -> state
   */
  function getTileLoadStates() {
    // Return shallow copy to prevent external mutation
    var copy = {};
    for (var k in tileLoadStates) {
      if (tileLoadStates.hasOwnProperty(k)) {
        copy[k] = tileLoadStates[k];
      }
    }
    return copy;
  }

  /**
   * Get current load policy configuration.
   * @returns {Object} Load policy object
   */
  function getLoadPolicy() {
    // Return shallow copy
    return {
      viewportMarginPx: loadPolicy.viewportMarginPx,
      loadBatchSize: loadPolicy.loadBatchSize,
      debounceMs: loadPolicy.debounceMs,
      thumbnailInitialQuality: loadPolicy.thumbnailInitialQuality,
      thumbnailUpgradeQuality: loadPolicy.thumbnailUpgradeQuality,
      enableViewportLazyLoad: loadPolicy.enableViewportLazyLoad
    };
  }

  /**
   * Check if IntersectionObserver is being used.
   * @returns {boolean} True if observer is active
   */
  function isViewportLoadingActive() {
    return tileObserver !== null;
  }

  // ========== YouTube IFrame API Helpers ==========

  function ensureYouTubeAPI() {
    if (ytAPIReady) return Promise.resolve();
    if (ytAPILoading) {
      return new Promise(function(resolve) {
        var check = setInterval(function() {
          if (ytAPIReady) { clearInterval(check); resolve(); }
        }, 100);
      });
    }
    ytAPILoading = true;
    return new Promise(function(resolve) {
      var prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function() {
        ytAPIReady = true;
        ytAPILoading = false;
        if (prev) prev();
        resolve();
      };
      var tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(tag);
    });
  }

  function extractYouTubeVideoId(url) {
    if (!url) return null;
    var m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?.*v=|embed\/|v\/))([A-Za-z0-9_-]{11})/);
    return m ? m[1] : null;
  }

  function destroyInlineYTPlayer() {
    if (inlineYTPlayer) {
      try { inlineYTPlayer.destroy(); } catch (e) { /* ignore */ }
      inlineYTPlayer = null;
    }
  }

  function getTilePreviewVideo(index) {
    var items = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
    var item = items[index];
    if (!item || isPropertyListing(item)) return null;
    // In expanded mode or single video_data, use direct reference
    if (item.video_data) return item.video_data;
    // In lane mode, use current lane video index
    if (item.videos && item.videos.length) {
      var vidIdx = (currentLaneFoundupIndex === index) ? laneVideoIndex : 0;
      return item.videos[vidIdx] || item.videos[0];
    }
    return null;
  }

  /**
   * Get video from lane queue at specific position
   * @param {number} foundupIndex - FoundUp index in catalog
   * @param {number} videoIndex - Position in videos[] queue
   * @returns {Object|null} Video data object
   */
  function getLaneVideo(foundupIndex, videoIndex) {
    var item = mallCatalog[foundupIndex];
    if (!item || isPropertyListing(item) || !item.videos || !item.videos.length) return null;
    return item.videos[videoIndex] || null;
  }

  /**
   * Advance to next video in current lane queue
   * Policy: Loop to start when queue ends (Shorts-style continuous play)
   */
  function advanceToNextInLane() {
    if (currentLaneFoundupIndex === null || !laneAutoplayEnabled) return;
    var item = mallCatalog[currentLaneFoundupIndex];
    if (!item || !item.videos || !item.videos.length) return;

    var nextIndex = laneVideoIndex + 1;
    // Loop policy: wrap to start when queue ends
    if (nextIndex >= item.videos.length) {
      nextIndex = 0;
    }
    laneVideoIndex = nextIndex;
    // Start preview at new position (keep mute state)
    startLanePreview(currentLaneFoundupIndex, laneVideoIndex, previewMuted);
  }

  /**
   * Start lane preview at specific video position
   * @param {number} foundupIndex - FoundUp catalog index
   * @param {number} videoIndex - Position in videos[] queue
   * @param {boolean} muted - Whether to start muted
   */
  function startLanePreview(foundupIndex, videoIndex, muted) {
    var item = mallCatalog[foundupIndex];
    if (!item || isPropertyListing(item) || !item.videos || !item.videos.length) return;

    var video = item.videos[videoIndex];
    if (!video) return;

    // Get the tile element for this FoundUp
    var tile = getTileElement(foundupIndex);
    if (!tile) return;

    // Stop any existing preview FIRST (this clears lane state)
    stopInlinePreview();

    // Set lane state AFTER stopInlinePreview so it survives
    currentLaneFoundupIndex = foundupIndex;
    laneVideoIndex = videoIndex;

    var videoUrl = video.embed_url || video.embedUrl || video.source_url || video.sourceUrl || '';
    if (!videoUrl || typeof videoUrl !== 'string' || videoUrl.length < 5) return;

    var ytId = extractYouTubeVideoId(videoUrl);
    var stage = tile.querySelector('.mall-tile-preview-stage');
    if (!stage) return;

    playingIndex = foundupIndex;
    previewPaused = false;
    previewMuted = muted !== false;
    previewGeneration++;
    var gen = previewGeneration;

    applyTilePreviewState(foundupIndex, { previewing: true, paused: false, muted: previewMuted });

    if (ytId) {
      ensureYouTubeAPI().then(function() {
        if (gen !== previewGeneration) return;
        var hostDiv = document.createElement('div');
        hostDiv.className = 'mall-tile-preview-host';
        hostDiv.id = 'yt-preview-' + foundupIndex + '-' + gen;
        stage.innerHTML = '';
        stage.appendChild(hostDiv);
        inlineYTPlayer = new YT.Player(hostDiv.id, {
          videoId: ytId,
          playerVars: {
            autoplay: 1, mute: 1, controls: 0, modestbranding: 1,
            rel: 0, playsinline: 1
            // Note: removed loop - we handle advancement manually
          },
          events: {
            onReady: function(event) {
              if (gen !== previewGeneration) return;
              if (previewMuted) event.target.mute();
              else event.target.unMute();
              event.target.playVideo();
            },
            onStateChange: function(event) {
              if (gen !== previewGeneration) return;
              // YT.PlayerState.ENDED = 0
              if (event.data === 0) {
                advanceToNextInLane();
              }
            },
            onError: function(event) {
              if (gen !== previewGeneration) return;
              // Skip to next on error
              advanceToNextInLane();
            }
          }
        });
      });
    } else if (videoUrl) {
      var videoEl = document.createElement('video');
      videoEl.className = 'mall-tile-preview-media';
      videoEl.muted = previewMuted;
      videoEl.autoplay = true;
      videoEl.playsInline = true;
      videoEl.setAttribute('playsinline', '');
      // Advance on video end
      videoEl.addEventListener('ended', function() {
        if (gen !== previewGeneration) return;
        advanceToNextInLane();
      });
      videoEl.onerror = function() {
        if (gen !== previewGeneration) return;
        advanceToNextInLane();
      };
      stage.innerHTML = '';
      stage.appendChild(videoEl);
      inlineHTML5Video = videoEl;
      videoEl.src = videoUrl;
      videoEl.play().catch(function() {
        if (gen !== previewGeneration) return;
        advanceToNextInLane();
      });
    }
  }

  // ========== Inline Preview Runtime ==========

  function applyTilePreviewState(index, state) {
    if (!tileField) return;
    var allTiles = tileField.querySelectorAll('.mall-tile');
    allTiles.forEach(function(t) {
      t.classList.remove('is-previewing', 'is-paused', 'has-video-controls');
      var btn = t.querySelector('.mall-tile-audio');
      if (btn) btn.classList.remove('is-active', 'is-muted');
    });
    if (index === null || index === undefined || !state) return;
    var tile = getTileElement(index);
    if (!tile) return;
    if (state.previewing) {
      tile.classList.add('is-previewing', 'has-video-controls');
      if (state.paused) tile.classList.add('is-paused');
    }
    var audioBtn = tile.querySelector('.mall-tile-audio');
    if (audioBtn && state.previewing) {
      audioBtn.classList.add('is-active');
      if (state.muted) audioBtn.classList.add('is-muted');
      // Update SVG icon and accessibility text
      if (state.muted) {
        audioBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
        audioBtn.setAttribute('aria-label', 'Unmute preview');
        audioBtn.title = 'Unmute preview';
      } else {
        audioBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 010 14.14"/><path d="M15.54 8.46a5 5 0 010 7.07"/></svg>';
        audioBtn.setAttribute('aria-label', 'Mute preview');
        audioBtn.title = 'Mute preview';
      }
    }
  }

  function stopInlinePreview() {
    if (playingIndex === null) return;
    // Increment generation FIRST to invalidate any pending async callbacks
    previewGeneration++;
    destroyInlineYTPlayer();
    if (inlineHTML5Video) {
      // Remove error handler to prevent stale callback
      inlineHTML5Video.onerror = null;
      inlineHTML5Video.pause();
      inlineHTML5Video.src = '';
      // Call load() to release media buffers (mobile resource discipline)
      try { inlineHTML5Video.load(); } catch (e) { /* ignore */ }
      // Remove from DOM to ensure cleanup
      if (inlineHTML5Video.parentNode) {
        inlineHTML5Video.parentNode.removeChild(inlineHTML5Video);
      }
      inlineHTML5Video = null;
    }
    var tile = getTileElement(playingIndex);
    if (tile) {
      var stage = tile.querySelector('.mall-tile-preview-stage');
      if (stage) stage.innerHTML = '';
    }
    applyTilePreviewState(null, null);
    playingIndex = null;
    previewPaused = false;
    // Reset lane state
    currentLaneFoundupIndex = null;
    laneVideoIndex = 0;
  }

  function pauseInlinePreview() {
    if (playingIndex === null) return;
    if (inlineYTPlayer && typeof inlineYTPlayer.pauseVideo === 'function') {
      inlineYTPlayer.pauseVideo();
    }
    if (inlineHTML5Video) inlineHTML5Video.pause();
    previewPaused = true;
    applyTilePreviewState(playingIndex, { previewing: true, paused: true, muted: previewMuted });
  }

  function resumeInlinePreview() {
    if (playingIndex === null) return;
    if (inlineYTPlayer && typeof inlineYTPlayer.playVideo === 'function') {
      inlineYTPlayer.playVideo();
    }
    if (inlineHTML5Video) inlineHTML5Video.play();
    previewPaused = false;
    applyTilePreviewState(playingIndex, { previewing: true, paused: false, muted: previewMuted });
  }

  function startInlinePreview(index, muted) {
    // Defensive cleanup: always stop previous preview first
    stopInlinePreview();

    var videoData = getTilePreviewVideo(index);
    if (!videoData) return;

    var videoUrl = videoData.embed_url || videoData.embedUrl || videoData.source_url || videoData.sourceUrl || '';
    // Invalid URL fail-safe: don't attempt preview with empty/malformed URLs
    if (!videoUrl || typeof videoUrl !== 'string' || videoUrl.length < 5) {
      return;
    }
    var ytId = extractYouTubeVideoId(videoUrl);
    var tile = getTileElement(index);
    if (!tile) return;
    var stage = tile.querySelector('.mall-tile-preview-stage');
    if (!stage) return;

    playingIndex = index;
    previewPaused = false;
    previewMuted = muted !== false;
    previewGeneration++;
    var gen = previewGeneration;

    applyTilePreviewState(index, { previewing: true, paused: false, muted: previewMuted });

    if (ytId) {
      ensureYouTubeAPI().then(function() {
        if (gen !== previewGeneration) return;
        var hostDiv = document.createElement('div');
        hostDiv.className = 'mall-tile-preview-host';
        hostDiv.id = 'yt-preview-' + index + '-' + gen;
        stage.innerHTML = '';
        stage.appendChild(hostDiv);
        inlineYTPlayer = new YT.Player(hostDiv.id, {
          videoId: ytId,
          playerVars: {
            autoplay: 1, mute: 1, controls: 0, modestbranding: 1,
            rel: 0, playsinline: 1, loop: 1, playlist: ytId
          },
          events: {
            onReady: function(event) {
              if (gen !== previewGeneration) return;
              if (previewMuted) event.target.mute();
              else event.target.unMute();
              event.target.playVideo();
            },
            onError: function(event) {
              // YouTube player error: fail quietly, clean up state
              if (gen !== previewGeneration) return;
              stopInlinePreview();
            }
          }
        });
      });
    } else if (videoUrl) {
      var video = document.createElement('video');
      video.className = 'mall-tile-preview-media';
      video.muted = previewMuted;
      video.autoplay = true;
      video.loop = true;
      video.playsInline = true;
      video.setAttribute('playsinline', '');
      // Error handler: fail quietly without poisoning state
      video.onerror = function() {
        if (gen !== previewGeneration) return;
        stopInlinePreview();
      };
      stage.innerHTML = '';
      stage.appendChild(video);
      inlineHTML5Video = video;
      video.src = videoUrl;
      video.play().catch(function() {
        // Autoplay may be blocked — fail quietly, stop preview state
        if (gen !== previewGeneration) return;
        stopInlinePreview();
      });
    }
  }

  function togglePreviewMute() {
    if (playingIndex === null) return;
    previewMuted = !previewMuted;
    if (inlineYTPlayer) {
      if (previewMuted) { if (typeof inlineYTPlayer.mute === 'function') inlineYTPlayer.mute(); }
      else { if (typeof inlineYTPlayer.unMute === 'function') inlineYTPlayer.unMute(); }
    }
    if (inlineHTML5Video) inlineHTML5Video.muted = previewMuted;

    var tile = getTileElement(playingIndex);
    if (tile) {
      var audioBtn = tile.querySelector('.mall-tile-audio');
      if (audioBtn) {
        if (previewMuted) {
          audioBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
        } else {
          audioBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 010 14.14"/><path d="M15.54 8.46a5 5 0 010 7.07"/></svg>';
        }
      }
    }
    applyTilePreviewState(playingIndex, { previewing: true, paused: previewPaused, muted: previewMuted });
  }

  // ========== Page Visibility Resource Discipline ==========

  var visibilityBound = false;

  /**
   * Bind page visibility handler - pause preview when tab/page is hidden
   * to avoid burning resources offscreen (mobile battery discipline)
   */
  function bindVisibilityHandler() {
    if (visibilityBound) return;
    visibilityBound = true;

    document.addEventListener('visibilitychange', function() {
      if (document.hidden && playingIndex !== null) {
        // Page hidden: pause preview to save resources
        pauseInlinePreview();
      }
      // Note: we do NOT auto-resume on visible - user taps to resume
      // This is intentional: prevents unexpected audio/video playback
    });
  }

  // Locomotion state
  var dragScrollInstance = null;

  /**
   * Initialize tile field with catalog data
   * @param {Array} catalog - Array of FoundUp objects (with video data)
   */
  function initialize(catalog, options) {
    bindVideoOptionPlacement();
    // Search consumers replace their result set without reinstalling page listeners.
    if (tileField) {
      updateCatalog(catalog, options);
      return;
    }
    fullCatalog = Array.isArray(catalog) ? catalog.slice() : [];
    mallCatalog = fullCatalog.slice();
    originalOrder = mallCatalog.slice();  // Preserve original order
    currentFieldScope = null;  // Reset scope on init
    fixedVideoField = options?.fixedVideoField === true && mallCatalog.length === 1;
    entityPortraitField = options?.entityPortraitField === true && !fixedVideoField;
    replaceCatalogPager(options?.catalogPager);
    if (!catalogLifetimeBound) {
      catalogLifetimeBound = true;
      window.addEventListener('pagehide', function(event) {
        if (!event.persisted) { catalogPager?.close(); videoPager?.close(); selectionController?.abort(); }
      });
    }
    if (entityPortraitField) layoutMode = 'grid';
    scopedTheaterRequested = false;
    scopedPlaybackDismissed = false;
    scopedTheaterState = null;
    if (fixedVideoField) {
      expandedFoundUp = 0;
      layoutMode = 'grid';
    }
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

    configureGroups(options);
    desktopPosterBrowsing = window.matchMedia?.('(min-width: 1024px) and (hover: hover) and (pointer: fine)').matches === true;
    if (desktopPosterBrowsing && !fixedVideoField && groupDefinitions === null) layoutMode = 'grid';

    // Create collapse hint
    if (fixedVideoField) setMotionMode('glide');
    else createCollapseHint();

    // Auto-select density based on viewport (respects manual override)
    autoSelectDensity();

    // Bind resize handler for adaptive density
    window.addEventListener('resize', handleResize);

    // Enable desktop drag-to-scroll
    bindDragScroll();

    // Track scroll state for edge shadows
    bindScrollState();

    // Bind page visibility handler for resource discipline
    bindVisibilityHandler();

    renderTiles();
    bindInteractions();
    bindProjectionChips();
    if (fixedVideoField) bindScopedPlayerHistory(mallCatalog[0].foundup_id);
    else {
      initTileObserver();
      if (groupDefinitions === null) {
        window.mallVideoProjection?.mountMemberDock?.();
        ensureDesktopBlockNav();
        bindBlockSwipe();
      }
      syncDesktopBlockNav();
    }
  }

  /** Replace a public result set. This is presentation, not an access-control gate. */
  function updateCatalog(catalog, options) {
    if (fixedVideoField) return false;
    if (!tileField) {
      initialize(catalog, options);
      return;
    }
    stopInlinePreview();
    window.mallVideoPlayer?.close?.({ restore: false });
    cancelEntitySelection();
    replaceCatalogPager(options?.catalogPager);
    if (window.mallPlanes && typeof window.mallPlanes.closeView === 'function') {
      window.mallPlanes.closeView();
    }
    expandedFoundUp = null;
    if (collapseHint) collapseHint.classList.remove('visible');
    fullCatalog = Array.isArray(catalog) ? catalog.slice() : [];
    mallCatalog = fullCatalog.slice();
    originalOrder = mallCatalog.slice();
    currentFieldScope = null;
    currentProjection = 'default';
    tileLoadStates = {};
    if (options && Object.prototype.hasOwnProperty.call(options, 'entityPortraitField')) {
      entityPortraitField = options.entityPortraitField === true;
      if (entityPortraitField) layoutMode = 'grid';
    }
    configureGroups(options);
    if (window.mallPlanes && typeof window.mallPlanes.setCatalog === 'function') {
      window.mallPlanes.setCatalog(mallCatalog);
    }
    renderTiles();
    bindInteractions();
    initTileObserver();
    updateProjectionChips();
  }

  /** Opt in atomically with initialize/updateCatalog(catalog, {groups}). */
  function configureGroups(options) {
    var entering = groupDefinitions === null;
    groupDefinitions = options && Array.isArray(options.groups) ? options.groups.map(function(group) {
      return group && typeof group.key === 'string' && group.key ? {
        key: group.key,
        label: typeof group.label === 'string' ? group.label : group.key,
        subtitle: typeof group.subtitle === 'string' ? group.subtitle : '',
        itemIds: Array.isArray(group.itemIds) ? group.itemIds.slice() : []
      } : null;
    }).filter(Boolean) : null;
    if (groupDefinitions !== null && entering) setMotionMode('snap');
  }

  function resolveGroups() {
    var itemIndices = Object.create(null);
    mallCatalog.forEach(function(item, index) {
      if (typeof item.listing_id !== 'string' || !item.listing_id) return;
      // An ambiguous listing ID cannot establish row membership.
      itemIndices[item.listing_id] = Object.prototype.hasOwnProperty.call(itemIndices, item.listing_id) ? -1 : index;
    });
    var seenGroups = Object.create(null);
    var seenItems = Object.create(null);
    return groupDefinitions.filter(function(group) {
      if (seenGroups[group.key]) return false;
      seenGroups[group.key] = true;
      return true;
    }).map(function(group) {
      var indices = [];
      group.itemIds.forEach(function(id) {
        if (typeof id !== 'string' || seenItems[id] || !Object.prototype.hasOwnProperty.call(itemIndices, id) || itemIndices[id] < 0) return;
        seenItems[id] = true;
        indices.push(itemIndices[id]);
      });
      return { key: group.key, label: group.label, subtitle: group.subtitle, indices: indices };
    }).filter(function(group) { return group.indices.length > 0; });
  }

  function groupForIndex(index) {
    for (var i = 0; i < visibleGroups.length; i++) {
      if (visibleGroups[i].indices.indexOf(index) !== -1) return visibleGroups[i];
    }
    return null;
  }

  function groupElement(key) {
    var rows = tileField.querySelectorAll('.mall-field-group');
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].dataset.groupKey === key) return rows[i];
    }
    return null;
  }

  function rowPosition(key) {
    if (!groupPositions[key]) groupPositions[key] = { left: 0, activeId: null, activeIndex: 0, anchorId: null, anchorOffset: 0 };
    return groupPositions[key];
  }

  function clampScroll(value, extent, viewport) {
    return Math.max(0, Math.min(Number.isFinite(value) ? value : 0, Math.max(0, extent - viewport)));
  }

  function rememberTrack(track, selectVisible) {
    if (restoringGroups) return;
    var tiles = track.querySelectorAll('.mall-tile');
    if (!tiles.length) return; // Keep a temporarily empty area's last position.
    var state = rowPosition(track.dataset.groupKey);
    state.left = track.scrollLeft;
    var anchor = tiles[0];
    tiles.forEach(function(tile) {
      if (tile.offsetLeft <= track.scrollLeft + 1) anchor = tile;
    });
    state.anchorId = anchor.dataset.listingId;
    state.anchorOffset = track.scrollLeft - anchor.offsetLeft;
    if (selectVisible) {
      var center = track.scrollLeft + track.clientWidth / 2;
      var nearest = tiles[0];
      tiles.forEach(function(tile) {
        if (Math.abs(tile.offsetLeft + tile.offsetWidth / 2 - center) < Math.abs(nearest.offsetLeft + nearest.offsetWidth / 2 - center)) nearest = tile;
      });
      state.activeId = nearest.dataset.listingId;
      state.activeIndex = Array.prototype.indexOf.call(tiles, nearest);
      updateGroupButtons(track.closest('.mall-field-group'));
    }
  }

  function setTrackScroll(track, left) {
    // A queued native scroll event from restoration/keyboard movement must not
    // replace the explicitly selected listing with a different visible card.
    if (track.scrollLeft !== left) track._mallScrollTarget = left;
    track.scrollLeft = left;
  }

  function rememberGroupScroll() {
    if (restoringGroups) return;
    var rows = tileField.querySelectorAll('.mall-field-group');
    if (!rows.length) return;
    groupScrollTop = tileFieldWrapper.scrollTop;
    var nearest = rows[0];
    rows.forEach(function(row) {
      if (Math.abs(row.offsetTop - groupScrollTop) < Math.abs(nearest.offsetTop - groupScrollTop)) nearest = row;
    });
    activeGroupKey = nearest.dataset.groupKey;
    groupScrollOffset = groupScrollTop - nearest.offsetTop;
  }

  function captureGroupState() {
    tileField.querySelectorAll('.mall-field-group-track').forEach(function(track) { rememberTrack(track); });
    rememberGroupScroll();
    var focused = document.activeElement;
    if (!focused || !tileField.contains(focused)) return null;
    var tile = focused.closest('.mall-tile');
    var row = focused.closest('.mall-field-group');
    return {
      id: tile && tile.dataset.listingId, foundupId: tile && tile.dataset.foundupId,
      groupKey: row && row.dataset.groupKey,
      groupIndex: row ? Array.prototype.indexOf.call(tileField.querySelectorAll('.mall-field-group'), row) : 0,
      itemIndex: tile && row ? Array.prototype.indexOf.call(row.querySelectorAll('.mall-tile'), tile) : 0
    };
  }

  function restoreGroupState(focus) {
    restoringGroups = true;
    visibleGroups.forEach(function(group) {
      var row = groupElement(group.key);
      var track = row.querySelector('.mall-field-group-track');
      var tiles = track.querySelectorAll('.mall-tile');
      var state = rowPosition(group.key);
      var anchor = null;
      tiles.forEach(function(tile) { if (tile.dataset.listingId === state.anchorId) anchor = tile; });
      setTrackScroll(track, clampScroll(anchor ? anchor.offsetLeft + state.anchorOffset : state.left, track.scrollWidth, track.clientWidth));
      updateGroupButtons(row);
    });
    var activeRow = groupElement(activeGroupKey);
    tileFieldWrapper.scrollTop = clampScroll(activeRow ? activeRow.offsetTop + groupScrollOffset : groupScrollTop, tileFieldWrapper.scrollHeight, tileFieldWrapper.clientHeight);
    restoringGroups = false;

    // Do not steal focus from an open search plane or from a filter input.
    if (!focus || tileField.closest('[inert]')) return;
    var target = null;
    tileField.querySelectorAll('.mall-tile').forEach(function(tile) {
      if (tile.dataset.listingId === focus.id && tile.dataset.foundupId === focus.foundupId) target = tile;
    });
    if (!target && visibleGroups.length) {
      var row = groupElement(focus.groupKey) || groupElement(visibleGroups[Math.min(Math.max(focus.groupIndex, 0), visibleGroups.length - 1)].key);
      var candidates = row.querySelectorAll('.mall-tile');
      target = candidates[Math.min(Math.max(focus.itemIndex, 0), candidates.length - 1)] || tileField.querySelector('.mall-tile');
    }
    if (target) {
      target.focus({ preventScroll: true });
      rememberActiveTile(target);
    }
    else {
      tileField.setAttribute('tabindex', '-1');
      tileField.focus({ preventScroll: true });
    }
  }

  function geographicTenant() {
    if (!tileField || groupDefinitions === null || !visibleGroups.length) return null;
    var tenant = null;
    for (var i = 0; i < mallCatalog.length; i++) {
      var id = mallCatalog[i] && mallCatalog[i].foundup_id;
      if (typeof id !== 'string' || !id || (tenant !== null && id !== tenant)) return null;
      tenant = id;
    }
    return tenant;
  }

  /** Public presentation state only: stable area/listing IDs, never user data. */
  function getGeographicState() {
    var tenant = geographicTenant();
    if (!tenant) return null;
    captureGroupState();
    return {
      version: 1, foundup_id: tenant, activeGroupKey: activeGroupKey,
      scrollTop: groupScrollTop, groupOffset: groupScrollOffset,
      rows: visibleGroups.map(function(group) {
        var state = rowPosition(group.key);
        return { key: group.key, activeId: state.activeId, activeIndex: state.activeIndex,
          anchorId: state.anchorId, anchorOffset: state.anchorOffset, left: state.left };
      })
    };
  }

  /** Restore only known groups and members, clamped to this rendered catalog. */
  function restoreGeographicState(state) {
    var tenant = geographicTenant();
    function boundedNumber(value, signed) {
      return typeof value === 'number' && Number.isFinite(value) &&
        value >= (signed ? -1e7 : 0) && value <= 1e7;
    }
    function validId(value, limit, nullable) {
      return nullable && value === null || typeof value === 'string' && value.length > 0 &&
        value.length <= limit && !/[\u0000-\u001f\u007f]/.test(value);
    }
    if (!tenant || !state || typeof state !== 'object' || Array.isArray(state) ||
        state.version !== 1 || state.foundup_id !== tenant ||
        !validId(state.activeGroupKey, 1024, true) ||
        !boundedNumber(state.scrollTop, false) || !boundedNumber(state.groupOffset, true) ||
        !Array.isArray(state.rows) || state.rows.length > 500) return false;
    var seen = Object.create(null);
    for (var i = 0; i < state.rows.length; i++) {
      var record = state.rows[i];
      if (!record || typeof record !== 'object' || Array.isArray(record) ||
          !validId(record.key, 1024, false) || seen[record.key] ||
          !validId(record.activeId, 160, true) || !validId(record.anchorId, 160, true) ||
          !Number.isInteger(record.activeIndex) || record.activeIndex < 0 || record.activeIndex > 500 ||
          !boundedNumber(record.left, false) || !boundedNumber(record.anchorOffset, true)) return false;
      seen[record.key] = true;
    }
    state.rows.forEach(function(record) {
      var group = visibleGroups.find(function(candidate) { return candidate.key === record.key; });
      if (!group) return;
      var ids = group.indices.map(function(index) { return mallCatalog[index].listing_id; });
      groupPositions[group.key] = {
        activeId: ids.indexOf(record.activeId) !== -1 ? record.activeId : null,
        activeIndex: Math.min(record.activeIndex, ids.length - 1),
        anchorId: ids.indexOf(record.anchorId) !== -1 ? record.anchorId : null,
        anchorOffset: record.anchorOffset, left: record.left
      };
    });
    activeGroupKey = visibleGroups.some(function(group) { return group.key === state.activeGroupKey; }) ? state.activeGroupKey : null;
    groupScrollTop = state.scrollTop;
    groupScrollOffset = state.groupOffset;
    restoreGroupState(null);
    return true;
  }

  function activeRowIndex(group) {
    var state = rowPosition(group.key);
    var selected = group.indices.findIndex(function(index) { return mallCatalog[index].listing_id === state.activeId; });
    return selected >= 0 ? selected : Math.min(state.activeIndex, group.indices.length - 1);
  }

  function updateGroupButtons(row) {
    var group = visibleGroups.find(function(item) { return item.key === row.dataset.groupKey; });
    if (!group) return;
    var selected = activeRowIndex(group);
    row.querySelectorAll('.mall-group-nav').forEach(function(button) {
      button.disabled = selected < 0 || (button.dataset.groupStep === '-1' ? selected <= 0 : selected >= group.indices.length - 1);
    });
  }

  function rememberActiveTile(tile) {
    var track = tile.closest('.mall-field-group-track');
    if (!track) return;
    var state = rowPosition(track.dataset.groupKey);
    state.activeId = tile.dataset.listingId;
    state.activeIndex = Array.prototype.indexOf.call(track.querySelectorAll('.mall-tile'), tile);
    updateGroupButtons(track.closest('.mall-field-group'));
  }

  function focusGroupedTile(tile, alignRow) {
    if (!tile || tileField.closest('[inert]')) return;
    var track = tile.closest('.mall-field-group-track');
    var row = track.closest('.mall-field-group');
    tile.focus({ preventScroll: true });
    rememberActiveTile(tile);
    setTrackScroll(track, clampScroll(tile.offsetLeft, track.scrollWidth, track.clientWidth));
    rememberTrack(track);
    if (alignRow) {
      tileFieldWrapper.scrollTop = clampScroll(row.offsetTop, tileFieldWrapper.scrollHeight, tileFieldWrapper.clientHeight);
      rememberGroupScroll();
    }
  }

  function navigateGroupedTile(tile, key) {
    var group = groupForIndex(Number(tile.dataset.index));
    if (!group) return;
    var groupIndex = visibleGroups.indexOf(group);
    var itemIndex = group.indices.indexOf(Number(tile.dataset.index));
    var vertical = key === 'ArrowUp' || key === 'ArrowDown';
    if (vertical) {
      var step = key === 'ArrowDown' ? 1 : -1;
      do { groupIndex += step; } while (visibleGroups[groupIndex] && !visibleGroups[groupIndex].indices.length);
      group = visibleGroups[groupIndex];
      if (!group) return;
      itemIndex = Math.max(0, activeRowIndex(group));
    } else {
      itemIndex += key === 'ArrowRight' ? 1 : -1;
      if (itemIndex < 0 || itemIndex >= group.indices.length) return;
    }
    var row = groupElement(group.key);
    var target = row.querySelectorAll('.mall-tile')[itemIndex];
    focusGroupedTile(target, vertical);
  }

  function bindGroupedRows() {
    tileField.querySelectorAll('.mall-field-group-track').forEach(function(track) {
      track.addEventListener('scroll', function() {
        var programmatic = Number.isFinite(track._mallScrollTarget) && Math.abs(track.scrollLeft - track._mallScrollTarget) < 1;
        delete track._mallScrollTarget;
        rememberTrack(track, !programmatic);
      }, { passive: true });
    });
    tileField.querySelectorAll('.mall-group-nav').forEach(function(button) {
      button.addEventListener('click', function() {
        var row = button.closest('.mall-field-group');
        var group = visibleGroups.find(function(item) { return item.key === row.dataset.groupKey; });
        if (!group) return;
        var index = activeRowIndex(group) + Number(button.dataset.groupStep);
        if (index >= 0 && index < group.indices.length) focusGroupedTile(row.querySelectorAll('.mall-tile')[index], false);
      });
    });
  }

  /**
   * Enable drag-to-scroll on desktop for the wrapper
   * Uses custom implementation with tap guard (gesture-engine lacks 2D + guard)
   */
  function bindDragScroll() {
    if (!tileFieldWrapper) return;

    // Clean up previous instance
    if (dragScrollInstance && dragScrollInstance.destroy) {
      dragScrollInstance.destroy();
    }

    // Custom implementation: 2D scroll + tap guard + is-dragging class
    {
      var isDragging = false;
      var startX = 0;
      var startY = 0;
      var scrollStartX = 0;
      var scrollStartY = 0;
      var dragMoved = false;
      var dragTrack = null;
      var dragAxis = null;
      var horizontalTarget = null;

      function onMouseDown(e) {
        // Each row uses its own horizontal track. Geographic rows retain their
        // axis lock; ordinary category browsing keeps the shared two-axis drag.
        if (groupDefinitions !== null) {
          if (tileField.closest('[inert]') || e.target.closest('button, a, input, select, textarea, [contenteditable]')) return;
          dragTrack = e.target.closest('.mall-field-group-track');
        } else {
          if (e.target.closest('button, a, input, select, textarea')) return;
          dragTrack = null;
        }
        if (e.button !== 0) return;

        isDragging = true;
        dragMoved = false;
        dragAxis = null;
        startX = e.clientX;
        startY = e.clientY;
        horizontalTarget = groupDefinitions !== null
          ? (dragTrack || tileFieldWrapper)
          : (e.target.closest('.mall-category-track') || tileFieldWrapper);
        scrollStartX = horizontalTarget.scrollLeft;
        scrollStartY = tileFieldWrapper.scrollTop;
        if (groupDefinitions === null) {
          tileFieldWrapper.classList.add('is-dragging');
          e.preventDefault();
        }
      }

      function onMouseMove(e) {
        if (!isDragging) return;
        var dx = e.clientX - startX;
        var dy = e.clientY - startY;
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
          dragMoved = true;
          tapGuardActive = true;
          tileFieldWrapper.classList.add('is-dragging');
          if (!dragAxis) dragAxis = dragTrack && Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
        }
        if (groupDefinitions === null) {
          horizontalTarget.scrollLeft = scrollStartX - dx;
          tileFieldWrapper.scrollTop = scrollStartY - dy;
        } else if (dragMoved) {
          e.preventDefault();
          if (dragAxis === 'x') {
            dragTrack.scrollLeft = clampScroll(scrollStartX - dx, dragTrack.scrollWidth, dragTrack.clientWidth);
            rememberTrack(dragTrack, true);
          } else {
            tileFieldWrapper.scrollTop = clampScroll(scrollStartY - dy, tileFieldWrapper.scrollHeight, tileFieldWrapper.clientHeight);
            rememberGroupScroll();
          }
        }
      }

      function onMouseUp() {
        if (!isDragging) return;
        isDragging = false;
        tileFieldWrapper.classList.remove('is-dragging');
        // Brief guard to prevent tap after drag
        if (dragMoved) {
          setTimeout(function() { tapGuardActive = false; }, 100);
        } else {
          tapGuardActive = false;
        }
        dragTrack = null;
        dragAxis = null;
        horizontalTarget = null;
      }

      tileFieldWrapper.addEventListener('mousedown', onMouseDown);
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);

      dragScrollInstance = {
        destroy: function() {
          tileFieldWrapper.removeEventListener('mousedown', onMouseDown);
          document.removeEventListener('mousemove', onMouseMove);
          document.removeEventListener('mouseup', onMouseUp);
        }
      };
    }
  }

  /**
   * Track scroll state for edge shadow indicators
   */
  function bindScrollState() {
    if (!tileFieldWrapper) return;

    function updateScrollState() {
      var canScrollUp = tileFieldWrapper.scrollTop > 10;
      var canScrollDown = tileFieldWrapper.scrollTop < (tileFieldWrapper.scrollHeight - tileFieldWrapper.clientHeight - 10);
      tileFieldWrapper.classList.toggle('can-scroll-up', canScrollUp);
      tileFieldWrapper.classList.toggle('can-scroll-down', canScrollDown);
      if (groupDefinitions !== null) rememberGroupScroll();
      if (fixedVideoField && !scopedPlaybackPosition) fixedBrowsePosition = captureFixedPosition();
    }

    tileFieldWrapper.addEventListener('scroll', updateScrollState, { passive: true });
    // Initial check
    updateScrollState();
  }

  /**
   * Create collapse hint element (shown when in expanded mode)
   */
  function createCollapseHint() {
    if (entityPortraitField) return;
    collapseHint = document.createElement('div');
    collapseHint.className = 'mall-tile-field-collapse-hint';
    collapseHint.textContent = 'Pinch in to collapse';
    collapseHint.id = 'tileFieldCollapseHint';
    document.body.appendChild(collapseHint);
  }

  /**
   * Render the existing Mall tile interaction for a public property record.
   * Property identity belongs to a FoundUp; it is not a synthetic FoundUp ID.
   */
  function isPropertyListing(item) {
    return !!item && item.source_type === 'property_listing';
  }

  function propertyArea(value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0
      ? value.toLocaleString('en-US') + ' m\u00b2' : 'Not stated';
  }

  function renderPropertyTile(item, index) {
    var name = item.name || item.title || 'House listing';
    var location = [item.locality || item.locality_ja, item.municipality, item.prefecture, item.country].filter(Boolean).join(' \u00b7 ');
    var price = typeof item.price_jpy === 'number' && Number.isFinite(item.price_jpy) && item.price_jpy >= 0
      ? '\u00a5' + item.price_jpy.toLocaleString('en-US') : item.price_status === 'negotiable' ? 'Price negotiable' : 'Price not stated';
    var condition = item.repair_level === 'major' ? 'Major repairs required' :
      item.repair_level === 'some' ? 'Some repairs required' :
      item.repair_level === 'none_reported' ? 'No repairs reported at source' : 'Repair needs not stated';
    var theme = /^[a-z0-9_-]+$/i.test(item.theme || '') ? item.theme : 'default';
    // Source photographs remain on their original listing. Ignore supplied video,
    // token, readiness, avatar and poster fields on property records.
    return '<article class="mall-tile non-video property-listing theme-' + theme + '" data-index="' + index +
      '" data-foundup-id="' + escapeAttr(item.foundup_id || '') + '" data-listing-id="' + escapeAttr(item.listing_id || '') +
      '" data-tile-type="property" tabindex="0" role="button" aria-haspopup="dialog" aria-label="' + escapeAttr(name + ', ' + price + ', ' + location) + '">' +
      '<span class="mall-property-photo-note">Photos at source</span>' +
      '<div class="mall-tile-inner">' +
        '<span class="mall-property-location">' + escapeHtml(location) + '</span>' +
        '<p class="mall-tile-name">' + escapeHtml(name) + '</p>' +
        '<strong class="mall-property-price">' + escapeHtml(price) + '</strong>' +
        '<span class="mall-property-area">Land ' + escapeHtml(propertyArea(item.land_area_m2)) + '</span>' +
        '<span class="mall-property-area">Building ' + escapeHtml(propertyArea(item.building_area_m2)) + '</span>' +
        '<span class="mall-property-condition">' + escapeHtml(condition) + '</span>' +
        '<span class="mall-property-open">View house details \u2197</span>' +
      '</div></article>';
  }

  function isEntityGrid() {
    return entityPortraitField && !fixedVideoField && expandedFoundUp === null &&
      groupDefinitions === null && layoutMode === 'grid';
  }

  function isSelectedEntityScope() {
    return entityPortraitField && !fixedVideoField && expandedFoundUp !== null;
  }

  function selectedDesktop() {
    return window.matchMedia?.('(min-width: 900px) and (hover: hover) and (pointer: fine)').matches === true;
  }

  function capturePlayerCaller(record, tile) {
    var bounds = tileFieldWrapper.getBoundingClientRect();
    return {
      foundupId: record.foundup_id || record.id,
      expandedId: expandedFoundUp === null ? null : mallCatalog[expandedFoundUp]?.foundup_id,
      videoId: tile?.dataset.videoId || null,
      scrollTop: tileFieldWrapper.scrollTop,
      scrollLeft: tileFieldWrapper.scrollLeft,
      offset: tile ? tile.getBoundingClientRect().top - bounds.top : null,
      rows: captureRowOffsets(),
      inlineOpen: tileFieldWrapper.classList.contains('member-inline-open'),
      fieldScope: currentFieldScope,
      projection: currentProjection,
      catalogEpoch: catalogEpoch
    };
  }

  function restorePlayerCaller(caller) {
    if (!caller || caller.catalogEpoch !== catalogEpoch) return null;
    var tile = null;
    if (fixedVideoField) {
      var queue = mallCatalog[0]?.videos || [];
      tile = getScopedTile(queue.findIndex(function(video) { return video.video_id === caller.videoId; }));
    } else if (caller.expandedId && expandedFoundUp !== null) {
      var lane = mallCatalog[expandedFoundUp];
      if (lane?.foundup_id === caller.expandedId) {
        var videoIndex = lane.videos.findIndex(function(video) { return video.video_id === caller.videoId; });
        if (videoIndex >= 0) tile = getTileElement(videoIndex);
      }
    } else {
      var index = mallCatalog.findIndex(function(item) { return (item.foundup_id || item.id) === caller.foundupId; });
      if (index >= 0) tile = getTileElement(index);
    }
    restoreRowOffsets(caller.rows);
    if (!restoreBrowsePosition(caller.scrollTop, caller.scrollLeft)) {
      tileFieldWrapper.scrollTo({ top: caller.scrollTop, left: caller.scrollLeft, behavior: 'instant' });
    }
    if (tile && Number.isFinite(caller.offset)) {
      var rect = tile.getBoundingClientRect();
      var bounds = tileFieldWrapper.getBoundingClientRect();
      if (rect.bottom <= bounds.top || rect.top >= bounds.bottom) {
        tileFieldWrapper.scrollTop += rect.top - bounds.top -
          Math.max(1 - rect.height, Math.min(caller.offset, bounds.height - 1));
      }
    }
    (tile || tileField.querySelector('.mall-tile'))?.focus({ preventScroll: true });
    return tile;
  }

  // One ephemeral caller belongs to the existing player session. The catalog,
  // pager and history owners remain authoritative; no second navigation stack.
  function preparePlayerReturn(record, tile, caller) {
    caller = caller || capturePlayerCaller(record, tile);
    playerCaller = caller;
    var foundupId = record.foundup_id || record.id;
    var historyView = { type: 'video', foundupId: foundupId, retainedPlayer: true };
    if (!fixedVideoField) window.mallStateRestore?.openView?.(historyView, caller);
    return {
      onReturnToMall: function(options) {
        if (caller.catalogEpoch !== catalogEpoch) return false;
        if (isSelectedEntityScope()) {
          retainedLane = {
            record: mallCatalog[expandedFoundUp], epoch: selectionEpoch, catalogEpoch: catalogEpoch,
            scrollTop: tileFieldWrapper.scrollTop, scrollLeft: tileFieldWrapper.scrollLeft,
            renderedCount: fixedRenderedCount, sourceIndex: expandSourceIndex,
            sourceVisual: expandSourceVisual, browseScrollTop: browseScrollTop
          };
          if (!caller.expandedId) collapseFoundUp({ retainPlayback: true });
        }
        tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
        // Restore the caller's original snap/anchor condition as well as its
        // pixels. Enabling mandatory snap here shifts a lane captured while
        // Floating by the player's former clearance height.
        tileFieldWrapper.classList.toggle('member-inline-open', caller.inlineOpen === true);
        desktopInlineTile = null;
        var origin = restorePlayerCaller(caller);
        if (!options?.fromHistory) {
          if (fixedVideoField) {
            if (window.history.state?.[SCOPED_PLAYER_HISTORY] === foundupId) window.history.back();
          } else window.mallStateRestore?.closeView?.('video');
        }
        window.mallStateRestore?.save?.();
        return origin;
      },
      onResumeFromMall: function(options) {
        if (caller.catalogEpoch !== catalogEpoch ||
            !fullCatalog.some(function(item) { return (item.foundup_id || item.id) === foundupId; })) return false;
        if (!fixedVideoField && (currentFieldScope !== caller.fieldScope || currentProjection !== caller.projection)) {
          setFieldScope(caller.fieldScope);
          if (currentProjection !== caller.projection) setProjection(caller.projection, { preserveScope: true });
        }
        if (retainedLane) {
          if (retainedLane.epoch !== selectionEpoch || retainedLane.catalogEpoch !== catalogEpoch ||
              retainedLane.record.foundup_id !== foundupId) return false;
          var index = mallCatalog.findIndex(function(item) { return item.foundup_id === foundupId; });
          if (index < 0) return false;
          expandedFoundUp = index;
          expandSourceIndex = index;
          expandSourceVisual = retainedLane.sourceVisual;
          browseScrollTop = retainedLane.browseScrollTop;
          renderTiles();
          if (retainedLane.renderedCount > fixedRenderedCount) renderTiles(retainedLane.renderedCount);
          bindInteractions();
          tileFieldWrapper.scrollTo({ top: retainedLane.scrollTop, left: retainedLane.scrollLeft, behavior: 'instant' });
          syncSelectedControls();
        }
        var player = window.mallVideoPlayer;
        var currentId = player.getCurrentVideoId?.();
        var currentTile;
        if (fixedVideoField) {
          currentTile = getScopedTile(mallCatalog[0].videos.findIndex(function(video) { return video.video_id === currentId; }));
        } else if (isSelectedEntityScope()) {
          var lane = mallCatalog[expandedFoundUp];
          var currentIndex = lane.videos.findIndex(function(video) { return video.video_id === currentId; });
          currentTile = currentIndex < 0 ? null : getTileElement(currentIndex);
        } else {
          var currentIndex = mallCatalog.findIndex(function(item) { return (item.foundup_id || item.id) === foundupId; });
          currentTile = currentIndex < 0 ? null : getTileElement(currentIndex);
        }
        if (!currentTile) return false;
        retainedLane = null;
        currentTile.setAttribute('aria-current', 'true');
        if (!fixedVideoField) {
          desktopInlineTile = currentTile;
          tileFieldWrapper.classList.add('member-inline-open');
        }
        if (!options?.fromHistory) {
          if (fixedVideoField) pushScopedPlayerHistory(foundupId);
          else window.mallStateRestore?.openView?.(historyView, caller);
        }
        return currentTile;
      }
    };
  }

  function replaceCatalogPager(session) {
    if (catalogPager === (session || null)) return;
    catalogPager?.close();
    catalogPager = session || null;
    catalogLoad = null;
    catalogRefreshPending = false;
    catalogError = '';
    catalogEpoch++;
  }

  function syncSelectedControls() {
    if (!entityPortraitField) return;
    var selected = isSelectedEntityScope();
    var visible = selected || pendingEntityId !== null;
    var header = document.querySelector('.mall-header');
    var logo = header?.querySelector('.mall-brand-minimal');
    if (logo && logo !== selectedLogo) {
      selectedLogo = logo;
      selectedLogoOriginal = { href: logo.getAttribute('href'), label: logo.getAttribute('aria-label') };
      logo.addEventListener('click', function(event) {
        if (entityPortraitField && (isSelectedEntityScope() || pendingEntityId !== null)) {
          event.preventDefault();
          returnEntityToMall();
        }
      });
    }
    if (logo) {
      if (visible) {
        logo.setAttribute('href', 'https://play.foundups.com/');
        logo.setAttribute('aria-label', 'Return to Play Mall');
      } else {
        ['href', 'aria-label'].forEach(function(attribute) {
          var value = attribute === 'href' ? selectedLogoOriginal.href : selectedLogoOriginal.label;
          if (value === null) logo.removeAttribute(attribute);
          else logo.setAttribute(attribute, value);
        });
      }
    }
    if (!selectedControls && header) {
      selectedControls = document.createElement('div');
      selectedControls.className = 'mall-selected-controls';
      selectedControls.innerHTML = '<button type="button" data-selected-back>Back to Mall</button>' +
        '<span class="mall-selected-label" role="status"></span>' +
        '<button type="button" data-selected-watch>Watch</button>';
      header.appendChild(selectedControls);
      selectedControls.querySelector('[data-selected-back]').addEventListener('click', returnEntityToMall);
      selectedControls.querySelector('[data-selected-watch]').addEventListener('click', function() {
        var player = window.mallVideoPlayer;
        var index = player?.isOpen?.() ? player.getCurrentIndex() : selectedVideoIndex;
        openDesktopVideo(index, false, { autoplay: true });
      });
    }
    if (selectedControls) {
      selectedControls.hidden = !visible;
      header.classList.toggle('mall-selected-header', visible);
      var item = selected ? mallCatalog[expandedFoundUp] : fullCatalog.find(function(record) {
        return record.foundup_id === pendingEntityId;
      });
      selectedControls.querySelector('.mall-selected-label').textContent = pendingEntityId
        ? 'Loading ' + (item?.name || item?.title || 'videos') + '…'
        : (item?.name || item?.title || 'Videos') + ' · Catalog order' + selectedNotice;
      selectedControls.querySelector('[data-selected-watch]').hidden = !selected || pendingEntityId !== null;
    }
    tileFieldWrapper?.classList.toggle('mall-selected-video-wrapper', selected);
    if (collapseHint) collapseHint.hidden = true;
    window.mallVideoPlayer?.syncFloatingGeometry?.();
  }

  function cancelEntitySelection() {
    var owned = isSelectedEntityScope() || pendingEntityId !== null || retainedLane !== null;
    retainedLane = null;
    playerCaller = null;
    selectionEpoch++;
    selectionController?.abort();
    selectionController = null;
    videoPager?.close();
    videoPager = null;
    videoLoad = null;
    if (videoRecord) videoRecord.videos = [];
    videoRecord = null;
    pendingEntityId = null;
    pendingSelection = null;
    selectedNotice = '';
    selectedVideoIndex = 0;
    discoveryError = '';
    if (owned) window.mallVideoPlayer?.close?.({ restore: false });
  }

  function returnEntityToMall() {
    if (window.mallVideoPlayer?.isOpen?.() && !window.mallVideoPlayer.isMallHidden?.()) {
      return window.mallVideoPlayer.returnToMall?.();
    }
    var sourceId = mallCatalog[expandedFoundUp ?? expandSourceIndex]?.foundup_id;
    if (isSelectedEntityScope()) collapseFoundUp();
    else cancelEntitySelection();
    syncSelectedControls();
    var source = mallCatalog.findIndex(function(item) { return item.foundup_id === sourceId; });
    var tile = source < 0 ? null : getTileElement(source);
    tile?.focus({ preventScroll: true });
    window.mallStateRestore?.save?.();
  }

  async function loadCatalogPage() {
    if (!catalogPager?.hasMore) return [];
    if (catalogLoad) return catalogLoad;
    var session = catalogPager;
    var epoch = catalogEpoch;
    catalogLoad = (async function() {
      try {
        var batch = await session.loadNext();
        if (session !== catalogPager || epoch !== catalogEpoch) return [];
        catalogError = '';
        batch.forEach(function(item) {
          if (!fullCatalog.some(function(existing) { return existing.foundup_id === item.foundup_id; })) fullCatalog.push(item);
        });
        window.mallPlanes?.setCatalog?.(fullCatalog);
        if (isSelectedEntityScope()) catalogRefreshPending = true;
        else {
          catalogRefreshPending = false;
          var canAppend = currentFieldScope === null && currentProjection === 'default';
          mallCatalog = filterByScope(currentFieldScope);
          originalOrder = mallCatalog.slice();
          mallCatalog = sortByProjection(currentProjection);
          if (canAppend) renderTiles(entityRenderedCount + FIXED_VIDEO_BATCH);
          else { renderTiles(); bindInteractions(); }
        }
        return batch;
      } catch (error) {
        if (session === catalogPager && error.name !== 'AbortError') {
          catalogError = 'Could not load the next cards. Use Load more cards to retry.';
          if (!isSelectedEntityScope()) {
            tileField.querySelector('.mall-video-grid-tail')?.remove();
            renderFixedTail(mallCatalog.length, true, FIXED_VIDEO_BATCH);
          }
        }
        return [];
      } finally { if (session === catalogPager && epoch === catalogEpoch) catalogLoad = null; }
    })();
    return catalogLoad;
  }

  async function loadSelectedPage() {
    if (window.mallVideoPlayer?.isMallHidden?.()) return [];
    if (!isSelectedEntityScope() || !videoPager?.hasMore) return [];
    if (videoLoad) return videoLoad;
    var session = videoPager;
    var epoch = selectionEpoch;
    var lane = mallCatalog[expandedFoundUp];
    videoLoad = (async function() {
      try {
        var batch = await session.loadNext();
        if (session !== videoPager || epoch !== selectionEpoch ||
            (!isSelectedEntityScope() && retainedLane?.record !== lane)) return [];
        discoveryError = '';
        var additions = batch.filter(function(video) {
          return !lane.videos.some(function(existing) { return existing.video_id === video.video_id; });
        });
        lane.videos.push.apply(lane.videos, additions);
        if (!window.mallVideoPlayer?.isMallHidden?.()) {
          renderTiles(fixedRenderedCount + FIXED_VIDEO_BATCH);
          window.mallVideoPlayer?.refreshQueue?.();
        }
        return additions;
      } catch (error) {
        if (session === videoPager && error.name !== 'AbortError') {
          discoveryError = 'Could not load the next videos. Use Load more videos to retry.';
          if (!window.mallVideoPlayer?.isMallHidden?.()) {
            tileField.querySelector('.mall-video-grid-tail')?.remove();
            renderFixedTail(lane.videos.length, false, FIXED_VIDEO_BATCH);
          }
        }
        return [];
      } finally { if (session === videoPager && epoch === selectionEpoch) videoLoad = null; }
    })();
    return videoLoad;
  }

  async function openEntityVideos(index, options) {
    var record = mallCatalog[index];
    if (!entityPortraitField || !record || isPropertyListing(record)) return false;
    if (window.mallVideoPlayer?.isMallHidden?.() && window.mallVideoPlayer.getFoundUpId?.() === record.foundup_id) {
      return window.mallVideoPlayer.resumeFromMall({ tileActivation: options?.tileActivation === true, autoplay: options?.autoplay !== false });
    }
    if (isSelectedEntityScope() && expandedFoundUp === index) {
      return openDesktopVideo(0, options?.immersive === true, {
        autoplay: options?.autoplay !== false, tileActivation: options?.tileActivation === true
      });
    }
    if (pendingEntityId === record.foundup_id && pendingSelection) return pendingSelection;
    if (!record.videos?.length && !record.video_pages?.catalog) {
      if (pendingEntityId === record.foundup_id) {
        cancelEntitySelection();
        syncSelectedControls();
      }
      return false;
    }
    if (isSelectedEntityScope()) collapseFoundUp();
    var callerIndex = mallCatalog.findIndex(function(item) { return item.foundup_id === record.foundup_id; });
    if (callerIndex < 0) return false;
    var caller = capturePlayerCaller(record, getTileElement(callerIndex));
    cancelEntitySelection();
    var epoch = selectionEpoch;
    var controller = new AbortController();
    selectionController = controller;
    pendingEntityId = record.foundup_id;
    discoveryError = '';
    syncSelectedControls();
    pendingSelection = (async function() {
      try {
        if (record.video_pages?.catalog) {
          var session = await window.mallDiscoveryPager.openVideos(record, 'catalog', { signal: controller.signal });
          if (controller.signal.aborted || epoch !== selectionEpoch) { session.close(); return false; }
          videoPager = session;
          videoRecord = record;
          record.videos = session.items.slice();
        }
        if (controller.signal.aborted || epoch !== selectionEpoch || !record.videos?.length) return false;
        index = mallCatalog.findIndex(function(item) { return item.foundup_id === record.foundup_id; });
        if (index < 0) { cancelEntitySelection(); syncSelectedControls(); return false; }
        pendingEntityId = null;
        expandFoundUp(index);
        browseScrollTop = caller.scrollTop;
        tileFieldWrapper.scrollTop = 0;
        var selectedIndex = options?.videoId ? record.videos.findIndex(function(video) {
          return video.video_id === options.videoId;
        }) : 0;
        if (selectedIndex < 0) {
          selectedIndex = 0;
          selectedNotice = ' · Previous video is outside the loaded page; showing its first video.';
        }
        selectedVideoIndex = selectedIndex;
        syncSelectedControls();
        openDesktopVideo(selectedIndex, options?.immersive === true, {
          autoplay: options?.autoplay !== false, queueQuery: options?.queueQuery,
          tileActivation: options?.tileActivation === true, caller: caller
        });
        window.mallStateRestore?.save?.();
        return true;
      } catch (error) {
        if (epoch === selectionEpoch && error.name !== 'AbortError') {
          pendingEntityId = null;
          discoveryError = 'Could not load videos. Select the card to retry.';
          syncSelectedControls();
          renderTiles(); bindInteractions();
        }
        return false;
      } finally { if (epoch === selectionEpoch) pendingSelection = null; }
    })();
    return pendingSelection;
  }

  async function openEntityById(foundupId, options) {
    if (!entityPortraitField || typeof foundupId !== 'string') return false;
    var missing = !fullCatalog.some(function(item) { return item.foundup_id === foundupId; });
    if (missing) {
      if (isSelectedEntityScope()) collapseFoundUp();
      else cancelEntitySelection();
      pendingEntityId = foundupId;
      syncSelectedControls();
    }
    var intent = selectionEpoch;
    var catalogIntent = catalogEpoch;
    while (!fullCatalog.some(function(item) { return item.foundup_id === foundupId; }) && catalogPager?.hasMore) {
      var batch = await loadCatalogPage();
      if (selectionEpoch !== intent || catalogEpoch !== catalogIntent) return false;
      if (!batch.length) { pendingEntityId = null; syncSelectedControls(); return false; }
    }
    if (selectionEpoch !== intent || catalogEpoch !== catalogIntent) return false;
    var index = mallCatalog.findIndex(function(item) { return item.foundup_id === foundupId; });
    if (index < 0) { pendingEntityId = null; syncSelectedControls(); return false; }
    return openEntityVideos(index, options);
  }

  // Catalog mappings are explicit registry evidence. A channel/profile ID is not
  // a FoundUp identity merely because it can be formatted as a route.
  function canonicalFoundUpId(item) {
    var identifier = item && item.canonical_foundup_id;
    return typeof identifier === 'string' && /^[a-z0-9][a-z0-9_-]{0,63}$/i.test(identifier) &&
      !['__proto__', 'constructor', 'prototype'].includes(identifier) ? identifier : null;
  }

  function validPublicHttpUrl(value) {
    if (typeof value !== 'string' || !value || /[\u0000-\u0020\\]/.test(value)) return '';
    try {
      var parsed = new URL(value);
      return parsed.protocol === 'https:' && parsed.hostname && !parsed.username && !parsed.password ? parsed.href : '';
    } catch (e) {
      return '';
    }
  }

  function publicLaunchLabel(item) {
    var fid = item && item.foundup_id;
    if (fid === 'autopost') return 'Enter AutoPost \u2197';
    if (fid === 'science_swarm') return 'Enter Science Swarm \u2197';
    if (fid === 'hpc') return 'Open HPC Shorts \u2197';
    if (fid === 'esingularity_001') return 'Open eSingularity.ai \u2197';
    if (item && (String(item.category || '').toLowerCase() === 'marketplace' || fid === 'gotjunk_001')) return 'Open Shop \u2197';
    if (item && item.source_type === 'github_repo') return 'View Repo \u2197';
    if (item && item.launch_readiness === 'discoverable_only') return 'Project Info \u2197';
    return 'Open Preview \u2197';
  }

  function openNonVideoFoundUpDetail(index) {
    var item = mallCatalog[index];
    if (!item) return;
    if (isEntityGrid() && item.discovery_kind === 'candidate') {
      var candidateTile = getTileElement(index);
      if (candidateTile) setCardFlipped(candidateTile, true, { pinned: true });
      return;
    }
    var foundupId = item.foundup_id || item.id;
    if (desktopInlineTile && !window.mallVideoPlayer?.isTucked?.() && !window.mallVideoPlayer?.isMallHidden?.()) window.mallVideoPlayer.close();
    if (foundupId && window.mallPlanes && typeof window.mallPlanes.openFoundUpById === 'function') {
      window.mallPlanes.openFoundUpById(foundupId);
      return;
    }
    if (foundupId) navigateToFoundUp(foundupId);
  }

  function stepMallBlock(direction) {
    if (!tileFieldWrapper || fixedVideoField || groupDefinitions !== null || expandedFoundUp !== null) return;
    var step = Math.max(240, Math.round((tileFieldWrapper.clientHeight || window.innerHeight || 640) * 0.72));
    var delta = (direction < 0 ? -1 : 1) * step;
    if (delta > 0 && isEntityGrid() && catalogPager?.hasMore &&
        (tileFieldWrapper.scrollTop + tileFieldWrapper.clientHeight >= tileFieldWrapper.scrollHeight - step)) {
      loadCatalogPage();
    }
    if (typeof tileFieldWrapper.scrollBy === 'function') {
      tileFieldWrapper.scrollBy({ top: delta, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    } else {
      tileFieldWrapper.scrollTop = clampScroll(tileFieldWrapper.scrollTop + delta, tileFieldWrapper.scrollHeight, tileFieldWrapper.clientHeight);
    }
  }

  function syncDesktopBlockNav() {
    if (!desktopBlockNav) return;
    desktopBlockNav.hidden = fixedVideoField || groupDefinitions !== null || expandedFoundUp !== null || !mallCatalog.length;
  }

  function ensureDesktopBlockNav() {
    var hostShell = document.querySelector('.mall-shell');
    if (!hostShell || desktopBlockNav) return desktopBlockNav;
    var nav = hostShell.querySelector('.mall-desktop-block-nav');
    if (!nav) {
      nav = document.createElement('div');
      nav.className = 'mall-desktop-block-nav';
      nav.setAttribute('aria-label', 'Mall block navigation');
      nav.innerHTML =
        '<button type="button" class="mall-block-step-btn" data-mall-block-step="-1" aria-label="Previous block" title="Previous block">\u25c0</button>' +
        '<button type="button" class="mall-block-step-btn" data-mall-block-step="1" aria-label="Next block" title="Next block">\u25b6</button>';
      hostShell.appendChild(nav);
    }
    if (!nav.dataset.blockNavBound) {
      nav.dataset.blockNavBound = '1';
      nav.querySelectorAll('[data-mall-block-step]').forEach(function(btn) {
        btn.addEventListener('click', function() {
          stepMallBlock(Number(btn.dataset.mallBlockStep || 1));
        });
      });
    }
    desktopBlockNav = nav;
    syncDesktopBlockNav();
    return desktopBlockNav;
  }

  function bindBlockSwipe() {
    if (!tileFieldWrapper || tileFieldWrapper.dataset.blockSwipeBound) return;
    tileFieldWrapper.dataset.blockSwipeBound = '1';
    var startX = 0;
    var startY = 0;
    var swipeActive = false;
    tileFieldWrapper.addEventListener('touchstart', function(e) {
      if (fixedVideoField || groupDefinitions !== null || layoutMode !== 'grid' || expandedFoundUp !== null || activeFlippedTile) {
        swipeActive = false;
        return;
      }
      if (!e.touches || e.touches.length !== 1 || e.target?.closest?.('.mall-card-back, .mall-field-group-track, .mall-category-track')) {
        swipeActive = false;
        return;
      }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      swipeActive = true;
    }, { passive: true });
    tileFieldWrapper.addEventListener('touchend', function(e) {
      if (!swipeActive) return;
      swipeActive = false;
      if (e.touches && e.touches.length > 0) return;
      if (!e.changedTouches || e.changedTouches.length !== 1) return;
      var dx = e.changedTouches[0].clientX - startX;
      var dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 64 && Math.abs(dx) > Math.abs(dy) * 1.6) {
        // Swipe LEFT advances next block; swipe RIGHT returns previous block
        stepMallBlock(dx < 0 ? 1 : -1);
      }
    }, { passive: true });
    tileFieldWrapper.addEventListener('touchcancel', function() { swipeActive = false; }, { passive: true });
  }

  function renderCardBack(item, index, canonical, cardHasVideos) {
    var name = item.name || item.title || 'Untitled source';
    var candidate = item.discovery_kind === 'candidate';
    var sourceLabel = item.source_type === 'linkedin_profile' ? 'Source profile' : 'Source channel';
    var kind = canonical ? 'FoundUp' : sourceLabel + ' · not a canonical FoundUp';
    var pitch = item.one_sentence_pitch || item.tagline || 'No public pitch provided.';
    var description = item.description || 'No public description provided.';
    var entitySub = (item.entity && item.entity !== name && item.entity !== (item.title || ''))
      ? '<p class="mall-card-kind">' + escapeHtml(item.entity) + '</p>' : '';
    var osp = ['outcome', 'solution', 'pain'].filter(function(key) { return item[key]; }).map(function(key) {
      return '<div class="mall-tile-osp-row"><span class="mall-tile-osp-kicker osp-' + key + '">' +
        key.charAt(0).toUpperCase() + key.slice(1) + '</span><p>' + escapeHtml(item[key]) + '</p></div>';
    }).join('');
    if (candidate) kind = 'Project candidate · canonical registration unverified';
    var stage = canonical || candidate ? 'Stage: ' + (item.lifecycle_stage || 'not supplied') +
      ' · ' + (item.launch_readiness || 'readiness not supplied').replace(/_/g, ' ') : '';
    var publicUrl = (!candidate) ? (validPublicHttpUrl(item.external_url) || validPublicHttpUrl(item.public_poc_url)) : '';
    var backExpandBtn = (!candidate && !cardHasVideos)
      ? '<button type="button" class="mall-card-expand-detail" data-expand-foundup="1" aria-label="' +
        escapeAttr('Expand ' + name + ' full details') + '" title="Expand full details (or pinch out)">\u2922</button>'
      : '';
    return '<section class="mall-card-back" id="mall-card-about-' + index + '" role="group" aria-label="' +
      escapeAttr('About ' + name) + '" hidden inert>' +
      '<div class="mall-card-back-bar">' +
        '<button type="button" class="mall-card-flip-back">Back to portrait</button>' +
        backExpandBtn +
      '</div>' +
      '<h3>' + escapeHtml(name) + '</h3>' +
      entitySub +
      '<p class="mall-card-kind">' + escapeHtml(kind) + '</p>' +
      '<p class="mall-card-pitch"><strong>Pitch</strong> ' + escapeHtml(pitch) + '</p>' +
      '<p>' + escapeHtml(description) + '</p>' +
      osp +
      (stage ? '<p class="mall-card-stage">' + escapeHtml(stage) + '</p>' : '') +
      (item.entry_copy ? '<p>' + escapeHtml(item.entry_copy) + '</p>' : '') +
      (candidate && item.public_plan_url === 'https://github.com/FOUNDUPS/Foundups-Agent/blob/72a3182c70974f0523be91d5ce4bd32808d824bc/modules/foundups/docs/PFMALL_OPPORTUNITY_INSTANCE_MODEL.md'
        ? '<a class="mall-card-plan" href="' + escapeAttr(item.public_plan_url) + '" target="_blank" rel="noopener noreferrer">Read public plan (new tab)</a>' : '') +
      ((item.videos?.length || item.video_pages?.catalog) ? '<button type="button" class="mall-tile-osp-play">Play queue</button>' : '') +
      (publicUrl ? '<a class="mall-card-public-launch" data-public-launch-id="' + escapeAttr(item.foundup_id || '') +
        '" href="' + escapeAttr(publicUrl) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(publicLaunchLabel(item)) + '</a>' : '') +
      (canonical ? '<button type="button" class="mall-card-enter" data-canonical-foundup-id="' +
        escapeAttr(canonical) + '">Enter FoundUp · Member Portal</button>' : '') +
      '</section>';
  }

  function setCardFlipped(tile, flipped, options) {
    var front = tile.querySelector('.mall-card-front');
    var back = tile.querySelector('.mall-card-back');
    if (!front || !back) return false;
    if (flipped && activeFlippedTile && activeFlippedTile !== tile) {
      setCardFlipped(activeFlippedTile, false, { focus: false });
    }
    tile.classList.toggle('is-card-flipped', flipped);
    if (flipped && options?.pinned) tile.dataset.flipPinned = '1';
    else if (!flipped || options?.pinned === false) delete tile.dataset.flipPinned;
    tile.tabIndex = flipped ? -1 : 0;
    front.hidden = front.inert = flipped;
    back.hidden = back.inert = !flipped;
    var trigger = front.querySelector('.mall-card-flip');
    if (trigger) trigger.setAttribute('aria-expanded', String(flipped));
    activeFlippedTile = flipped ? tile : (activeFlippedTile === tile ? null : activeFlippedTile);
    if (options?.focus !== false) {
      var targetFocus = flipped ? back.querySelector('.mall-card-flip-back') : trigger;
      if (targetFocus && typeof targetFocus.focus === 'function') targetFocus.focus({ preventScroll: true });
    }
    return flipped;
  }

  function renderTiles(appendThrough, keepSlot) {
    var entityGrid = isEntityGrid();
    var incremental = fixedVideoField || entityGrid || isSelectedEntityScope() || usesProgressivePatchGrid();
    var batchSize = activePatchBatchSize();
    var append = incremental && Number.isInteger(appendThrough);
    if (!append && desktopInlineTile && !window.mallVideoPlayer?.isTucked?.() && !window.mallVideoPlayer?.isMallHidden?.()) {
      window.mallVideoPlayer.close({ restore: false });
    }
    syncSelectedControls();
    var groupedFocus = captureGroupState();
    captureRowOffsets();
    var itemsToRender = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
    if (!append) fixedTailObserver?.disconnect();
    if (fixedVideoField && !append) scopedRenderedIndices = scopedVisibleIndices();
    var indices = fixedVideoField ? scopedRenderedIndices : null;
    if (indices) itemsToRender = indices.map(function(index) { return itemsToRender[index]; });
    var start = append ? (entityGrid ? entityRenderedCount : fixedRenderedCount) : 0;
    var end = incremental
      ? Math.min(itemsToRender.length, append ? appendThrough : batchSize)
      : itemsToRender.length;
    if (append && end <= start) return;
    if (!append) activeFlippedTile = null;
    var phoneLazyPosters = isPhonePatchViewport();
    var grouped = groupDefinitions !== null && expandedFoundUp === null;
    var memberPlayer = usesMemberVideoPlayer();
    var desktopGrid = memberPlayer && desktopPosterBrowsing && layoutMode === 'grid';
    visibleGroups = grouped ? resolveGroups() : [];
    tileField.setAttribute('data-layout', grouped ? 'grouped' : layoutMode);
    tileField.classList.toggle('mall-entity-portrait-grid', entityGrid);
    tileFieldWrapper.classList.toggle('mall-field-grouped-wrapper', grouped);
    tileFieldWrapper.classList.toggle('browse-rows', !grouped && layoutMode === 'rows');
    tileFieldWrapper.classList.toggle('desktop-poster-grid', desktopGrid);

    if ((!grouped && !itemsToRender.length) || (grouped && !visibleGroups.length)) {
      if (entityGrid) entityRenderedCount = 0;
      if (tileObserver) tileObserver.disconnect();
      if (fixedTailObserver) fixedTailObserver.disconnect();
      fixedRenderedCount = 0;
      tileLoadStates = {};
      tileField.classList.remove('expanded-mode');
      if (indices) {
        tileField.innerHTML = '<p class="mall-video-grid-empty" role="status">No videos match your search.</p>';
        return;
      }
      tileField.innerHTML = '<div class="mall-tile-field-empty"><span class="mall-tile-field-empty-icon">&#x1F6D2;</span><span>' + (catalogPager ? 'No loaded cards match these filters.' : 'No results match these filters') + '</span></div>';
      if (entityGrid && catalogPager?.hasMore) renderFixedTail(0, true, FIXED_VIDEO_BATCH);
      if (grouped) restoreGroupState(groupedFocus);
      return;
    }

    var tileMarkup = itemsToRender.slice(start, end).map(function(item, localIdx) {
      var index = localIdx + start;
      if (indices) index = indices[index];
      if (isPropertyListing(item)) return renderPropertyTile(item, index);
      var theme = escapeAttr(item.theme || item.foundup_id || CATEGORY_THEME[item.category] || 'default');
      var readiness = item.launch_readiness || item.status || 'discoverable_only';
      var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');

      // Video-backed: use channel_avatar_url (preferred) or poster_url as background
      // Track tile type for CSS background-size: avatar uses contain, video uses cover
      var isAvatarTile = !!item.channel_avatar_url && !item.video_data;
      var posterUrl = item.channel_avatar_url || item.poster_url || '';
      var memberMedia = item.video_data || item;
      var memberCard = window.mallVideoPlayer?.isMemberCardVideo?.(memberMedia) ? memberMedia.member_card : null;
      if (memberCard) posterUrl = '';
      var deferPoster = phoneLazyPosters && !append && index >= loadPolicy.loadBatchSize && !!posterUrl;
      var posterStyle = (posterUrl && !deferPoster) ? 'background-image: url(' + escapeAttr(posterUrl) + ')' : '';
      var posterDataAttr = posterUrl ? ' data-poster-url="' + escapeAttr(posterUrl) + '"' : '';
      var tileType = isAvatarTile ? 'avatar' : 'video';
      var canonical = canonicalFoundUpId(item);
      var candidate = item.discovery_kind === 'candidate';
      var cardBack = !fixedVideoField && expandedFoundUp === null;
      var sourceLabel = item.source_type === 'linkedin_profile' ? 'Source profile' : 'Source channel';
      if (entityGrid) tileType = canonical ? 'foundup' : candidate ? 'candidate' : 'source';

      // Determine if tile has videos (includes expanded video tiles with video_data)
      var hasVideos = item.videos?.length || item.video_data || (entityPortraitField && item.video_pages?.catalog && item.video_count) || (!memberPlayer && item.video_count);
      var inlineControls = hasVideos && !fixedVideoField && !memberPlayer;

      // Queue count (true_video_count preferred, then video_count, then videos array length)
      var queueCount = item.true_video_count || item.video_count || (item.videos ? item.videos.length : 0);
      var queueBadge = queueCount > 0 ? '<span class="mall-tile-queue-count">' + queueCount + ' videos</span>' : '';

      // Play indicator — video tiles only
      var playIndicator = inlineControls ? '<div class="mall-tile-play-indicator"></div>' : '';

      // Corner expand button for explicit fullscreen entry — video tiles only
      var expandIcon = fixedVideoField
        ? '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M14 4h6v6m0-6-6 6M10 20H4v-6m0 6 6-6"/></svg>'
        : '&#9654;';
      var expandBtn = hasVideos ? '<button type="button" class="mall-tile-expand" aria-label="Open fullscreen" title="Fullscreen">' + expandIcon + '</button>' : '';
      var detailExpandBtn = (!hasVideos && cardBack && !candidate)
        ? '<button type="button" class="mall-card-expand-detail" data-expand-foundup="1" aria-label="' +
          escapeAttr('Expand ' + (item.name || item.title || 'this card') + ' full details') +
          '" title="Expand full details (or pinch out)">\u2922</button>'
        : '';

      // Enter FoundUp button (bottom-left, visible during preview) — video tiles only
      // Uses stable foundup_id for WSP 104 canonical routing
      var enterFoundupBtn = inlineControls && (!entityPortraitField || canonicalFoundUpId(mallCatalog[expandedFoundUp ?? index])) ? '<button class="mall-tile-enter" aria-label="Enter FoundUp" title="Enter FoundUp"><svg viewBox="0 0 24 24"><path d="M15 3h6v6M14 10l6.1-6.1M9 21H3v-6M10 14l-6.1 6.1"/></svg></button>' : '';

      // Inline preview container (YouTube iframe or HTML5 video goes here) — video tiles only
      var previewContainer = inlineControls ? '<div class="mall-tile-preview"><div class="mall-tile-preview-stage"></div></div>' : '';

      // Speaker button for mute/unmute (top-left, video-backed only)
      var speakerSvg = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
      var audioBtn = inlineControls ? '<button class="mall-tile-audio" aria-label="Start muted preview" title="Start muted preview">' + speakerSvg + '</button>' : '';

      // Non-video source type action badge
      var sourceTypeActions = {
        'github_repo': 'View Repo',
        'external_app': 'Open App',
        'internal_app': 'Open App',
        'internal_service': 'Open Service'
      };
      var sourceAction = !entityGrid && !hasVideos && item.source_type && sourceTypeActions[item.source_type];
      var sourceActionBadge = sourceAction ? '<span class="mall-tile-action-badge">' + sourceAction + '</span>' : '';

      // Non-video tile class modifier
      var tileClass = 'mall-tile theme-' + theme + (hasVideos ? '' : ' non-video') + (memberCard ? ' mall-member-card' : '');

      var videoId = (fixedVideoField || isSelectedEntityScope()) ? ' data-video-id="' + escapeAttr(item.video_data?.video_id || '') + '"' : '';
      var classification = entityGrid ? ' data-catalog-kind="' + (canonical ? 'foundup' : candidate ? 'candidate' : 'source') +
        '" data-canonical-foundup-id="' + escapeAttr(canonical || '') + '"' : '';
      return '<article class="' + tileClass + '" data-index="' + index + '"' + videoId + posterDataAttr + classification + ' data-foundup-id="' + escapeAttr(item.foundup_id || item.id || '') + '" data-tile-type="' + tileType + '" tabindex="0" aria-label="' + escapeAttr(item.name || item.title || '') + '" style="' + posterStyle + '">' +
        (cardBack ? '<div class="mall-card-front">' : '') +
        previewContainer +
        (fixedVideoField ? '' : '<span class="mall-tile-badge ' + badgeClass + '">' +
          escapeHtml(entityGrid ? (canonical ? 'FoundUp' : candidate ? 'Project candidate' : sourceLabel) : readiness.replace('_', ' ')) + '</span>') +
        detailExpandBtn +
        queueBadge +
        sourceActionBadge +
        playIndicator +
        audioBtn +
        enterFoundupBtn +
        (memberCard ? '' : expandBtn) +
        (memberCard ? renderMemberCard(memberCard, expandBtn) : '<div class="mall-tile-inner">' +
          '<span class="mall-tile-token">' + escapeHtml(item.token_symbol || '') + '</span>' +
          '<span class="mall-tile-hero">' + escapeHtml(item.hero_label || '') + '</span>' +
          '<p class="mall-tile-name">' + escapeHtml(item.name || item.title || '') + '</p>' +
        '</div>') +
        (cardBack ? '<button type="button" class="mall-card-flip" aria-expanded="false" aria-controls="mall-card-about-' +
          index + '" aria-label="' + escapeAttr('About ' + (item.name || item.title || 'this source')) + '">About</button></div>' +
          renderCardBack(item, index, canonical, !!hasVideos) : '') +
      '</article>';
    });

    if (append) {
      tileField.querySelector('.mall-video-grid-tail')?.remove();
      tileField.insertAdjacentHTML('beforeend', tileMarkup.join(''));
    } else if (grouped) {
      if (fixedTailObserver) fixedTailObserver.disconnect();
      fixedRenderedCount = 0;
      tileField.innerHTML = visibleGroups.map(function(group, groupIndex) {
        var headingId = 'mallGroupHeading-' + groupIndex;
        var trackId = 'mallGroupTrack-' + groupIndex;
        return '<section class="mall-field-group" data-group-key="' + escapeAttr(group.key) + '" aria-labelledby="' + headingId + '">' +
          '<header class="mall-field-group-header"><div>' +
            '<h2 class="mall-field-group-heading" id="' + headingId + '">' + escapeHtml(group.label) + '</h2>' +
            (group.subtitle ? '<p class="mall-field-group-subtitle">' + escapeHtml(group.subtitle) + '</p>' : '') +
          '</div><div class="mall-field-group-controls">' +
            '<button class="mall-group-nav" data-group-step="-1" type="button" aria-label="' + escapeAttr('Previous home in ' + group.label) + '" aria-controls="' + trackId + '">\u2190</button>' +
            '<button class="mall-group-nav" data-group-step="1" type="button" aria-label="' + escapeAttr('Next home in ' + group.label) + '" aria-controls="' + trackId + '">\u2192</button>' +
          '</div></header>' +
          '<div class="mall-field-group-track" id="' + trackId + '" data-group-key="' + escapeAttr(group.key) + '" role="group" aria-labelledby="' + headingId + '">' +
            (group.indices.length ? group.indices.map(function(index) { return tileMarkup[index]; }).join('') : '<p class="mall-field-group-empty">No homes match in this area.</p>') +
          '</div></section>';
      }).join('');
      bindGroupedRows();
      restoreGroupState(groupedFocus);
    } else if (layoutMode === 'rows' && expandedFoundUp === null) {
      if (fixedTailObserver) fixedTailObserver.disconnect();
      fixedRenderedCount = 0;
      var groups = new Map();
      itemsToRender.forEach(function(item, index) {
        var key = item.category || 'Other';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(tileMarkup[index]);
      });
      var rows = [];
      groups.forEach(function(markup, key) {
        rows.push('<section class="mall-category-row"><h2 class="mall-category-title">' + escapeHtml(key) + '</h2>' +
          '<div class="mall-row-controls"><button type="button" data-row-step="-1" aria-label="Previous in ' + escapeAttr(key) + '">←</button>' +
          '<button type="button" data-row-step="1" aria-label="Next in ' + escapeAttr(key) + '">→</button></div>' +
          '<div class="mall-category-track" data-row-key="' + escapeAttr(key) + '" tabindex="0" role="region" aria-label="' + escapeAttr(key) + '">' + markup.join('') + '</div></section>');
      });
      tileField.innerHTML = rows.join('');
      tileField.querySelectorAll('[data-row-step]').forEach(function(button) {
        button.addEventListener('click', function() {
          var track = button.closest('.mall-category-row').querySelector('.mall-category-track');
          track.scrollBy({ left: Number(button.dataset.rowStep) * track.clientWidth * 0.8,
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        });
      });
      restoreRowOffsets(rowOffsets);
    } else if (keepSlot) {
      Array.from(tileField.children).forEach(function(child) {
        if (child !== keepSlot) child.remove();
      });
      keepSlot.insertAdjacentHTML('beforebegin', tileMarkup.join(''));
    } else {
      tileField.innerHTML = tileMarkup.join('');
    }

    // Update expanded mode class
    tileField.classList.toggle('expanded-mode', expandedFoundUp !== null);

    var tiles = tileField.querySelectorAll('.mall-tile');
    if (append) {
      tiles = Array.from(tiles).slice(start);
      observeTiles(tiles);
      bindInteractions(tiles);
    } else {
      tileLoadStates = {};
      initTileObserver();
    }
    if (incremental) {
      if (entityGrid) entityRenderedCount = end;
      else fixedRenderedCount = end;
      renderFixedTail(itemsToRender.length, entityGrid, batchSize);
    }
    syncDesktopBlockNav();
  }

  // Typed media uses the same selection and accessible expand controls.
  function renderMemberCard(card, expandBtn) {
    var hashtag = String(card.hashtag || '');
    var action = /OUT$/.test(hashtag)
      ? escapeHtml(hashtag.slice(0, -3)) + '<strong>OUT</strong>' : escapeHtml(hashtag);
    return '<div class="mall-member-card-content">' +
      '<header class="mall-member-card-heading"><h3>' + escapeHtml(card.name || '') + '</h3>' +
      '<p>' + escapeHtml([card.chamber, card.constituency].filter(Boolean).join(' · ')) + '</p></header>' +
      '<div class="mall-member-card-art"><picture><source media="(prefers-reduced-motion: no-preference)" type="image/webp" srcset="' +
      escapeAttr(card.animation_url || card.still_url || '') + '"><img src="' + escapeAttr(card.still_url || '') +
      '" alt="' + escapeAttr('AI caricature of ' + (card.name || 'a member of Congress')) + '" loading="lazy"></picture>' + (expandBtn || '') + '</div>' +
      '<footer class="mall-member-card-footer"><p class="mall-member-card-hashtag">' + action + '</p>' +
      '<p class="mall-member-card-scores"><span>UDP <b>Pending</b></span><span>CU <b>Pending</b></span></p></footer></div>';
  }

  function renderFixedTail(total, entityGrid, batchSize) {
    tileField.querySelector('.mall-grid-add-video')?.remove();
    var step = batchSize || FIXED_VIDEO_BATCH;
    var fieldError = entityGrid ? (catalogError || discoveryError) : discoveryError;
    fixedTailObserver?.disconnect();
    var tail = document.createElement('div');
    tail.className = 'mall-video-grid-tail';
    var rendered = entityGrid ? entityRenderedCount : fixedRenderedCount;
    var session = entityGrid ? catalogPager : (isSelectedEntityScope() ? videoPager : null);
    if (rendered < total || session?.hasMore) {
      var more = document.createElement('button');
      more.type = 'button';
      more.textContent = entityGrid ? 'Load more cards' : 'Load more videos';
      var load = async function() {
        if (!tail.isConnected || more.disabled) return;
        more.disabled = true;
        more.setAttribute('aria-busy', 'true');
        if (rendered < total) renderTiles(rendered + step);
        else if (entityGrid) await loadCatalogPage();
        else await loadSelectedPage();
        if (tail.isConnected) {
          more.disabled = false;
          more.removeAttribute('aria-busy');
        }
      };
      more.addEventListener('click', load);
      tail.appendChild(more);
      if (typeof IntersectionObserver !== 'undefined') {
        fixedTailObserver = new IntersectionObserver(function(entries) {
          // Paged startup stays at six; scrolling or the explicit button admits
          // the next small page. Intersection alone never drains a collection.
          if (!fieldError && (!session || tileFieldWrapper.scrollTop > 0) && entries.some(function(entry) { return entry.isIntersecting; })) load();
        }, { root: tileFieldWrapper, rootMargin: '120px 0px' });
        fixedTailObserver.observe(tail);
      }
    } else tail.textContent = entityGrid ? 'End of catalog' : 'End of collection';
    if (fieldError) {
      var error = document.createElement('p');
      error.setAttribute('role', 'status');
      error.textContent = fieldError;
      tail.appendChild(error);
    }
    if (fixedVideoField && mallCatalog[0]?.foundup_id === 'hpc') {
      var addVideo = document.createElement('button');
      addVideo.type = 'button';
      addVideo.className = 'mall-grid-add-video';
      addVideo.setAttribute('aria-label', 'Add Video to HPC');
      addVideo.innerHTML = '<span aria-hidden="true">+</span><span>Add Video</span>';
      addVideo.addEventListener('click', function () {
        window.mallVideoProjection?.showContributionReview?.({ action: 'add-video', foundupId: 'hpc' }, false, addVideo);
      });
      if (window.mallStateRestore?.getVideoOptions?.().addVideoPosition === 'first') tileField.prepend(addVideo);
      else tileField.appendChild(addVideo);
    }
    tileField.appendChild(tail);
  }

  function captureFixedPosition(tile) {
    if (!tileFieldWrapper || !tileField) return null;
    var top = tileFieldWrapper.getBoundingClientRect().top;
    var state = { scrollTop: tileFieldWrapper.scrollTop, scrollLeft: 0 };
    tile = tile || Array.from(tileField.querySelectorAll('.mall-tile')).find(function(card) {
      return card.getBoundingClientRect().bottom > top;
    });
    if (tile?.dataset.videoId) {
      state.anchorVideoId = tile.dataset.videoId;
      state.anchorOffset = tile.getBoundingClientRect().top - top;
    }
    return state;
  }

  function rememberTheater() {
    var player = window.mallVideoPlayer;
    if (player?.isMallHidden?.()) return;
    if (!player?.isTheater?.()) return;
    scopedTheaterState = {
      videoId: mallCatalog[0].videos[player.getCurrentIndex()].video_id,
      query: player.getQueueQuery()
    };
  }

  function getVideoGridState() {
    if (!fixedVideoField) return null;
    rememberTheater();
    var position = scopedPlaybackPosition || captureFixedPosition();
    if (!position) return null;
    if (scopedTheaterState) position = { ...position, theater: scopedTheaterState };
    return scopedPhoneQuery ? { ...position, phoneQuery: scopedPhoneQuery } : position;
  }

  function restoreVideoGridState(state) {
    if (!fixedVideoField || !state || !tileFieldWrapper) return false;
    if (state.theater) scopedTheaterState = state.theater;
    if (typeof state.phoneQuery === 'string' && state.phoneQuery !== scopedPhoneQuery) {
      updateScopedPhoneQuery(state.phoneQuery);
      syncScopedTiles();
    }
    var queue = mallCatalog[0].videos || [];
    var index = state.anchorVideoId ? queue.findIndex(function(video) {
      return video.video_id === state.anchorVideoId;
    }) : -1;
    var tile = getScopedTile(index);
    var targetTop = state.scrollTop;
    if (tile) {
      var rect = tile.getBoundingClientRect();
      var offset = Math.max(1 - rect.height, Math.min(state.anchorOffset, tileFieldWrapper.clientHeight - 1));
      targetTop = tileFieldWrapper.scrollTop + rect.top - tileFieldWrapper.getBoundingClientRect().top - offset;
    }
    while (fixedRenderedCount < scopedVisibleCount() &&
        targetTop > tileFieldWrapper.scrollHeight - tileFieldWrapper.clientHeight) {
      renderTiles(fixedRenderedCount + FIXED_VIDEO_BATCH);
    }
    tileFieldWrapper.scrollTop = targetTop;
    tileFieldWrapper.scrollLeft = 0;
    fixedBrowsePosition = captureFixedPosition();
    return true;
  }

  function scopedVisibleCount() {
    return scopedRenderedIndices?.length ?? mallCatalog[0].videos.length;
  }

  function scopedVisibleIndices() {
    return scopedTheaterRequested ? null : scopedPhonePlaybackIndices || scopedPhoneIndices;
  }

  function matchesScopedVideo(video, query) {
    return matchesCatalogQuery({ creator: video.source_label, videos: [video] }, query);
  }

  function updateScopedPhoneQuery(query) {
    scopedPhoneQuery = query.trim().slice(0, 300);
    scopedPhoneIndices = scopedPhoneQuery ? [] : null;
    scopedPhonePlaybackIndices = null;
    if (scopedPhoneIndices) {
      mallCatalog[0].videos.forEach(function(video, index) {
        if (matchesScopedVideo(video, scopedPhoneQuery)) scopedPhoneIndices.push(index);
      });
    }
  }

  function replaceScopedTiles() {
    renderTiles(undefined, tileField.querySelector('.mall-inline-player-slot'));
    bindInteractions();
  }

  function syncScopedTiles() {
    if (scopedRenderedIndices !== scopedVisibleIndices()) replaceScopedTiles();
  }

  function setScopedPhoneQuery(query) {
    if (!fixedVideoField || scopedTheaterRequested || typeof query !== 'string') return;
    // Filtering the browsing field must not dismiss its separate shared player.
    // Its existing queue remains scoped until a deliberate new selection.
    updateScopedPhoneQuery(query);
    replaceScopedTiles();
    tileFieldWrapper.scrollTop = 0;
    fixedBrowsePosition = captureFixedPosition();
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
        theme: foundup.theme || foundup.foundup_id || CATEGORY_THEME[foundup.category] || 'default',
        launch_readiness: foundup.launch_readiness || foundup.status || 'discoverable_only',
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
  function bindInteractions(batch) {
    var tiles = batch || tileField.querySelectorAll('.mall-tile');

    tiles.forEach(function(tile) {
      var hasOspBack = !!tile.querySelector('.mall-card-back');
      var hoverTimer = null;
      var holdTimer = null;
      var holdTriggered = false;
      var holdStartX = 0;
      var holdStartY = 0;

      if (hasOspBack) {
        tile.addEventListener('pointerenter', function(e) {
          if (e.pointerType !== 'mouse') return;
          clearTimeout(hoverTimer);
          hoverTimer = setTimeout(function() {
            if (!tapGuardActive && tile.isConnected && !tile.contains(document.activeElement) &&
                !activeFlippedTile?.contains(document.activeElement)) {
              setTileFlipped(tile, true, { focus: false });
            }
          }, HOVER_FLIP_DELAY_MS);
        });
        tile.addEventListener('pointerleave', function(e) {
          if (e.pointerType !== 'mouse') return;
          clearTimeout(hoverTimer);
          hoverTimer = null;
          if (tile.classList.contains('is-card-flipped') && tile.dataset.flipPinned !== '1' && !tile.contains(document.activeElement)) {
            setTileFlipped(tile, false, { focus: false });
          }
        });
        tile.addEventListener('touchstart', function(e) {
          if (!e.touches || e.touches.length !== 1) {
            clearTimeout(holdTimer);
            holdTimer = null;
            return;
          }
          if (e.target && e.target.closest && e.target.closest('button, a')) return;
          holdStartX = e.touches[0].clientX;
          holdStartY = e.touches[0].clientY;
          holdTriggered = false;
          clearTimeout(holdTimer);
          holdTimer = setTimeout(function() {
            holdTimer = null;
            if (!tile.isConnected) return;
            holdTriggered = true;
            tapGuardActive = true;
            setTileFlipped(tile, !tile.classList.contains('is-card-flipped'), { pinned: true });
          }, HOLD_FLIP_DELAY_MS);
        }, { passive: true });
        tile.addEventListener('touchmove', function(e) {
          if (!holdTimer) return;
          if (!e.touches || e.touches.length !== 1) {
            clearTimeout(holdTimer);
            holdTimer = null;
            return;
          }
          var dx = e.touches[0].clientX - holdStartX;
          var dy = e.touches[0].clientY - holdStartY;
          if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
            clearTimeout(holdTimer);
            holdTimer = null;
          }
        }, { passive: true });
        tile.addEventListener('touchend', function() {
          if (holdTimer) {
            clearTimeout(holdTimer);
            holdTimer = null;
          }
          if (holdTriggered) {
            holdTriggered = false;
            setTimeout(function() { tapGuardActive = false; }, 220);
          }
        }, { passive: true });
        tile.addEventListener('touchcancel', function() {
          if (holdTimer) {
            clearTimeout(holdTimer);
            holdTimer = null;
          }
          if (holdTriggered) tapGuardActive = false;
          holdTriggered = false;
        }, { passive: true });
      }

      // Tap selects playback or quick view according to the active layout.
      // FoundUp entry is explicit via fullscreen "Enter FoundUp" button
      tile.addEventListener('click', function(e) {
        clearTimeout(hoverTimer);
        if (tile.classList.contains('is-card-flipped')) return;
        if (e.target.closest('.mall-card-front[hidden], .mall-card-back, .mall-card-flip, .mall-card-expand-detail')) return;
        // Ignore tap if guard is active (just finished dragging)
        if (tapGuardActive) return;
        if (groupDefinitions !== null && tileField.closest('[inert]')) return;


        var index = Number(tile.dataset.index || 0);
        if (groupDefinitions !== null) rememberActiveTile(tile);
        togglePlay(index);
      });

      // Keyboard support
      tile.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && tile.classList.contains('is-card-flipped')) {
          e.preventDefault();
          e.stopPropagation();
          setCardFlipped(tile, false);
          return;
        }
        if (tile.classList.contains('is-card-flipped') ||
            (e.target !== tile && e.target.closest('.mall-card-flip, .mall-card-back, .mall-card-expand-detail'))) return;
        var index = Number(tile.dataset.index || 0);
        var memberPlayer = usesMemberVideoPlayer();
        if ((e.key === 'i' || e.key === 'f') && e.target === tile && hasOspBack) {
          e.preventDefault();
          setTileFlipped(tile, undefined, { pinned: true });
          return;
        }
        if ((fixedVideoField || memberPlayer) && e.target !== tile) return;
        if (groupDefinitions !== null && tileField.closest('[inert]')) return;
        if (groupDefinitions !== null && /^Arrow(Left|Right|Up|Down)$/.test(e.key)) {
          e.preventDefault();
          navigateGroupedTile(tile, e.key);
        } else if (e.key === ' ') {
          e.preventDefault();
          togglePlay(index);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          // Match the pointer path in the shared video presentations.
          if (fixedVideoField || memberPlayer) togglePlay(index);
          else if (isEntityGrid()) togglePlay(index);
          else openFullscreenFromTile(index);
        }
      });

      if (groupDefinitions !== null) {
        tile.addEventListener('focus', function() { rememberActiveTile(tile); });
      }

      var flip = tile.querySelector('.mall-card-flip');
      var flipBack = tile.querySelector('.mall-card-flip-back');
      if (flip && flipBack) {
        flip.addEventListener('click', function(e) {
          e.stopPropagation();
          if (!tapGuardActive) setCardFlipped(tile, true, { pinned: true });
        });
        flipBack.addEventListener('click', function(e) {
          e.stopPropagation();
          setCardFlipped(tile, false);
        });
        tile.querySelector('.mall-tile-osp-play')?.addEventListener('click', function(e) {
          e.stopPropagation();
          if (tapGuardActive) return;
          setCardFlipped(tile, false);
          togglePlay(Number(tile.dataset.index || 0));
        });
        tile.querySelector('.mall-card-public-launch')?.addEventListener('click', function(e) {
          e.stopPropagation();
        });
        tile.querySelector('.mall-card-enter')?.addEventListener('click', function(e) {
          e.stopPropagation();
          navigateToFoundUp(e.currentTarget.dataset.canonicalFoundupId);
        });
      }
      tile.querySelectorAll('.mall-card-expand-detail').forEach(function(detailBtn) {
        detailBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (tapGuardActive) return;
          setCardFlipped(tile, false, { focus: false });
          openNonVideoFoundUpDetail(Number(tile.dataset.index || 0));
        });
      });

      // Pinch support via gesture engine (if available)
      if (window.gestureZone) {
        window.gestureZone(tile, {
          onPinchOut: function() {
            var index = Number(tile.dataset.index || 0);
            var activeItems = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
            var item = activeItems[index];
            var tileHasVideos = item && (item.videos?.length || item.video_data || (entityPortraitField && item.video_pages?.catalog && item.video_count) || (!usesMemberVideoPlayer() && item.video_count));
            if (!tileHasVideos && !fixedVideoField && !isPropertyListing(item)) {
              setCardFlipped(tile, false, { focus: false });
              openNonVideoFoundUpDetail(index);
              return;
            }
            if (tile.classList.contains('is-card-flipped')) return;
            if (fixedVideoField || expandedFoundUp !== null) {
              openFullscreenFromTile(index);
              return;
            }
            if (isPropertyListing(mallCatalog[index])) {
              togglePlay(index);
              return;
            }
            if (entityPortraitField) openEntityVideos(index);
            else expandFoundUp(index);
          },
          onPinchIn: function() {
            if (tile.classList.contains('is-card-flipped')) return;
            if (expandedFoundUp !== null) {
              collapseFoundUp();
            }
          }
        });
      }
    });

    // Corner expand buttons — open fullscreen, stop event from reaching tile tap
    var expandBtns = batch ? batch.flatMap(function(tile) {
      return Array.from(tile.querySelectorAll('.mall-tile-expand'));
    }) : tileField.querySelectorAll('.mall-tile-expand');
    expandBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        // Ignore if guard is active (just finished dragging)
        if (tapGuardActive) return;
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var index = Number(tile.dataset.index || 0);
        openFullscreenFromTile(index);
      });
    });

    // Audio buttons — toggle mute or start muted preview
    var audioBtns = batch ? [] : tileField.querySelectorAll('.mall-tile-audio');
    audioBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (tapGuardActive) return;
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var index = Number(tile.dataset.index || 0);
        if (playingIndex === index) {
          togglePreviewMute();
        } else {
          startInlinePreview(index, true);
        }
      });
    });

    // Enter FoundUp buttons — navigate to canonical /f/{foundup_id} route
    var enterBtns = batch ? [] : tileField.querySelectorAll('.mall-tile-enter');
    enterBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (tapGuardActive) return;
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var index = Number(tile.dataset.index || 0);

        // In expanded mode, route to PARENT FoundUp, not synthetic video ID
        var foundupId;
        if (expandedFoundUp !== null) {
          var parentItem = mallCatalog[expandedFoundUp];
          foundupId = parentItem ? (parentItem.foundup_id || parentItem.id) : null;
        } else {
          // In Mall mode, use stable foundup_id from data attribute
          foundupId = tile.dataset.foundupId;
        }
        if (entityPortraitField) foundupId = canonicalFoundUpId(mallCatalog[expandedFoundUp ?? index]);

        if (foundupId) {
          navigateToFoundUp(foundupId);
        }
      });
    });

    // Bind once: rerendering rows must not accumulate document listeners.
    if (escapeBound) return;
    escapeBound = true;
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && activeFlippedTile) {
        e.stopPropagation();
        setTileFlipped(activeFlippedTile, false);
      } else if (e.key === 'Escape' && expandedFoundUp !== null && !fixedVideoField) {
        e.stopPropagation();
        collapseFoundUp();
      } else if (e.key === 'Escape' && playingIndex !== null) {
        e.stopPropagation();
        stopInlinePreview();
      }
    });
  }

  function usesMemberVideoPlayer() {
    return !fixedVideoField && groupDefinitions === null &&
      typeof window.mallVideoPlayer?.openDesktopVideo === 'function';
  }

  /**
   * Activate a tile using the current field's playback or quick-view path.
   * @param {number} index - Tile index
   */
  function togglePlay(index) {
    if (fixedVideoField) {
      openScopedVideo(index, false, { tileActivation: true });
      return;
    }
    var targetTile = getTileElement(index);

    // Immediate visual feedback: tap pulse
    if (targetTile) {
      targetTile.classList.remove('tap-pulse');
      // Force reflow to restart animation
      void targetTile.offsetWidth;
      targetTile.classList.add('tap-pulse');
    }

    // Get item to check if it has videos (includes expanded video tiles with video_data)
    var items = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
    var item = items[index];
    if (isPropertyListing(item)) {
      stopInlinePreview();
      if (window.mallPlanes && typeof window.mallPlanes.openListingById === 'function') {
        var group = groupForIndex(index);
        window.mallPlanes.setCatalog(group ? group.indices.map(function(itemIndex) { return mallCatalog[itemIndex]; }) : mallCatalog);
        window.mallPlanes.openListingById(item.foundup_id, item.listing_id);
      }
      return;
    }
    var memberPlayer = usesMemberVideoPlayer();
    var hasVideos = item && (item.videos?.length || item.video_data || (entityPortraitField && item.video_pages?.catalog && item.video_count) || (!memberPlayer && item.video_count));

    // Non-video tiles: scoped member projection on portal, or flip card to reveal OSP & actions
    if (!hasVideos) {
      if (isEntityGrid() && item?.discovery_kind === 'candidate') {
        var candidateTile = getTileElement(index);
        if (candidateTile) setCardFlipped(candidateTile, true, { pinned: true });
        return;
      }
      var foundupId = item && (item.foundup_id || item.id);
      var memberProjection = foundupId && !fixedVideoField && window.mallVideoProjection?.memberPath?.(foundupId);
      if (memberProjection && !entityPortraitField) {
        if (desktopInlineTile) window.mallVideoPlayer.close();
        window.mallStateRestore?.save?.();
        if (typeof window.location?.assign === 'function') {
          window.location.assign(memberProjection);
        } else if (window.location) {
          window.location.href = memberProjection;
        }
        return;
      }
      var nonVideoTile = getTileElement(index);
      if (nonVideoTile && nonVideoTile.querySelector('.mall-card-back')) {
        setCardFlipped(nonVideoTile, !nonVideoTile.classList.contains('is-card-flipped'), { pinned: true });
        return;
      }
      openNonVideoFoundUpDetail(index);
      return;
    }

    if (entityPortraitField && expandedFoundUp === null && hasVideos) {
      openEntityVideos(index, { tileActivation: true });
      return;
    }

    if (memberPlayer) {
      openDesktopVideo(index, false, { tileActivation: true });
      return;
    }

    // Video tiles: inline preview behavior
    if (playingIndex === index) {
      if (previewPaused) resumeInlinePreview();
      else pauseInlinePreview();
      return;
    }

    // In Mall mode (not expanded): use lane autoplay through videos[] queue
    if (expandedFoundUp === null && item.videos && item.videos.length) {
      startLanePreview(index, 0, false);
    } else {
      // Expanded mode or single video: use existing preview
      startInlinePreview(index, false);
    }
  }

  function getScopedTile(index) {
    var rank = scopedRenderedIndices ? scopedRenderedIndices.indexOf(index) : index;
    if (rank < 0) return null;
    if (rank >= fixedRenderedCount) {
      renderTiles(Math.ceil((rank + 1) / FIXED_VIDEO_BATCH) * FIXED_VIDEO_BATCH);
    }
    return getTileElement(index);
  }

  function replaceScopedTile(slot, tile) {
    var indices = scopedRenderedIndices;
    var index = Number(tile.dataset.index);
    var rank = indices ? indices.indexOf(index) : index;
    var firstInRow = rank - rank % FIXED_VIDEO_COLUMNS;
    var firstTile = getTileElement(indices ? indices[firstInRow] : firstInRow);
    if (!slot.isConnected) {
      firstTile.before(slot);
    } else if (slot.nextElementSibling !== firstTile) {
      // Move the tiles around the slot so resizing leaves the provider iframe mounted.
      var tiles = Array.from(tileField.querySelectorAll('.mall-tile'));
      slot.before(...tiles.slice(0, firstInRow));
      slot.after(...tiles.slice(firstInRow));
    }
    tile.setAttribute('data-video-replaced', '');
  }

  function setScopedTheater(enabled) {
    if (!fixedVideoField) return;
    scopedTheaterRequested = enabled;
    var player = window.mallVideoPlayer;
    if (player?.isMallHidden?.()) return;
    var lane = mallCatalog[0];
    // Keep the immersive WikiTube dialog's inert siblings mounted until it closes.
    if (document.getElementById('videoPlayerFullscreen')?.getAttribute('aria-modal') === 'true') return;
    if (!enabled && player.isTheater() && scopedPhoneIndices) {
      var activeIndex = player.getCurrentIndex();
      // Keep an out-of-filter desktop selection visible while it is playing.
      scopedPhonePlaybackIndices = scopedPhoneIndices.includes(activeIndex) ? null : [activeIndex, ...scopedPhoneIndices];
    }
    syncScopedTiles();
    if (enabled) {
      if (player.isOpen()) {
        tileField.querySelector('[data-video-replaced]')?.removeAttribute('data-video-replaced');
        player.setTheater?.(true);
      } else {
        if (scopedPlaybackDismissed) return;
        var restoredIndex = lane.videos.findIndex(function(video) {
          return video.video_id === scopedTheaterState?.videoId;
        });
        openScopedVideo(Math.max(0, restoredIndex), false);
      }
      return;
    }
    if (!player.isTheater?.()) return;

    rememberTheater();
    var index = player.getCurrentIndex();
    var tile = getScopedTile(index);
    player.setTheater(false, tile);
    if (tile) {
      tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
      tile.setAttribute('aria-current', 'true');
      tile.scrollIntoView({ block: 'center', behavior: 'instant' });
      scopedPlaybackPosition = captureFixedPosition(tile);
    }
    pushScopedPlayerHistory(lane.foundup_id);
  }

  function pushScopedPlayerHistory(foundupId) {
    if (window.history.state?.[SCOPED_PLAYER_HISTORY] !== foundupId) {
      window.history.pushState({ ...window.history.state, [SCOPED_PLAYER_HISTORY]: foundupId }, '');
    }
  }

  function syncScopedActiveTile(activeIndex) {
    tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
    var activeTile = getScopedTile(activeIndex);
    if (activeTile) activeTile.setAttribute('aria-current', 'true');
    return activeTile;
  }

  function openScopedVideo(index, immersive, options) {
    var player = window.mallVideoPlayer;
    var lane = mallCatalog[0];
    if (!player || !lane?.videos?.[index]) return;
    syncScopedTiles();
    var tile = getScopedTile(index);
    if (!tile) return;
    var tileActivation = options?.tileActivation === true;
    if (tileActivation) scopedPlaybackDismissed = false;
    var theater = !tileActivation && scopedTheaterRequested && !immersive;
    var autoplay = theater ? window.mallStateRestore?.getVideoOptions?.().autoplayNext !== false : canAutoplayFromTile(tile);

    var samePlayer = player.isOpen() && player.getFoundUpId() === lane.foundup_id;
    if (samePlayer && player.isMallHidden?.() && player.getCurrentIndex() === index) {
      return player.resumeFromMall({ tileActivation: tileActivation, autoplay: autoplay });
    }
    // A new deliberate selection owns the visible grid caller. Resuming the
    // old retained theater first can hide/reflow that grid before capture.
    var activationCaller = tileActivation && player.isMallHidden?.()
      ? capturePlayerCaller(lane, tile) : null;
    if (player.isMallHidden?.()) {
      if (!samePlayer || player.resumeFromMall({ fromHistory: true, autoplay: false }) === false) {
        player.close({ restore: false });
        samePlayer = false;
      }
    }
    if (samePlayer && !tileActivation) {
      if (player.getCurrentIndex() === index) {
        if (immersive) {
        if (player.isTheater?.()) player.setTheater(false, tile);
        player.openWikiTube ? player.openWikiTube() : player.expandInline();
      }
        else if (player.isTucked?.()) player.untuck();
        else if (autoplay && player.getPlaybackSnapshot?.()?.state !== 'playing') {
          player.selectVideo?.(index, { autoplay: true, returnTile: tile });
        }
        return;
      }
      syncScopedActiveTile(index);
      if (!theater) pushScopedPlayerHistory(lane.foundup_id);
      if (immersive && !player.isWikiTube?.()) {
        player.selectVideo?.(index, { autoplay: autoplay, returnTile: tile });
        player.openWikiTube?.();
        return;
      }
      if (typeof player.selectVideo === 'function') {
        player.selectVideo(index, { autoplay: autoplay, returnTile: tile });
        return;
      }
    }

    if (!samePlayer || !tileActivation) player.close({ restore: false });
    syncScopedTiles();
    tile = getScopedTile(index);
    if (!tile) return;
    scopedPlaybackPosition = captureFixedPosition(theater ? null : tile);
    if (!theater) pushScopedPlayerHistory(lane.foundup_id);
    syncScopedActiveTile(index);

    player.open(lane.foundup_id, lane.videos, index, {
      ...preparePlayerReturn(lane, tile, activationCaller),
      tileActivation: tileActivation,
      floating: !immersive && !theater,
      scoped: true,
      returnTile: tile,
      theater: theater,
      query: scopedTheaterState?.query,
      queueQuery: scopedPhoneQuery,
      matchesQuery: matchesScopedVideo,
      autoplay: autoplay,
      onSelectChange: function(nextIdx) {
        if (!fixedVideoField) return;
        var nextTile = syncScopedActiveTile(nextIdx);
        if (nextTile) scopedPlaybackPosition = captureFixedPosition(theater ? null : nextTile);
      },
      onClose: function(restore, lifecycle) {
        if ((restore || lifecycle?.dismissPlayback) && !lifecycle?.preserveQueueOwner) scopedPlaybackDismissed = true;
        tileField.querySelector('[data-video-replaced]')?.removeAttribute('data-video-replaced');
        tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
        var hadFilterInjection = !!scopedPhonePlaybackIndices;
        var position = scopedPlaybackPosition;
        scopedPlaybackPosition = null;
        scopedPhonePlaybackIndices = null;
        if (restore) {
          syncScopedTiles();
          if (hadFilterInjection && position) restoreVideoGridState(position);
          if (window.history.state?.[SCOPED_PLAYER_HISTORY] === lane.foundup_id) window.history.back();
        }
      }
    });
  }

  function bindScopedPlayerHistory(foundupId) {
    // A reload never reopens playback, even if it occurred on the player entry.
    if (window.history.state?.[SCOPED_PLAYER_HISTORY] === foundupId) {
      var state = { ...window.history.state };
      delete state[SCOPED_PLAYER_HISTORY];
      window.history.replaceState(state, '');
    }
    window.addEventListener('popstate', function() {
      if (window.history.state?.[SCOPED_PLAYER_HISTORY] === foundupId &&
          window.mallVideoPlayer?.getFoundUpId() === foundupId && window.mallVideoPlayer.isMallHidden?.()) {
        window.mallVideoPlayer.resumeFromMall({ fromHistory: true, autoplay: false });
      } else if (window.history.state?.[SCOPED_PLAYER_HISTORY] !== foundupId &&
          window.mallVideoPlayer?.getFoundUpId() === foundupId &&
          !window.mallVideoPlayer.isTheater?.() && !window.mallVideoPlayer.isMallHidden?.()) {
        window.mallVideoPlayer.returnToMall({ fromHistory: true });
      }
    });
  }

  function openFullscreenFromTile(index) {
    stopInlinePreview();
    if (fixedVideoField) {
      openScopedVideo(index, true);
      return;
    }
    if (expandedFoundUp === null && isPropertyListing(mallCatalog[index])) {
      togglePlay(index);
      return;
    }
    if (entityPortraitField && expandedFoundUp === null && mallCatalog[index]?.video_count > 0) {
      openEntityVideos(index, { immersive: true });
      return;
    }
    if (!window.mallVideoPlayer) return;
    if (usesMemberVideoPlayer()) {
      openDesktopVideo(index, true);
      return;
    }

    if (expandedFoundUp !== null) {
      // Expanded mode: tiles are individual videos from one FoundUp
      var parentItem = mallCatalog[expandedFoundUp];
      if (!parentItem || !parentItem.videos || !parentItem.videos.length) return;
      var foundupId = parentItem.foundup_id || parentItem.id || '';
      var activeQuery = activeScopeQuery();
      window.mallVideoPlayer.open(foundupId, parentItem.videos, index, activeQuery ? {
        query: activeQuery,
        queueQuery: activeQuery,
        matchesQuery: matchesScopedVideo
      } : undefined);
    } else {
      // Mall mode: tiles are FoundUps — open queue at first video (or enter member projection)
      var item = mallCatalog[index];
      if (!item) return;
      var foundupId = item.foundup_id || item.id || '';
      var queue = item.videos || [];
      if (!queue.length) {
        if (foundupId && window.mallVideoProjection?.memberPath?.(foundupId)) {
          togglePlay(index);
        }
        return;
      }
      var activeMallQuery = activeScopeQuery();
      var startIdx = 0;
      if (activeMallQuery) {
        var matchedIdx = queue.findIndex(function(video) { return matchesScopedVideo(video, activeMallQuery); });
        if (matchedIdx >= 0) startIdx = matchedIdx;
      }
      window.mallVideoPlayer.open(foundupId, queue, startIdx, activeMallQuery ? {
        query: activeMallQuery,
        queueQuery: activeMallQuery,
        matchesQuery: matchesScopedVideo
      } : undefined);
    }
  }

  function activeScopeQuery() {
    if (!currentFieldScope || typeof currentFieldScope.query !== 'string') return '';
    return (currentFieldScope.type === 'query' || currentFieldScope.type === 'tag')
      ? currentFieldScope.query.trim().slice(0, 300)
      : '';
  }

  function openDesktopVideo(index, immersive, opts) {
    var player = window.mallVideoPlayer;
    var tile = getTileElement(index);
    var lane = mallCatalog[expandedFoundUp ?? index];
    var activeQueueQuery = typeof opts?.queueQuery === 'string'
      ? opts.queueQuery.trim().slice(0, 300)
      : activeScopeQuery();
    var videoIndex = Number.isInteger(opts?.videoIndex) && opts.videoIndex >= 0
      ? opts.videoIndex
      : (expandedFoundUp === null ? 0 : index);
    if (expandedFoundUp === null && opts?.videoIndex === undefined && activeQueueQuery && Array.isArray(lane?.videos)) {
      var firstMatch = lane.videos.findIndex(function(video) {
        return matchesScopedVideo(video, activeQueueQuery);
      });
      if (firstMatch >= 0) videoIndex = firstMatch;
    }
    if (!tile || !lane?.videos?.[videoIndex]) return false;
    var targetFoundUpId = lane.foundup_id || lane.id;
    var autoplay = opts?.autoplay !== undefined ? opts.autoplay : canAutoplayFromTile(tile);
    var activationCaller = opts?.caller;
    if (!activationCaller && opts?.tileActivation && player.isMallHidden?.() &&
        (player.getFoundUpId?.() !== targetFoundUpId || player.getCurrentIndex() !== videoIndex)) {
      activationCaller = capturePlayerCaller(lane, tile);
    }
    if (player.isMallHidden?.() && player.getFoundUpId?.() === targetFoundUpId) {
      if (player.getCurrentIndex() === videoIndex) {
        return player.resumeFromMall({ tileActivation: opts?.tileActivation === true, autoplay: autoplay });
      }
      if (player.resumeFromMall({ fromHistory: true, autoplay: false }) === false) return false;
    }
    var selectedScope = isSelectedEntityScope();
    var scopeEpoch = selectionEpoch;
    var wantTheater = !opts?.tileActivation && !immersive && selectedScope && selectedDesktop();

    if (!opts?.tileActivation && desktopInlineTile === tile && opts?.videoIndex === undefined && player.isOpen() && player.getFoundUpId?.() === targetFoundUpId) {
      if (immersive) {
        if (player.isTheater?.()) player.setTheater(false, tile);
        player.openWikiTube ? player.openWikiTube() : player.expandInline();
      }
      else if (player.isTucked?.()) player.untuck();
      else if (autoplay && player.getPlaybackSnapshot?.()?.state !== 'playing') {
        player.selectVideo?.(player.getCurrentIndex(), { autoplay: true, returnTile: tile });
      }
      return true;
    }

    stopInlinePreview();
    if (desktopInlineTile && desktopInlineTile !== tile) {
      desktopInlineTile.removeAttribute('aria-current');
      desktopInlineTile = null;
    }
    var returnOptions = preparePlayerReturn(lane, tile, activationCaller);
    tile.setAttribute('aria-current', 'true');
    desktopInlineTile = tile;
    tileFieldWrapper.classList.add('member-inline-open');

    player.openDesktopVideo(targetFoundUpId, lane.videos, videoIndex, {
      ...returnOptions,
      tileActivation: opts?.tileActivation === true,
      floating: !immersive && !wantTheater,
      theater: wantTheater,
      onQueueEnd: selectedScope ? async function() {
        var batch = await loadSelectedPage();
        return selectionEpoch === scopeEpoch && batch.length > 0;
      } : undefined,
      onPinchReturn: selectedScope ? returnEntityToMall : undefined,
      returnFocusTo: tile,
      matchesQuery: matchesScopedVideo,
      query: activeQueueQuery,
      queueQuery: activeQueueQuery,
      autoplay: autoplay,
      muted: opts?.muted === true,
      onSelectChange: function(nextIdx) {
        if (selectedScope) selectedVideoIndex = nextIdx;
        if (expandedFoundUp !== null) {
          tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
          var nextTile = getTileElement(nextIdx);
          if (nextTile) {
            nextTile.setAttribute('aria-current', 'true');
            desktopInlineTile = nextTile;
          }
        }
      },
      onClose: function(restore, lifecycle) {
        if (!lifecycle?.preserveQueueOwner) {
          tileField.querySelector('.mall-tile[aria-current]')?.removeAttribute('aria-current');
          tileFieldWrapper.classList.remove('member-inline-open');
          desktopInlineTile = null;
        }
        // Final player Close disposes playback, not the selected field's pager.
        // The field remains browsable and owns cancellation on scope changes.
        // Its bounded page may finish, but the player's generation/intent gate
        // prevents that completion from recreating a closed provider/session.
        if (!lifecycle?.preserveQueueOwner) retainedLane = null;
        if (!lifecycle?.preserveQueueOwner) playerCaller = null;
      }
    });
    return true;
  }

  function getActiveVideo() {
    if (fixedVideoField || groupDefinitions !== null) return null;
    var player = window.mallVideoPlayer;
    if (player && typeof player.isOpen === 'function' && player.isOpen() && !player.isMallHidden?.()) {
      var foundupId = player.getFoundUpId?.();
      var videoId = player.getCurrentVideoId?.();
      if (!videoId && foundupId) {
        var lane = mallCatalog.find(function(item) { return (item.foundup_id || item.id) === foundupId; }) ||
          fullCatalog.find(function(item) { return (item.foundup_id || item.id) === foundupId; });
        var idx = player.getCurrentIndex?.() ?? -1;
        var v = lane?.videos?.[idx];
        videoId = v ? (v.video_id || v.videoId || v.id || null) : null;
      }
      if (foundupId && videoId) {
        return {
          foundupId: foundupId,
          videoId: videoId,
          queueQuery: (player.getQueueQuery?.() || activeScopeQuery()).slice(0, 300)
        };
      }
    }
    if (playingIndex !== null) {
      var activeLane = expandedFoundUp !== null ? mallCatalog[expandedFoundUp] : mallCatalog[playingIndex];
      var activeFid = activeLane && (activeLane.foundup_id || activeLane.id);
      var vIdx = expandedFoundUp !== null ? playingIndex : laneVideoIndex;
      var pv = activeLane?.videos?.[vIdx];
      var pvId = pv ? (pv.video_id || pv.videoId || pv.id || null) : null;
      if (activeFid && pvId) {
        return {
          foundupId: activeFid,
          videoId: pvId,
          queueQuery: activeScopeQuery()
        };
      }
    }
    return null;
  }

  function restoreActiveVideo(activeVideo) {
    if (fixedVideoField || groupDefinitions !== null || !activeVideo || typeof activeVideo !== 'object') return false;
    var foundupId = activeVideo.foundupId;
    var videoId = activeVideo.videoId;
    var queueQuery = typeof activeVideo.queueQuery === 'string' ? activeVideo.queueQuery.slice(0, 300) : '';
    if (!foundupId || !videoId) return false;
    if (entityPortraitField && catalogPager) return openEntityById(foundupId, { autoplay: false, videoId: videoId, queueQuery: queueQuery });
    var laneIndex = mallCatalog.findIndex(function(item) {
      return (item.foundup_id || item.id) === foundupId;
    });
    if (laneIndex < 0) return false;
    var lane = mallCatalog[laneIndex];
    if (!Array.isArray(lane?.videos) || !lane.videos.length) return false;
    var videoIndex = lane.videos.findIndex(function(video) {
      return (video.video_id || video.videoId || video.id) === videoId;
    });
    if (videoIndex < 0) return false;
    if (usesMemberVideoPlayer()) {
      return openDesktopVideo(laneIndex, false, {
        videoIndex: videoIndex,
        queueQuery: queueQuery,
        autoplay: false
      });
    }
    if (window.mallVideoPlayer && typeof window.mallVideoPlayer.open === 'function') {
      window.mallVideoPlayer.open(foundupId, lane.videos, videoIndex, {
        query: queueQuery,
        queueQuery: queueQuery,
        matchesQuery: matchesScopedVideo,
        autoplay: false
      });
      return true;
    }
    return false;
  }

  function canAutoplayFromTile(tile) {
    if (tile?.classList.contains('mall-member-card')) return true;
    // YouTube requires at least 120 × 70 CSS pixels for an autoplay trigger.
    var rect = tile?.getBoundingClientRect();
    return !!rect && rect.width >= 120 && rect.height >= 70;
  }

  function sizeMemberVideoSlot(slot) {
    if (!slot || !slot.style) return;
    var columns = window.getComputedStyle(tileField).gridTemplateColumns.split(' ');
    var width = parseFloat(columns[0]) || 1;
    if (columns.length > 1) {
      slot.style.setProperty('--member-inline-columns', Math.min(columns.length, Math.ceil(360 / width)));
    }
  }

  /**
   * Get tile element by index
   * @param {number} index - Tile index
   * @returns {HTMLElement|null}
   */
  function getTileElement(index) {
    if (!tileField) return null;
    var numericIndex = Number(index);
    if (!Number.isInteger(numericIndex) || numericIndex < 0) return null;
    if (isEntityGrid() && numericIndex < mallCatalog.length && numericIndex >= entityRenderedCount) {
      renderTiles(Math.ceil((numericIndex + 1) / FIXED_VIDEO_BATCH) * FIXED_VIDEO_BATCH);
    }
    if (!isEntityGrid() && (isSelectedEntityScope() || usesProgressivePatchGrid()) && numericIndex < getExpandedVideos().length && numericIndex >= fixedRenderedCount) {
      renderTiles(Math.ceil((numericIndex + 1) / activePatchBatchSize()) * activePatchBatchSize());
    }
    return tileField.querySelector('.mall-tile[data-index="' + numericIndex + '"]');
  }

  /** Materialize only the batches needed to restore a public-grid scroll position. */
  function restoreBrowsePosition(top, left) {
    if (!isEntityGrid() || !tileFieldWrapper || !Number.isFinite(top) || top < 0) return false;
    while (entityRenderedCount < mallCatalog.length &&
        tileFieldWrapper.scrollHeight - tileFieldWrapper.clientHeight < top) {
      renderTiles(entityRenderedCount + FIXED_VIDEO_BATCH);
    }
    // Restoration must settle before a FLIP transition measures its target.
    var scrollLeft = Number.isFinite(left) && left >= 0 ? left : tileFieldWrapper.scrollLeft;
    tileFieldWrapper.scrollTo({ top: top, left: scrollLeft, behavior: 'instant' });
    return true;
  }

  /**
   * Check if reduced-motion is preferred
   * @returns {boolean}
   */
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /**
   * Create FLIP transition layer for expand/collapse animation
   * @param {DOMRect} sourceRect - Starting bounding rect
   * @param {string} backgroundImage - CSS background-image value
   * @param {string} backgroundColor - Fallback background color
   * @returns {HTMLElement} Transition layer element
   */
  function createFlipLayer(sourceRect, backgroundImage, backgroundColor) {
    var layer = document.createElement('div');
    layer.className = 'mall-flip-layer';
    layer.style.left = sourceRect.left + 'px';
    layer.style.top = sourceRect.top + 'px';
    layer.style.width = sourceRect.width + 'px';
    layer.style.height = sourceRect.height + 'px';
    if (backgroundImage) {
      layer.style.backgroundImage = backgroundImage;
    }
    if (backgroundColor) {
      layer.style.backgroundColor = backgroundColor;
    }
    document.body.appendChild(layer);
    return layer;
  }

  /**
   * Clean up FLIP transition layer
   * @param {HTMLElement} layer - Transition layer to remove
   */
  function cleanupFlipLayer(layer) {
    if (layer && layer.parentNode) {
      layer.parentNode.removeChild(layer);
    }
  }

  /**
   * Expand a FoundUp into its video field
   * @param {number} index - FoundUp index in catalog
   */
  function expandFoundUp(index) {
    if (fixedVideoField || expandedFoundUp === index) return;
    if (isPropertyListing(mallCatalog[index])) {
      togglePlay(index);
      return;
    }
    stopInlinePreview();

    var item = mallCatalog[index];
    if (!item || !item.videos || !item.videos.length) {
      console.warn('[mall-tile-field] Cannot expand: no videos for FoundUp', index);
      return;
    }

    var sourceTile = getTileElement(index);
    var sourceRect = sourceTile ? sourceTile.getBoundingClientRect() : null;
    var reducedMotion = prefersReducedMotion();

    if (expandedFoundUp === null) browseScrollTop = tileFieldWrapper.scrollTop;

    // Store source index and visual for collapse animation continuity
    expandSourceIndex = index;
    var bgImage = sourceTile ? sourceTile.style.backgroundImage || '' : '';
    var bgColor = sourceTile ? window.getComputedStyle(sourceTile).backgroundColor : '';
    expandSourceVisual = { bgImage: bgImage, bgColor: bgColor };

    // FLIP animation (skip if reduced motion)
    if (sourceRect && !reducedMotion) {
      var flipLayer = createFlipLayer(sourceRect, bgImage, bgColor);

      // Target: full viewport (the expanded field area)
      var targetRect = tileField.getBoundingClientRect();

      // Force reflow to establish initial geometry
      void flipLayer.offsetWidth;

      // Add transition class BEFORE setting target (enables CSS transition)
      flipLayer.classList.add('flip-animating');

      // Force another reflow so browser registers the transition
      void flipLayer.offsetWidth;

      // Animate to target geometry
      flipLayer.style.left = targetRect.left + 'px';
      flipLayer.style.top = targetRect.top + 'px';
      flipLayer.style.width = targetRect.width + 'px';
      flipLayer.style.height = targetRect.height + 'px';
      flipLayer.style.borderRadius = '0';

      // Render actual content during animation
      tileField.classList.add('transitioning');
      expandedFoundUp = index;
      playingIndex = null;
      renderTiles();
      bindInteractions();

      // Cleanup after animation
      setTimeout(function() {
        cleanupFlipLayer(flipLayer);
        tileField.classList.remove('transitioning');
        if (collapseHint && expandedFoundUp === index) {
          collapseHint.classList.add('visible');
        }
      }, 300);
    } else {
      // Reduced motion or no source: instant transition
      tileField.classList.add('transitioning');

      {
        expandedFoundUp = index;
        playingIndex = null;
        renderTiles();
        bindInteractions();
        tileField.classList.remove('transitioning');
        if (collapseHint && expandedFoundUp === index) {
          collapseHint.classList.add('visible');
        }
      }
    }
  }

  /**
   * Collapse expanded video field back to Mall
   */
  function collapseFoundUp(options) {
    if (expandedFoundUp === null || fixedVideoField) return;
    if (entityPortraitField && !options?.retainPlayback) cancelEntitySelection();
    stopInlinePreview();

    // Hide collapse hint first
    if (collapseHint) {
      collapseHint.classList.remove('visible');
    }

    var sourceIndex = expandSourceIndex;
    if (entityPortraitField && catalogRefreshPending) {
      var sourceId = mallCatalog[sourceIndex]?.foundup_id;
      mallCatalog = filterByScope(currentFieldScope);
      originalOrder = mallCatalog.slice();
      mallCatalog = sortByProjection(currentProjection);
      sourceIndex = mallCatalog.findIndex(function(item) { return item.foundup_id === sourceId; });
      expandSourceIndex = sourceIndex;
      catalogRefreshPending = false;
    }
    var expandedRect = tileField.getBoundingClientRect();
    var reducedMotion = prefersReducedMotion();

    if (options?.retainPlayback) {
      expandedFoundUp = null;
      playingIndex = null;
      renderTiles();
      bindInteractions();
      if (playerCaller) restorePlayerCaller(playerCaller);
      expandSourceIndex = null;
      expandSourceVisual = null;
      return;
    }

    // FLIP animation (skip if reduced motion)
    if (sourceIndex !== null && expandSourceVisual && !reducedMotion) {
      // Use stored source visual for continuity (not first tile in expanded view)
      var bgImage = expandSourceVisual.bgImage || '';
      var bgColor = expandSourceVisual.bgColor || '';
      var flipLayer = createFlipLayer(expandedRect, bgImage, bgColor);
      flipLayer.style.borderRadius = '0';

      // Render mall tiles (to get target rect)
      tileField.classList.add('transitioning');
      expandedFoundUp = null;
      playingIndex = null;
      renderTiles();
      bindInteractions();
      if (isEntityGrid() && sourceIndex !== null) getTileElement(sourceIndex);
      if (!restoreBrowsePosition(browseScrollTop, 0)) tileFieldWrapper.scrollTop = browseScrollTop;

      // Find target tile position
      var targetTile = getTileElement(sourceIndex);
      var targetRect = targetTile ? targetTile.getBoundingClientRect() : null;

      if (targetRect) {
        // Force reflow to establish initial geometry
        void flipLayer.offsetWidth;

        // Add transition class BEFORE setting target (enables CSS transition)
        flipLayer.classList.add('flip-collapsing');

        // Force another reflow so browser registers the transition
        void flipLayer.offsetWidth;

        // Animate to target tile position
        flipLayer.style.left = targetRect.left + 'px';
        flipLayer.style.top = targetRect.top + 'px';
        flipLayer.style.width = targetRect.width + 'px';
        flipLayer.style.height = targetRect.height + 'px';
        flipLayer.style.borderRadius = '';  // Return to tile radius

        // Cleanup after animation
        setTimeout(function() {
          cleanupFlipLayer(flipLayer);
          tileField.classList.remove('transitioning');
          expandSourceIndex = null;
          expandSourceVisual = null;
        }, 270);
      } else {
        // No target found, instant cleanup
        cleanupFlipLayer(flipLayer);
        tileField.classList.remove('transitioning');
        expandSourceIndex = null;
        expandSourceVisual = null;
      }
    } else {
      // Reduced motion: instant transition
      tileField.classList.add('transitioning');

      {
        expandedFoundUp = null;
        playingIndex = null;
        renderTiles();
        bindInteractions();
        if (isEntityGrid() && sourceIndex !== null) getTileElement(sourceIndex);
        if (!restoreBrowsePosition(browseScrollTop, 0)) tileFieldWrapper.scrollTop = browseScrollTop;
        tileField.classList.remove('transitioning');
        expandSourceIndex = null;
        expandSourceVisual = null;
      }
    }
  }

  // Shared browsing layout. Catalog indexes remain stable inside grouped DOM rows.
  function captureRowOffsets() {
    if (tileField) tileField.querySelectorAll('[data-row-key]').forEach(function(row) {
      rowOffsets[row.dataset.rowKey] = row.scrollLeft;
    });
    return Object.assign({}, rowOffsets);
  }

  function restoreRowOffsets(offsets) {
    if (!offsets || typeof offsets !== 'object') return;
    Object.keys(offsets).forEach(function(key) {
      if (Number.isFinite(offsets[key]) && offsets[key] >= 0) rowOffsets[key] = offsets[key];
    });
    if (tileField) tileField.querySelectorAll('[data-row-key]').forEach(function(row) {
      row.scrollLeft = rowOffsets[row.dataset.rowKey] || 0;
    });
  }

  function setLayoutMode(mode) {
    if (mode !== 'rows' && mode !== 'grid') return false;
    if (entityPortraitField && mode !== 'grid') return false;
    // A product adapter owns its geographic projection. Category/grid controls
    // cannot silently replace that declaration or report an unapplied change.
    if (groupDefinitions !== null) return false;
    stopInlinePreview();
    layoutMode = mode;
    if (tileField) { renderTiles(); bindInteractions(); }
    return true;
  }

  // Projection changes invalidate index-based media state.
  function resetMediaScope() {
    if (entityPortraitField && !window.mallVideoPlayer?.isMallHidden?.()) cancelEntitySelection();
    stopInlinePreview();
    expandedFoundUp = null;
    expandSourceIndex = null;
    if (collapseHint) collapseHint.classList.remove('visible');
  }

  // Bounded local catalog search, not semantic ranking or a conversation runtime.
  function searchCatalog(query) {
    // Geographic filters belong to the registered domain adapter, including
    // clearing a query. Preserve its form, URL and catalog as one state owner.
    if (groupDefinitions !== null) return false;
    if (typeof query !== 'string') return;
    query = query.trim().slice(0, 300);
    if (!query) { clearFieldScope(); return; }
    var scope = { type: 'query', query: query };
    setFieldScope(scope);
    return (async function() {
      // An explicit search may inspect small metadata pages, never other queues.
      while (catalogPager?.hasMore && currentFieldScope === scope && !isSelectedEntityScope()) {
        if (!(await loadCatalogPage()).length) break;
      }
      window.mallStateRestore?.save?.();
    })();
  }

  function matchesCatalogQuery(item, query) {
    var normalized = query.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, ' ').trim().replace(/\s+/g, ' ');
    // Only remove a recognized leading request. Keep negation, budgets and
    // other unsupported constraints as literal terms; this is not intent AI.
    normalized = normalized.replace(/^(?:hey\s+)?(?:red\s+dog\s+)?(?:please\s+)?(?:i\s+(?:m|am)\s+looking\s+for|show\s+me|find|browse)\s+/, '');
    var words = normalized.split(/\s+/).filter(function(word) {
      return word && !['hey', 'please', 'show', 'me', 'find', 'browse', 'on', 'in', 'about', 'the', 'some'].includes(word);
    });
    var wantsVideos = words.some(function(word) { return word === 'videos' || word === 'video'; });
    if (wantsVideos && !(item.videos?.length || item.video_count)) return false;
    words = words.filter(function(word) { return word !== 'videos' && word !== 'video'; });
    var clothingTerms = 'clothes clothing apparel fashion';
    var aliases = { houses: 'house housing homes property real-estate', house: 'house housing homes property real-estate',
      cars: 'car cars automotive vehicles', clothes: clothingTerms, clothing: clothingTerms, apparel: clothingTerms };
    var metadata = [item.name, item.title, item.description, item.tagline, item.creator, item.creator_display,
      item.entity, item.category, item.topic_family, item.geo, item.tags].concat((item.videos || []).map(function(video) {
        return [video.title, video.description, video.tags, video.geo].join(' ');
      })).join(' ').toLowerCase();
    return words.every(function(word) {
      return (aliases[word] || word).split(' ').some(function(term) { return metadata.indexOf(term) !== -1; });
    });
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
      tileFieldWrapper.classList.toggle('motion-snap', mode === 'snap');
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

  // All valid density presets
  var ALL_DENSITIES = ['3x4', '3x5', '4x6', '5x8', '6x3', '8x2', '8x5', '10x6', '12x3', '12x8', '15x4'];

  // Density tiers by device class
  var DENSITY_TIERS = {
    phone: ['3x4', '3x5'],
    tablet: ['3x4', '3x5', '4x6', '5x8'],
    desktop: ALL_DENSITIES
  };

  /**
   * Get device class based on pointer type and viewport
   * @returns {{ deviceClass: string, shortSide: number, isCoarse: boolean, isLandscape: boolean }}
   */
  function getDeviceInfo() {
    var width = window.innerWidth;
    var height = window.innerHeight;
    var isCoarsePointer = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    var isLandscape = width > height;
    var shortSide = Math.min(width, height);

    var deviceClass;
    if (!isCoarsePointer) {
      deviceClass = 'desktop';
    } else if (shortSide < 600) {
      deviceClass = 'phone';
    } else {
      deviceClass = 'tablet';
    }

    return {
      deviceClass: deviceClass,
      shortSide: shortSide,
      isCoarse: isCoarsePointer,
      isLandscape: isLandscape,
      width: width,
      height: height
    };
  }

  /**
   * Get allowed density presets for current device
   * @returns {{ allowed: string[], deviceClass: string, reason: string }}
   */
  function getDevicePolicy() {
    var info = getDeviceInfo();
    var allowed = DENSITY_TIERS[info.deviceClass] || DENSITY_TIERS.phone;

    return {
      allowed: allowed,
      deviceClass: info.deviceClass,
      reason: info.deviceClass === 'phone'
        ? 'Phone (coarse pointer, short side < 600px)'
        : info.deviceClass === 'tablet'
          ? 'Tablet (coarse pointer, short side >= 600px)'
          : 'Desktop (fine pointer)'
    };
  }

  /**
   * Safe public API for density changes from AI/RedDog
   * Validates against device policy before applying
   * @param {string} preset - Requested density preset
   * @param {{ source?: string }} [options] - Options with source identifier
   * @returns {{ applied: boolean, preset: string, reason?: string }}
   */
  function requestDensity(preset, options) {
    options = options || {};
    var source = options.source || 'unknown';
    var policy = getDevicePolicy();

    if (!ALL_DENSITIES.includes(preset)) {
      return {
        applied: false,
        preset: preset,
        reason: 'Invalid density preset: ' + preset
      };
    }

    if (!policy.allowed.includes(preset)) {
      return {
        applied: false,
        preset: preset,
        reason: 'Density ' + preset + ' not allowed for ' + policy.deviceClass + '. Allowed: ' + policy.allowed.join(', ')
      };
    }

    setDensity(preset, true);
    return {
      applied: true,
      preset: preset,
      source: source,
      deviceClass: policy.deviceClass
    };
  }

  /**
   * Set field density preset (internal/low-level)
   * External callers should use requestDensity() for policy enforcement
   * @param {string} density - Density preset
   * @param {boolean} [isManual=true] - Whether this is a manual user override
   * @private
   */
  function setDensity(density, isManual) {
    if (!ALL_DENSITIES.includes(density)) {
      density = '3x5';
    }
    currentDensity = density;

    // Track manual override (defaults to true for API calls)
    if (isManual !== false) {
      densityManuallySet = true;
      if (groupDefinitions === null && layoutMode !== 'grid') setLayoutMode('grid');
    }

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

  /**
   * Detect viewport class and return optimal density
   * Uses device policy to ensure returned density is always allowed
   * @returns {string} Optimal density preset
   */
  function detectOptimalDensity() {
    var info = getDeviceInfo();
    var policy = getDevicePolicy();

    // Desktop: fine pointer + wide viewport + landscape
    if (info.deviceClass === 'desktop' && info.isLandscape) {
      if (info.width >= 2560) return '12x3';
      if (info.width >= 1920) return '10x6';
      if (info.width >= 1440) return '8x5';
      if (info.width >= 1024) return '6x3';
    }

    // Tablet landscape: coarse pointer but wide enough
    if (info.deviceClass === 'tablet' && info.isLandscape) {
      return '4x6';
    }

    if (info.deviceClass === 'tablet') return '4x6';
    // Phone: safe mobile default
    return '3x5';
  }

  /**
   * Auto-select density based on viewport (only if not manually set)
   */
  function autoSelectDensity() {
    if (densityManuallySet && getDevicePolicy().allowed.includes(currentDensity)) return;
    densityManuallySet = false;
    var optimal = detectOptimalDensity();
    setDensity(optimal, false); // false = not manual
  }

  /**
   * Handle viewport resize - re-evaluate density if not manually set
   */
  function handleResize() {
    if (fixedVideoField) {
      if (fixedBrowsePosition && !scopedPlaybackPosition) restoreVideoGridState(fixedBrowsePosition);
      return;
    }
    autoSelectDensity();
    if (isSelectedEntityScope() && window.mallVideoPlayer?.isOpen?.() && !window.mallVideoPlayer.isMallHidden?.() && !window.mallVideoPlayer.isWikiTube?.()) {
      window.mallVideoPlayer.setTheater?.(selectedDesktop());
    }
    if (desktopInlineTile || window.mallVideoPlayer?.isOpen?.()) {
      window.mallVideoPlayer?.syncFloatingGeometry?.();
    }
  }

  /**
   * Reset manual density override - allows auto-selection to resume
   */
  function resetDensityOverride() {
    densityManuallySet = false;
    autoSelectDensity();
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
   * Navigate to canonical FoundUp landing page
   * Uses WSP 104 routing: /f/{foundup_id}
   * @param {string} foundupId - Stable FoundUp identity
   */
  function navigateToFoundUp(foundupId) {
    if (fixedVideoField) return;
    if (!foundupId) return;
    // Stop any active preview before navigation
    stopInlinePreview();
    if (window.mallVideoProjection?.isOpenMallHost?.(window.location)) {
      window.mallStateRestore?.save?.();
      var portalUrl = window.mallVideoProjection.memberPortalUrl(foundupId);
      if (typeof window.location?.assign === 'function') window.location.assign(portalUrl);
      else window.location.href = portalUrl;
      return;
    }
    // Navigate to canonical route (WSP 104)
    window.location.href = '/f/' + encodeURIComponent(foundupId);
  }

  /**
   * Enter FoundUp view (legacy - opens quick-view plane)
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
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
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
          var readA = READINESS_ORDER[a.launch_readiness || a.status] || 0;
          var readB = READINESS_ORDER[b.launch_readiness || b.status] || 0;
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
   * Load remaining small discovery pages when an explicit sort/filter chip needs full-catalog coverage.
   */
  async function hydrateCatalogForFilter(expectedScope, expectedProjection) {
    while (catalogPager?.hasMore && currentFieldScope === expectedScope && currentProjection === expectedProjection) {
      var batch = await loadCatalogPage();
      if (!batch.length) break;
    }
  }

  /**
   * Set projection mode and re-render tiles
   * @param {string} projection - Projection name: default, alpha, readiness, category
   */
  function setProjection(projection, options) {
    if (fixedVideoField) return;
    resetMediaScope();
    if (!['default', 'alpha', 'readiness', 'category'].includes(projection)) {
      projection = 'default';
    }

    if (!options?.preserveScope) currentFieldScope = null;
    mallCatalog = options?.preserveScope ? filterByScope(currentFieldScope) : fullCatalog.slice();
    originalOrder = mallCatalog.slice();
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
    var activeGroup = currentFieldScope && currentFieldScope.type === 'source_group'
      ? currentFieldScope.query : null;
    var chips = document.querySelectorAll('.mall-projection-chip[data-projection]');
    chips.forEach(function(chip) {
      var proj = chip.dataset.projection;
      var active = activeGroup ? false : (proj === currentProjection);
      chip.classList.toggle('active', active);
    });
    var groupChips = document.querySelectorAll('.mall-projection-chip[data-scope-group]');
    groupChips.forEach(function(chip) {
      chip.classList.toggle('active', chip.dataset.scopeGroup === activeGroup);
    });
  }

  /**
   * Bind projection chip click handlers and progressive Build v24 discovery pills
   */
  function bindProjectionChips() {
    var nav = document.getElementById('mallProjection');
    if (nav && !fixedVideoField && groupDefinitions === null && !nav.dataset.discoveryFiltersBound) {
      nav.dataset.discoveryFiltersBound = '1';
      [
        { group: 'videos', label: 'Videos' },
        { group: 'apps', label: 'Apps' },
        { group: 'shop', label: 'Shop' }
      ].forEach(function(spec) {
        if (nav.querySelector('[data-scope-group="' + spec.group + '"]')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mall-projection-chip mall-filter-chip';
        btn.dataset.scopeGroup = spec.group;
        btn.textContent = spec.label;
        btn.addEventListener('click', function() {
          if (currentFieldScope && currentFieldScope.type === 'source_group' &&
              currentFieldScope.query === spec.group) {
            clearFieldScope();
          } else {
            filterBySourceGroup(spec.group);
            hydrateCatalogForFilter(currentFieldScope, currentProjection);
          }
          window.mallStateRestore?.save?.();
        });
        nav.appendChild(btn);
      });
    }
    var chips = document.querySelectorAll('.mall-projection-chip[data-projection]');
    chips.forEach(function(chip) {
      if (chip.dataset.projectionBound) return;
      chip.dataset.projectionBound = '1';
      chip.addEventListener('click', function() {
        var proj = chip.dataset.projection || 'default';
        if (proj === 'default' && currentFieldScope !== null) {
          clearFieldScope();
        } else {
          setProjection(proj);
          if (proj !== 'default') {
            hydrateCatalogForFilter(currentFieldScope, currentProjection);
          }
        }
        window.mallStateRestore?.save?.();
      });
    });
    updateProjectionChips();
  }

  // ========== Field Scope System ==========

  /**
   * Apply field scope filter to catalog
   * @param {Object|string|null} scope - Scope options or 'personal' or null
   * @returns {Array} Filtered catalog
   */
  function filterByScope(scope) {
    if (!scope) return fullCatalog.slice();

    // Legacy string support
    if (scope === 'personal') {
      scope = { type: 'personal' };
    }

    if (scope.type === 'source_group' && scope.query) {
      var groupKey = String(scope.query).toLowerCase();
      if (groupKey === 'videos') {
        return sortScopedResults(fullCatalog.filter(function(item) {
          return ((item.videos && item.videos.length) || item.video_count || 0) > 0;
        }));
      }
      if (groupKey === 'apps') {
        return sortScopedResults(fullCatalog.filter(function(item) {
          return ['github_repo', 'external_app', 'internal_app', 'internal_service'].indexOf(item.source_type) !== -1;
        }));
      }
      if (groupKey === 'shop') {
        return sortScopedResults(fullCatalog.filter(function(item) {
          return String(item.category || '').toLowerCase() === 'marketplace' ||
            String(item.source_type || '').toLowerCase() === 'marketplace';
        }));
      }
      return fullCatalog.slice();
    }

    if (scope.type === 'query' && typeof scope.query === 'string') {
      return sortScopedResults(fullCatalog.filter(function(item) { return matchesCatalogQuery(item, scope.query); }));
    }

    if (scope.type === 'personal') {
      // Filter to 012 lanes only
      var personal = fullCatalog.filter(function(item) {
        return item.creator === '012' || item.tags?.includes('012-lane');
      });
      return sortScopedResults(personal);
    }

    if (scope.type === 'creator' && scope.query) {
      // Filter by creator name (case-insensitive substring match)
      var query = scope.query.toLowerCase();
      var matches = fullCatalog.filter(function(item) {
        var creator = (item.creator || '').toLowerCase();
        var entity = (item.entity || '').toLowerCase();
        return creator.indexOf(query) !== -1 || entity.indexOf(query) !== -1;
      });
      return sortScopedResults(matches);
    }

    if (scope.type === 'category' && scope.query) {
      // Filter by category (case-insensitive match)
      var catQuery = scope.query.toLowerCase();
      var catMatches = fullCatalog.filter(function(item) {
        return (item.category || '').toLowerCase() === catQuery;
      });
      return sortScopedResults(catMatches);
    }

    if (scope.type === 'tag' && scope.query) {
      // Filter by tag (exact match in tags array)
      var tagQuery = scope.query.toLowerCase();
      var tagMatches = fullCatalog.filter(function(item) {
        if (!item.tags || !Array.isArray(item.tags)) return false;
        return item.tags.some(function(t) {
          return t.toLowerCase() === tagQuery;
        });
      });
      return sortScopedResults(tagMatches);
    }

    return fullCatalog.slice();
  }

  /**
   * Sort scoped results: video_count > 0 first, then display_order
   * @param {Array} items - Filtered items
   * @returns {Array} Sorted items
   */
  function sortScopedResults(items) {
    items.sort(function(a, b) {
      var aHasVideos = (a.video_count || 0) > 0;
      var bHasVideos = (b.video_count || 0) > 0;

      // Videos first, zero-video at end
      if (aHasVideos && !bHasVideos) return -1;
      if (!aHasVideos && bHasVideos) return 1;

      // Within same video status, sort by display_order
      var orderA = a.display_order || 999;
      var orderB = b.display_order || 999;
      return orderA - orderB;
    });
    return items;
  }

  /**
   * Set field scope with options
   * @param {Object} options - { type: 'personal'|'creator'|'category'|'tag', query?: string }
   */
  function setFieldScope(options) {
    if (fixedVideoField) return false;
    if (!options || !options.type) {
      clearFieldScope();
      return;
    }

    resetMediaScope();
    currentFieldScope = options;
    mallCatalog = filterByScope(options);
    originalOrder = mallCatalog.slice();
    currentProjection = 'default';
    renderTiles();
    bindInteractions();
    updateProjectionChips();
  }

  /**
   * Project Personal Mall (012 lanes only)
   * Scopes field to creator === '012'
   */
  function projectPersonalMall() {
    setFieldScope({ type: 'personal' });
  }

  /**
   * Search by creator name (string match, no backend)
   * @param {string} query - Creator name search string
   */
  function searchByCreator(query) {
    if (!query || !query.trim()) {
      clearFieldScope();
      return;
    }
    setFieldScope({ type: 'creator', query: query.trim() });
  }

  /**
   * Filter by category
   * @param {string} category - Category name
   */
  function filterByCategory(category) {
    if (!category || !category.trim()) {
      clearFieldScope();
      return;
    }
    setFieldScope({ type: 'category', query: category.trim() });
  }

  /**
   * Filter by tag
   * @param {string} tag - Tag name
   */
  function filterByTag(tag) {
    if (!tag || !tag.trim()) {
      clearFieldScope();
      return;
    }
    setFieldScope({ type: 'tag', query: tag.trim() });
  }

  /**
   * Filter by content source group ('videos' | 'apps')
   * @param {string} group - Source group identifier
   */
  function filterBySourceGroup(group) {
    if (!group || !String(group).trim()) {
      clearFieldScope();
      return;
    }
    setFieldScope({ type: 'source_group', query: String(group).trim().toLowerCase() });
  }

  /**
   * Clear field scope (show all lanes)
   */
  function clearFieldScope() {
    if (fixedVideoField) return;
    if (currentFieldScope === null) return;
    resetMediaScope();
    currentFieldScope = null;
    mallCatalog = fullCatalog.slice();
    originalOrder = mallCatalog.slice();
    currentProjection = 'default';
    renderTiles();
    bindInteractions();
    updateProjectionChips();
  }

  /**
   * Get current field scope
   * @returns {Object|null} Scope options or null
   */
  function getFieldScope() {
    return currentFieldScope;
  }

  // Expose public API
  var videoOptionsSubscription = null;
  function bindVideoOptionPlacement() {
    if (videoOptionsSubscription) return;
    videoOptionsSubscription = window.mallStateRestore?.subscribeVideoOptions?.(function(options) {
    var add = tileField?.querySelector('.mall-grid-add-video');
    if (!fixedVideoField || !add) return;
    var position = captureFixedPosition();
    if (options.addVideoPosition === 'first') tileField.prepend(add);
    else tileField.insertBefore(add, tileField.querySelector('.mall-video-grid-tail'));
    restoreVideoGridState(position);
    });
  }

  window.mallTileField = {
    // Shared responsive browse and local discovery
    setLayoutMode: setLayoutMode,
    getLayoutMode: function() { return groupDefinitions !== null ? 'grouped' : layoutMode; },
    getRowOffsets: captureRowOffsets,
    restoreRowOffsets: restoreRowOffsets,
    restoreBrowsePosition: restoreBrowsePosition,
    searchCatalog: searchCatalog,

    // Core
    initialize: initialize,
    updateCatalog: updateCatalog,
    openEntityById: openEntityById,
    getLoadedCatalog: function() { return fullCatalog.slice(); },
    preparePlayerReturn: preparePlayerReturn,
    getGeographicState: getGeographicState,
    restoreGeographicState: restoreGeographicState,
    getVideoGridState: getVideoGridState,
    setScopedTheater: setScopedTheater,
    getScopedPhoneQuery: function() { return scopedPhoneQuery; },
    setScopedPhoneQuery: setScopedPhoneQuery,
    matchesVideoQuery: matchesScopedVideo,
    restoreVideoGridState: restoreVideoGridState,
    enterFoundUp: enterFoundUp,
    navigateToFoundUp: navigateToFoundUp,

    // Video runtime
    togglePlay: togglePlay,
    getPlayingIndex: getPlayingIndex,
    getActiveVideo: getActiveVideo,
    restoreActiveVideo: restoreActiveVideo,
    expandFoundUp: expandFoundUp,
    collapseFoundUp: collapseFoundUp,
    isExpanded: isExpanded,
    getExpandedIndex: getExpandedIndex,

    // Lane autoplay
    startLanePreview: startLanePreview,
    advanceToNextInLane: advanceToNextInLane,
    getLaneVideoIndex: function() { return laneVideoIndex; },
    getCurrentLaneFoundupIndex: function() { return currentLaneFoundupIndex; },

    // Inline preview
    startInlinePreview: startInlinePreview,
    stopInlinePreview: stopInlinePreview,
    pauseInlinePreview: pauseInlinePreview,
    resumeInlinePreview: resumeInlinePreview,
    togglePreviewMute: togglePreviewMute,

    // Motion mode
    setMotionMode: setMotionMode,
    getMotionMode: getMotionMode,

    // Density (use requestDensity for AI/RedDog, setDensity is low-level)
    requestDensity: requestDensity,
    getDevicePolicy: getDevicePolicy,
    setDensity: setDensity,
    getDensity: getDensity,
    detectOptimalDensity: detectOptimalDensity,
    autoSelectDensity: autoSelectDensity,
    resetDensityOverride: resetDensityOverride,

    // Projection
    setProjection: setProjection,
    getProjection: getProjection,
    resetProjection: resetProjection,

    // Field Scope (My Mall + Search)
    projectPersonalMall: projectPersonalMall,
    setFieldScope: setFieldScope,
    clearFieldScope: clearFieldScope,
    getFieldScope: getFieldScope,
    searchByCreator: searchByCreator,
    filterByCategory: filterByCategory,
    filterByTag: filterByTag,
    filterBySourceGroup: filterBySourceGroup,

    // Intelligent Grid Loading (PFM11B)
    getTileLoadState: getTileLoadState,
    getTileLoadStates: getTileLoadStates,
    getLoadPolicy: getLoadPolicy,
    isViewportLoadingActive: isViewportLoadingActive,
    isPhonePatchViewport: isPhonePatchViewport,
    flipTile: function(foundupId, flipped) {
      if (!tileField) return false;
      var tile = tileField.querySelector('.mall-tile[data-foundup-id="' + String(foundupId || '').replace(/["\\]/g, '') + '"]');
      return setTileFlipped(tile, flipped);
    },

    // Debug helpers
    debugTiles: function() {
      var items = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
      console.table(items.map(function(item, i) {
        return {
          index: i,
          foundup_id: item.foundup_id,
          name: (item.name || item.title || '').substring(0, 30),
          poster_url: (item.poster_url || '').substring(0, 50)
        };
      }));
      console.log('Total tiles:', items.length, '| Density:', currentDensity, '| Expanded:', expandedFoundUp);
    },
    getCatalog: function() { return mallCatalog; }
  };

})();
