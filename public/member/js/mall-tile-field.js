/**
 * Mall Tile Field — Video-backed discovery surface
 *
 * Video Mall runtime with snapped field motion.
 * SoftProto mount point: #mallTileField[data-softproto-mount="tile-field"]
 *
 * Gestures (Mall context):
 *   - Tap tile: Play/pause inline preview in Mall context
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
  var currentDensity = '2x3';
  var expandedFoundUp = null; // Index of expanded FoundUp, or null
  var expandSourceIndex = null; // Original tile index for collapse animation
  var playingIndex = null; // Index of currently previewing tile
  var previewPaused = false;
  var previewMuted = false;
  var inlinePreviewVideo = null;
  var inlinePreviewYTPlayer = null;
  var inlinePreviewSession = 0;
  var ytPreviewAPIReady = false;
  var ytPreviewWaiters = [];

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

    // Warm the YouTube IFrame API so first inline preview is responsive.
    if (mallCatalog.some(function(item) { return hasTileVideos(item); })) {
      ensureYouTubeAPI(function () {});
    }

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
      var theme = escapeAttr(item.theme || item.foundup_id || CATEGORY_THEME[item.category] || 'default');
      var readiness = item.launch_readiness || item.status || 'discoverable_only';
      var badgeClass = readiness === 'ready' ? 'ready' : (readiness === 'conditional' ? 'conditional' : '');
      var hasVideos = hasTileVideos(item);

      // Video-backed: use poster_url as background
      var posterStyle = item.poster_url ? 'background-image: url(' + escapeAttr(item.poster_url) + ')' : '';

      // Queue count (video_count or videos array length)
      var queueCount = item.video_count || (item.videos ? item.videos.length : 0);
      var queueBadge = queueCount > 0 ? '<span class="mall-tile-queue-count">' + queueCount + ' videos</span>' : '';

      // Play indicator
      var playIndicator = '<div class="mall-tile-play-indicator"></div>';

      var previewStage = hasVideos ? '<div class="mall-tile-preview" aria-hidden="true"><div class="mall-tile-preview-stage"></div></div>' : '';
      var audioBtn = hasVideos ? [
        '<button class="mall-tile-audio" aria-label="Start muted preview" title="Start muted preview">',
        '  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 8.5a5 5 0 0 1 0 7M17 6a8.5 8.5 0 0 1 0 12M5 9h4l5-4v14l-5-4H5z"/></svg>',
        '</button>'
      ].join('') : '';
      var expandBtn = hasVideos ? [
        '<button class="mall-tile-expand" aria-label="Open fullscreen" title="Open fullscreen">',
        '  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5"/></svg>',
        '</button>'
      ].join('') : '';

      return '<article class="mall-tile' + (hasVideos ? ' has-video-controls' : '') + ' theme-' + theme + '" data-index="' + index + '" data-foundup-id="' + escapeAttr(item.foundup_id || item.id || '') + '" tabindex="0" aria-label="' + escapeAttr(item.name || item.title || '') + '" style="' + posterStyle + '">' +
        previewStage +
        '<span class="mall-tile-badge ' + badgeClass + '">' + escapeHtml(readiness.replace('_', ' ')) + '</span>' +
        queueBadge +
        playIndicator +
        audioBtn +
        expandBtn +
        '<div class="mall-tile-inner">' +
          '<span class="mall-tile-token">' + escapeHtml(item.token_symbol || '') + '</span>' +
          '<span class="mall-tile-hero">' + escapeHtml(item.hero_label || '') + '</span>' +
          '<p class="mall-tile-name">' + escapeHtml(item.name || item.title || '') + '</p>' +
        '</div>' +
      '</article>';
    }).join('');

    // Update expanded mode class
    tileField.classList.toggle('expanded-mode', expandedFoundUp !== null);
    applyTilePreviewState();
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

  function hasTileVideos(item) {
    if (!item) return false;
    if (item.video_data) return true;
    return !!((item.videos && item.videos.length) || item.video_count);
  }

  function getTileItem(index) {
    var items = expandedFoundUp !== null ? getExpandedVideos() : mallCatalog;
    return items[index] || null;
  }

  function getTilePreviewVideo(index) {
    var item = getTileItem(index);
    if (!item) return null;
    if (item.video_data) return item.video_data;
    if (item.videos && item.videos.length) return item.videos[0];
    return null;
  }

  function getTileElement(index) {
    if (!tileField) return null;
    return tileField.querySelector('.mall-tile[data-index="' + index + '"]');
  }

  function ensureYouTubeAPI(callback) {
    if (window.YT && window.YT.Player) {
      ytPreviewAPIReady = true;
      if (callback) callback();
      return;
    }

    if (callback) {
      ytPreviewWaiters.push(callback);
    }

    var prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function() {
      ytPreviewAPIReady = true;
      if (typeof prev === 'function') prev();
      while (ytPreviewWaiters.length) {
        try {
          ytPreviewWaiters.shift()();
        } catch (err) {
          console.warn('[mall-tile-field] YouTube preview callback failed', err);
        }
      }
    };

    if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      var tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(tag);
    }
  }

  function extractYouTubeVideoId(embedUrl) {
    if (!embedUrl) return null;
    var match = embedUrl.match(/youtube\.com\/embed\/([A-Za-z0-9_-]+)/);
    return match ? match[1] : null;
  }

  function destroyInlineYTPlayer() {
    if (inlinePreviewYTPlayer) {
      try {
        inlinePreviewYTPlayer.destroy();
      } catch (err) {
        // Player was already torn down.
      }
      inlinePreviewYTPlayer = null;
    }
  }

  function applyTilePreviewState() {
    if (!tileField) return;

    var tiles = tileField.querySelectorAll('.mall-tile');
    tiles.forEach(function(tile, index) {
      var isActive = index === playingIndex;
      tile.classList.toggle('is-previewing', isActive);
      tile.classList.toggle('is-playing', isActive && !previewPaused);
      tile.classList.toggle('is-paused', isActive && previewPaused);
      tile.classList.toggle('is-muted', isActive && previewMuted);

      var audioBtn = tile.querySelector('.mall-tile-audio');
      if (audioBtn) {
        var label = 'Start muted preview';
        if (isActive) {
          label = previewMuted ? 'Unmute preview' : 'Mute preview';
        }
        audioBtn.classList.toggle('is-active', isActive);
        audioBtn.classList.toggle('is-muted', isActive && previewMuted);
        audioBtn.setAttribute('aria-label', label);
        audioBtn.setAttribute('title', label);
      }
    });
  }

  function stopInlinePreview() {
    inlinePreviewSession += 1;

    if (inlinePreviewVideo) {
      try {
        inlinePreviewVideo.pause();
      } catch (err) {
        // Ignore teardown issues from detached media nodes.
      }
      inlinePreviewVideo = null;
    }

    destroyInlineYTPlayer();

    if (tileField) {
      var stages = tileField.querySelectorAll('.mall-tile-preview-stage');
      stages.forEach(function(stageEl) {
        stageEl.innerHTML = '';
      });
    }

    playingIndex = null;
    previewPaused = false;
    previewMuted = false;
    applyTilePreviewState();
  }

  function setPreviewMutedState(muted) {
    previewMuted = !!muted;

    if (inlinePreviewVideo) {
      inlinePreviewVideo.muted = previewMuted;
    }

    if (inlinePreviewYTPlayer) {
      if (previewMuted && inlinePreviewYTPlayer.mute) {
        inlinePreviewYTPlayer.mute();
      } else if (!previewMuted && inlinePreviewYTPlayer.unMute) {
        inlinePreviewYTPlayer.unMute();
      }
    }

    applyTilePreviewState();
  }

  function pauseInlinePreview() {
    if (playingIndex === null) return;
    previewPaused = true;

    if (inlinePreviewVideo) {
      inlinePreviewVideo.pause();
    }

    if (inlinePreviewYTPlayer && inlinePreviewYTPlayer.pauseVideo) {
      inlinePreviewYTPlayer.pauseVideo();
    }

    applyTilePreviewState();
  }

  function resumeInlinePreview() {
    if (playingIndex === null) return;
    previewPaused = false;

    if (inlinePreviewVideo) {
      var playPromise = inlinePreviewVideo.play();
      if (playPromise && playPromise.catch) {
        playPromise.catch(function() {
          previewPaused = true;
          applyTilePreviewState();
        });
      }
    }

    if (inlinePreviewYTPlayer && inlinePreviewYTPlayer.playVideo) {
      inlinePreviewYTPlayer.playVideo();
    }

    applyTilePreviewState();
  }

  function startInlinePreview(index, muted) {
    var video = getTilePreviewVideo(index);
    var tile = getTileElement(index);
    var stageEl = tile && tile.querySelector('.mall-tile-preview-stage');
    var embedUrl = video && (video.embed_url || video.embedUrl);
    var sourceUrl = video && (video.source_url || video.sourceUrl);
    var ytId = extractYouTubeVideoId(embedUrl);

    if (!video || !tile || !stageEl) return false;

    if (playingIndex !== null && playingIndex !== index) {
      stopInlinePreview();
    } else if (playingIndex === index) {
      destroyInlineYTPlayer();
      if (inlinePreviewVideo) {
        inlinePreviewVideo.pause();
        inlinePreviewVideo = null;
      }
      stageEl.innerHTML = '';
    }

    playingIndex = index;
    previewPaused = false;
    previewMuted = !!muted;
    inlinePreviewSession += 1;
    var session = inlinePreviewSession;

    applyTilePreviewState();

    if (ytId) {
      function createYTPreview() {
        if (session !== inlinePreviewSession || playingIndex !== index) return;

        stageEl.innerHTML = '';
        var holder = document.createElement('div');
        holder.id = 'mallTilePreviewHost_' + index + '_' + session;
        holder.className = 'mall-tile-preview-host';
        stageEl.appendChild(holder);
        destroyInlineYTPlayer();

        inlinePreviewYTPlayer = new window.YT.Player(holder.id, {
          videoId: ytId,
          playerVars: {
            autoplay: 1,
            controls: 0,
            rel: 0,
            modestbranding: 1,
            playsinline: 1
          },
          events: {
            onReady: function(event) {
              if (session !== inlinePreviewSession || playingIndex !== index) return;
              if (previewMuted && event.target.mute) {
                event.target.mute();
              } else if (event.target.unMute) {
                event.target.unMute();
              }
              if (previewPaused && event.target.pauseVideo) {
                event.target.pauseVideo();
              } else if (event.target.playVideo) {
                event.target.playVideo();
              }
            },
            onStateChange: function(event) {
              if (session !== inlinePreviewSession || playingIndex !== index) return;

              if (event.data === window.YT.PlayerState.ENDED) {
                stopInlinePreview();
              } else if (event.data === window.YT.PlayerState.PAUSED) {
                previewPaused = true;
                applyTilePreviewState();
              } else if (event.data === window.YT.PlayerState.PLAYING) {
                previewPaused = false;
                applyTilePreviewState();
              }
            }
          }
        });
      }

      if (ytPreviewAPIReady && window.YT && window.YT.Player) {
        createYTPreview();
      } else {
        ensureYouTubeAPI(createYTPreview);
      }
      return true;
    }

    if (sourceUrl && sourceUrl.match(/\.(mp4|webm|ogg)$/i)) {
      stageEl.innerHTML = '';
      inlinePreviewVideo = document.createElement('video');
      inlinePreviewVideo.className = 'mall-tile-preview-media';
      inlinePreviewVideo.src = sourceUrl;
      inlinePreviewVideo.autoplay = true;
      inlinePreviewVideo.controls = false;
      inlinePreviewVideo.loop = false;
      inlinePreviewVideo.playsInline = true;
      inlinePreviewVideo.muted = previewMuted;
      inlinePreviewVideo.preload = 'metadata';
      inlinePreviewVideo.setAttribute('playsinline', '');
      inlinePreviewVideo.addEventListener('play', function() {
        if (session !== inlinePreviewSession || playingIndex !== index) return;
        previewPaused = false;
        applyTilePreviewState();
      });
      inlinePreviewVideo.addEventListener('pause', function() {
        if (session !== inlinePreviewSession || playingIndex !== index) return;
        previewPaused = true;
        applyTilePreviewState();
      });
      inlinePreviewVideo.addEventListener('ended', function() {
        if (session !== inlinePreviewSession || playingIndex !== index) return;
        stopInlinePreview();
      });
      stageEl.appendChild(inlinePreviewVideo);

      var playPromise = inlinePreviewVideo.play();
      if (playPromise && playPromise.catch) {
        playPromise.catch(function() {
          previewPaused = true;
          applyTilePreviewState();
        });
      }
      return true;
    }

    stopInlinePreview();
    return false;
  }

  function togglePreviewMute(index) {
    if (playingIndex !== index) {
      startInlinePreview(index, true);
      return;
    }

    setPreviewMutedState(!previewMuted);
  }

  /**
   * Bind tile interactions (video Mall runtime)
   */
  function bindInteractions() {
    var tiles = tileField.querySelectorAll('.mall-tile');

    tiles.forEach(function(tile) {
      // Touch/click handling: tap = inline preview play/pause, double-tap = enter
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
          // Single tap: toggle inline preview in Mall context
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
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var index = Number(tile.dataset.index || 0);
        openFullscreenFromTile(index);
      });
    });

    var audioBtns = tileField.querySelectorAll('.mall-tile-audio');
    audioBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var tile = btn.closest('.mall-tile');
        if (!tile) return;
        var index = Number(tile.dataset.index || 0);
        togglePreviewMute(index);
      });
    });

    // Global escape handler - collapse expanded view
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
   * Toggle inline preview play/pause for a tile
   * @param {number} index - Tile index
   */
  function togglePlay(index) {
    var tiles = tileField.querySelectorAll('.mall-tile');
    var targetTile = tiles[index];
    var previewVideo = getTilePreviewVideo(index);

    // Immediate visual feedback: tap pulse
    if (targetTile) {
      targetTile.classList.remove('tap-pulse');
      // Force reflow to restart animation
      void targetTile.offsetWidth;
      targetTile.classList.add('tap-pulse');
    }

    if (!previewVideo) return;

    if (playingIndex === index) {
      if (previewPaused) {
        resumeInlinePreview();
      } else {
        pauseInlinePreview();
      }
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

    var item = mallCatalog[index];
    if (!item || !item.videos || !item.videos.length) {
      console.warn('[mall-tile-field] Cannot expand: no videos for FoundUp', index);
      return;
    }

    stopInlinePreview();

    var sourceTile = getTileElement(index);
    var sourceRect = sourceTile ? sourceTile.getBoundingClientRect() : null;
    var reducedMotion = prefersReducedMotion();

    // Store source index for collapse animation
    expandSourceIndex = index;

    // FLIP animation (skip if reduced motion)
    if (sourceRect && !reducedMotion) {
      var bgImage = sourceTile.style.backgroundImage || '';
      var bgColor = window.getComputedStyle(sourceTile).backgroundColor;
      var flipLayer = createFlipLayer(sourceRect, bgImage, bgColor);

      // Target: full viewport (the expanded field area)
      var targetRect = tileField.getBoundingClientRect();

      // Force reflow before animation
      void flipLayer.offsetWidth;

      // Animate to target
      flipLayer.style.left = targetRect.left + 'px';
      flipLayer.style.top = targetRect.top + 'px';
      flipLayer.style.width = targetRect.width + 'px';
      flipLayer.style.height = targetRect.height + 'px';
      flipLayer.classList.add('flip-expanding');

      // Render actual content during animation
      tileField.classList.add('transitioning');
      expandedFoundUp = index;
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
    if (sourceIndex !== null && !reducedMotion) {
      // Capture first frame from expanded field
      var firstTile = tileField.querySelector('.mall-tile');
      var bgImage = firstTile ? firstTile.style.backgroundImage || '' : '';
      var bgColor = firstTile ? window.getComputedStyle(firstTile).backgroundColor : '';
      var flipLayer = createFlipLayer(expandedRect, bgImage, bgColor);
      flipLayer.style.borderRadius = '0';

      // Render mall tiles (to get target rect)
      tileField.classList.add('transitioning');
      expandedFoundUp = null;
      renderTiles();
      bindInteractions();

      // Find target tile position
      var targetTile = getTileElement(sourceIndex);
      var targetRect = targetTile ? targetTile.getBoundingClientRect() : null;

      if (targetRect) {
        // Force reflow
        void flipLayer.offsetWidth;

        // Animate to target tile position
        flipLayer.style.left = targetRect.left + 'px';
        flipLayer.style.top = targetRect.top + 'px';
        flipLayer.style.width = targetRect.width + 'px';
        flipLayer.style.height = targetRect.height + 'px';
        flipLayer.classList.add('flip-collapsing');

        // Cleanup after animation
        setTimeout(function() {
          cleanupFlipLayer(flipLayer);
          tileField.classList.remove('transitioning');
          expandSourceIndex = null;
        }, 270);
      } else {
        // No target found, instant cleanup
        cleanupFlipLayer(flipLayer);
        tileField.classList.remove('transitioning');
        expandSourceIndex = null;
      }
    } else {
      // Reduced motion: instant transition
      tileField.classList.add('transitioning');

      setTimeout(function() {
        expandedFoundUp = null;
        renderTiles();
        bindInteractions();
        tileField.classList.remove('transitioning');
        expandSourceIndex = null;
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
    stopInlinePreview();

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
    if (!['default', 'alpha', 'readiness', 'category'].includes(projection)) {
      projection = 'default';
    }

    currentProjection = projection;
    stopInlinePreview();
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
    stopInlinePreview();
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
    currentFieldScope = null;
    stopInlinePreview();
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
