/**
 * Mall Tile Field — Video-backed discovery surface
 *
 * Portrait-first 9:16 video wall (Shorts-style)
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
 *   - 3x4, 3x5, 4x6, 5x8 (default: 3x5 for mobile-first dense wall)
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

  // Field scope state (filter before projection)
  var currentFieldScope = null;  // null = all, 'personal' = 012 lanes only
  var fullCatalog = [];  // Unscoped catalog reference

  // Category → theme fallback (used when item.theme and item.foundup_id have no CSS match)
  var CATEGORY_THEME = {
    'travel': 'cat-travel',
    'music': 'cat-music',
    'startup': 'cat-startup',
    'media': 'cat-media',
    'thought-leadership': 'cat-thought-leadership',
    'ai-education': 'cat-ai-education',
    'ai-research': 'cat-ai-research'
  };

  // Video Mall runtime state
  var motionMode = 'snap'; // 'snap' | 'glide'
  var currentDensity = '3x5';
  var expandedFoundUp = null; // Index of expanded FoundUp, or null
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
    if (!item) return null;
    return item.video_data || (item.videos && item.videos[0]) || null;
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
    var tile = allTiles[index];
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
  function initialize(catalog) {
    fullCatalog = catalog || [];
    mallCatalog = fullCatalog.slice();
    originalOrder = mallCatalog.slice();  // Preserve original order
    currentFieldScope = null;  // Reset scope on init
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

    // Enable desktop drag-to-scroll
    bindDragScroll();

    // Track scroll state for edge shadows
    bindScrollState();

    // Bind page visibility handler for resource discipline
    bindVisibilityHandler();

    renderTiles();
    bindInteractions();
    bindProjectionChips();
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

      function onMouseDown(e) {
        // Ignore if on interactive elements
        if (e.target.closest('button, a, [tabindex]')) return;
        if (e.button !== 0) return;

        isDragging = true;
        dragMoved = false;
        startX = e.clientX;
        startY = e.clientY;
        scrollStartX = tileFieldWrapper.scrollLeft;
        scrollStartY = tileFieldWrapper.scrollTop;
        tileFieldWrapper.classList.add('is-dragging');
        e.preventDefault();
      }

      function onMouseMove(e) {
        if (!isDragging) return;
        var dx = e.clientX - startX;
        var dy = e.clientY - startY;
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
          dragMoved = true;
          tapGuardActive = true;
        }
        tileFieldWrapper.scrollLeft = scrollStartX - dx;
        tileFieldWrapper.scrollTop = scrollStartY - dy;
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
    }

    tileFieldWrapper.addEventListener('scroll', updateScrollState, { passive: true });
    // Initial check
    updateScrollState();
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
      var theme = escapeAttr(item.theme || item.foundup_id || CATEGORY_THEME[item.category] || 'default');
      var readiness = item.launch_readiness || item.status || 'discoverable_only';
      var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');

      // Video-backed: use poster_url as background
      var posterStyle = item.poster_url ? 'background-image: url(' + escapeAttr(item.poster_url) + ')' : '';

      // Determine if tile has videos (includes expanded video tiles with video_data)
      var hasVideos = (item.videos && item.videos.length) || item.video_count || item.video_data;

      // Queue count (video_count or videos array length) — video tiles only
      var queueCount = item.video_count || (item.videos ? item.videos.length : 0);
      var queueBadge = queueCount > 0 ? '<span class="mall-tile-queue-count">' + queueCount + ' videos</span>' : '';

      // Play indicator — video tiles only
      var playIndicator = hasVideos ? '<div class="mall-tile-play-indicator"></div>' : '';

      // Corner expand button for explicit fullscreen entry — video tiles only
      var expandBtn = hasVideos ? '<button class="mall-tile-expand" aria-label="Open fullscreen" title="Fullscreen">&#9654;</button>' : '';

      // FoundUp entry button (bottom-left) — all tiles, explicit entry path
      var entryBtnSvg = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>';
      var entryBtn = '<button class="mall-tile-entry" aria-label="About ' + escapeAttr(item.name || item.title || 'this FoundUp') + '" title="About">' + entryBtnSvg + '</button>';

      // Inline preview container (YouTube iframe or HTML5 video goes here) — video tiles only
      var previewContainer = hasVideos ? '<div class="mall-tile-preview"><div class="mall-tile-preview-stage"></div></div>' : '';

      // Speaker button for mute/unmute (top-left, video-backed only)
      var speakerSvg = '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
      var audioBtn = hasVideos ? '<button class="mall-tile-audio" aria-label="Start muted preview" title="Start muted preview">' + speakerSvg + '</button>' : '';

      // Non-video source type action badge
      var sourceTypeActions = {
        'github_repo': 'View Repo',
        'external_app': 'Open App',
        'internal_service': 'Open Service'
      };
      var sourceAction = !hasVideos && item.source_type && sourceTypeActions[item.source_type];
      var sourceActionBadge = sourceAction ? '<span class="mall-tile-action-badge">' + sourceAction + '</span>' : '';

      // Non-video tile class modifier
      var tileClass = 'mall-tile theme-' + theme + (hasVideos ? '' : ' non-video');

      return '<article class="' + tileClass + '" data-index="' + index + '" data-foundup-id="' + escapeAttr(item.foundup_id || item.id || '') + '" tabindex="0" aria-label="' + escapeAttr(item.name || item.title || '') + '" style="' + posterStyle + '">' +
        previewContainer +
        '<span class="mall-tile-badge ' + badgeClass + '">' + escapeHtml(readiness.replace('_', ' ')) + '</span>' +
        queueBadge +
        sourceActionBadge +
        playIndicator +
        audioBtn +
        expandBtn +
        entryBtn +
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
  function bindInteractions() {
    var tiles = tileField.querySelectorAll('.mall-tile');

    tiles.forEach(function(tile) {
      // Touch/click handling: tap = play/pause, double-tap = enter
      tile.addEventListener('click', function(e) {
        // Ignore tap if guard is active (just finished dragging)
        if (tapGuardActive) return;

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

    // Corner expand buttons — open fullscreen, stop event from reaching tile tap
    var expandBtns = tileField.querySelectorAll('.mall-tile-expand');
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
    var audioBtns = tileField.querySelectorAll('.mall-tile-audio');
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

    // Entry buttons — explicit FoundUp landing entry using stable identity
    // Routes directly to canonical /f/{foundup_id} landing (WSP 104), not preview plane
    var entryBtns = tileField.querySelectorAll('.mall-tile-entry');
    entryBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (tapGuardActive) return;
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var foundupId = tile.dataset.foundupId;
        if (!foundupId) return;
        // Extract parent ID from expanded-mode synthetic IDs (e.g., "abc123_video_0" -> "abc123")
        var parentId = foundupId.replace(/_video_\d+$/, '');
        // Navigate directly to canonical landing route (WSP 104)
        window.location.href = '/f/' + encodeURIComponent(parentId);
      });
    });

    // Global escape handler - collapse expanded view or stop preview
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && expandedFoundUp !== null) {
        e.stopPropagation();
        collapseFoundUp();
      } else if (e.key === 'Escape' && playingIndex !== null) {
        e.stopPropagation();
        stopInlinePreview();
      }
    });
  }

  /**
   * Toggle play/pause for a tile
   * @param {number} index - Tile index
   */
  function togglePlay(index) {
    var tiles = tileField.querySelectorAll('.mall-tile');
    var targetTile = tiles[index];

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
    var hasVideos = item && ((item.videos && item.videos.length) || item.video_count || item.video_data);

    // Non-video tiles: open quick-view instead of trying inline preview
    if (!hasVideos) {
      var foundupId = item && (item.foundup_id || item.id);
      if (foundupId && window.mallPlanes && typeof window.mallPlanes.openFoundUpById === 'function') {
        window.mallPlanes.openFoundUpById(foundupId);
      }
      return;
    }

    // Video tiles: inline preview behavior
    if (playingIndex === index) {
      if (previewPaused) resumeInlinePreview();
      else pauseInlinePreview();
      return;
    }
    startInlinePreview(index, false);
  }

  /**
   * Open fullscreen player from a tile interaction.
   * In Mall mode: opens the FoundUp's video queue starting at first video.
   * In expanded mode: opens at the specific video index.
   * @param {number} index - Tile index
   */
  function openFullscreenFromTile(index) {
    if (!window.mallVideoPlayer) return;

    stopInlinePreview();

    if (expandedFoundUp !== null) {
      // Expanded mode: tiles are individual videos from one FoundUp
      var parentItem = mallCatalog[expandedFoundUp];
      if (!parentItem || !parentItem.videos || !parentItem.videos.length) return;
      var foundupId = parentItem.foundup_id || parentItem.id || '';
      window.mallVideoPlayer.open(foundupId, parentItem.videos, index);
    } else {
      // Mall mode: tiles are FoundUps — open queue at first video
      var item = mallCatalog[index];
      if (!item) return;
      var foundupId = item.foundup_id || item.id || '';
      var queue = item.videos || [];
      if (!queue.length) return; // No videos to play
      window.mallVideoPlayer.open(foundupId, queue, 0);
    }
  }

  /**
   * Get tile element by index
   * @param {number} index - Tile index
   * @returns {HTMLElement|null}
   */
  function getTileElement(index) {
    if (!tileField) return null;
    return tileField.querySelector('.mall-tile[data-index="' + index + '"]');
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
    if (expandedFoundUp === index) return; // Already expanded
    stopInlinePreview();

    var item = mallCatalog[index];
    if (!item || !item.videos || !item.videos.length) {
      console.warn('[mall-tile-field] Cannot expand: no videos for FoundUp', index);
      return;
    }

    var sourceTile = getTileElement(index);
    var sourceRect = sourceTile ? sourceTile.getBoundingClientRect() : null;
    var reducedMotion = prefersReducedMotion();

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
        if (collapseHint) {
          collapseHint.classList.add('visible');
        }
      }, 300);
    } else {
      // Reduced motion or no source: instant transition
      tileField.classList.add('transitioning');

      setTimeout(function() {
        expandedFoundUp = index;
        playingIndex = null;
        renderTiles();
        bindInteractions();
        tileField.classList.remove('transitioning');
        if (collapseHint) {
          collapseHint.classList.add('visible');
        }
      }, 60);
    }
  }

  /**
   * Collapse expanded video field back to Mall
   */
  function collapseFoundUp() {
    if (expandedFoundUp === null) return;
    stopInlinePreview();

    // Hide collapse hint first
    if (collapseHint) {
      collapseHint.classList.remove('visible');
    }

    var sourceIndex = expandSourceIndex;
    var expandedRect = tileField.getBoundingClientRect();
    var reducedMotion = prefersReducedMotion();

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

      setTimeout(function() {
        expandedFoundUp = null;
        playingIndex = null;
        renderTiles();
        bindInteractions();
        tileField.classList.remove('transitioning');
        expandSourceIndex = null;
        expandSourceVisual = null;
      }, 60);
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
   * @param {string} density - '3x4' | '3x5' | '4x6' | '5x8'
   */
  function setDensity(density) {
    var validDensities = ['3x4', '3x5', '4x6', '5x8'];
    if (!validDensities.includes(density)) {
      density = '3x5';
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
   * Set projection mode and re-render tiles
   * @param {string} projection - Projection name: default, alpha, readiness, category
   */
  function setProjection(projection) {
    stopInlinePreview();
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

    if (scope.type === 'personal') {
      // Filter to 012 lanes only
      var personal = fullCatalog.filter(function(item) {
        return item.creator === '012';
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
    if (!options || !options.type) {
      clearFieldScope();
      return;
    }

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
   * Clear field scope (show all lanes)
   */
  function clearFieldScope() {
    if (currentFieldScope === null) return;
    stopInlinePreview();
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

    // Inline preview
    startInlinePreview: startInlinePreview,
    stopInlinePreview: stopInlinePreview,
    pauseInlinePreview: pauseInlinePreview,
    resumeInlinePreview: resumeInlinePreview,
    togglePreviewMute: togglePreviewMute,

    // Motion mode
    setMotionMode: setMotionMode,
    getMotionMode: getMotionMode,

    // Density
    setDensity: setDensity,
    getDensity: getDensity,

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
    filterByTag: filterByTag
  };

})();
