/**
 * Mall Video Player — Unified Top-Anchored Floating Player, Desktop Theater & WikiTube Queue Player.
 *
 * Single shared player instance (#videoPlayerFullscreen) permanently mounted in document.body
 * so switching between Floating, Tucked, WikiTube, and Desktop Theater never reparents or
 * reloads the active media <iframe> / <video>.
 *
 * Modes:
 *   - Floating (.video-player-floating): top-anchored card over scrolling grid; swipe-right (or Tuck button)
 *     pauses when tucked to the screen edge; the visible restore handle returns a paused player;
 *     pinch-out opens WikiTube.
 *   - WikiTube (.video-player-wikitube): fullscreen sequential queue player with bounded skip/halt recovery
 *     for unavailable/restricted videos and pinch-in return to grid.
 *   - Theater (.video-player-theater): wide-viewport desktop stage + search + thumbnail rail.
 *
 * Depends on:
 *   - gesture-engine.js (window.gestureZone)
 *   - CSS: mall-video-player.css
 */
(function () {
  'use strict';

  // ─── Constants ───
  var CHROME_AUTO_HIDE_MS = 3500;
  var PINCH_IN_RATIO = 0.78;
  var PINCH_OUT_RATIO = 1.25;
  var PINCH_MIN_DELTA_PX = 26;
  var PINCH_MIN_START_PX = 20;
  var TUCK_SWIPE_PX = 48;
  var UNTUCK_SWIPE_PX = 24;
  var YOUTUBE_TIMEOUT_MS = 12000;
  var PLAY_START_GUARD_MS = 2800;
  var DEFAULT_AUTO_SKIP_MS = 650;
  var MAX_CONSECUTIVE_AUTO_SKIPS = 5;
  var YOUTUBE_HOSTS = ['www.youtube.com', 'youtube.com', 'www.youtube-nocookie.com', 'youtube-nocookie.com'];

  // ─── State ───
  var container = null;
  var tuckHandle = null;
  var stage = null;
  var topBar = null;
  var queueRail = null;
  var queueTrack = null;
  var mediaPanel = null;
  var queuePanel = null;
  var queueSearchForm = null;
  var queueSearch = null;
  var queueEmpty = null;
  var filteredIndices = null;
  var matchesQuery = null;
  var edgeTrigger = null;
  var gestureHint = null;
  var titleEl = null;
  var saveBtn = null;
  var statusEl = null;
  var playBtn = null;
  var gestureGrip = null;
  var floatingPosition = null;
  var floatingDrag = null;
  var requestYouTubePlay = null;
  var memberMotionCleanup = null;
  var memberAnimation = null;

  var inline = false;
  var floating = false;
  var floatingLandscapeQuery = null;
  var theater = false;
  var wikitube = false;
  var tucked = false;
  var hiddenSelectionPending = false;
  // A live session can be paused behind the Mall without becoming a floating
  // player or being destroyed. This state is page-local, never persisted.
  var mallHidden = false;
  var mallReturnMode = null;
  var muteOnStart = false;
  var mutedAutoplayRetryUsed = false;
  var onClose = null;
  var onSelectChange = null;
  var onQueueEnd = null;
  var onPinchReturn = null;
  var onReturnToMall = null;
  var onResumeFromMall = null;
  var queueContinuation = null;
  var playbackIntentEpoch = 0;
  var autoplayRequested = true;
  var previousOverflow = null;
  var inertElements = [];
  var renderGeneration = 0;
  var playbackTimer = null;
  var startGuardTimer = null;
  var autoSkipTimer = null;
  var playbackStatus = null;

  var isOpen = false;
  var currentQueue = [];
  var currentFoundUpId = null;
  var currentEntryIdentity;
  var currentIndex = -1;
  var chromeTimer = null;
  var railTimer = null;

  // Bounded WikiTube sequential error-recovery tracking
  var failedQueueIndices = new Set();
  var consecutiveAutoSkips = 0;
  var queueHalted = false;

  // Gesture state
  var pinchActive = false;
  var pinchConsumed = false;
  var initialPinchDistance = 0;
  var swipeTracking = false;
  var swipeStartX = 0;
  var swipeStartY = 0;
  var swipeStartTime = 0;
  var gestureClickBlockedUntil = 0;
  var suppressNextClick = false;

  // ─── Storage Keys ───
  var SAVED_KEY = 'pfmall_saved_videos';
  var HISTORY_KEY = 'pfmall_watch_history';
  var HISTORY_MAX = 50;
  /** Local-only resume: omit sub-threshold & “finished” positions (HTML5 video only; embeds cannot read time). */
  var MIN_RESUME_SECONDS = 5;
  var COMPLETE_RATIO = 0.97;
  var pendingResumeSeconds = null;

  var returnTile = null;
  var memberQueueDock = null;
  var scopedDockLoan = null;
  var scopedQueueQuery = '';
  var railQuery = null;
  var returnScroll = null;
  var scopedPlayer = false;

  var ytPlayer = null;
  var ytReady = false;
  var ytHost = null;
  var ytActiveGeneration = 0;
  var ytActiveVideoId = null;
  var ytLoad = null;

  // ─── YouTube IFrame API ───
  function ensureYouTubeAPI() {
    if (window.YT?.Player) return Promise.resolve();
    if (ytLoad) return ytLoad;
    ytLoad = new Promise(function (resolve, reject) {
      var previous = window.onYouTubeIframeAPIReady;
      var existing = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');
      var script = existing || document.createElement('script');
      var timer = setTimeout(failed, YOUTUBE_TIMEOUT_MS);
      function cleanup() {
        clearTimeout(timer);
        script.removeEventListener('error', failed);
        if (window.onYouTubeIframeAPIReady === ready) window.onYouTubeIframeAPIReady = previous;
      }
      function ready() {
        cleanup();
        resolve();
        if (typeof previous === 'function') previous();
      }
      function failed() {
        cleanup();
        if (!existing) script.remove();
        reject(new Error('YouTube API unavailable'));
      }
      window.onYouTubeIframeAPIReady = ready;
      script.addEventListener('error', failed, { once: true });
      if (!existing) {
        script.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(script);
      }
    }).finally(function () { ytLoad = null; });
    return ytLoad;
  }

  // Warm IFrame API script in background when idle so first tile tap stays synchronous
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    var warmAPI = function () {
      if (window.YT?.Player) return;
      if (/^https?:$/.test(window.location?.protocol || '')) {
        ensureYouTubeAPI().catch(function () { /* offline or blocked fixture */ });
      }
    };
    if (document.readyState === 'complete') setTimeout(warmAPI, 120);
    else window.addEventListener('load', function () { setTimeout(warmAPI, 120); }, { once: true });
  }

  function extractYouTubeVideoId(embedUrl) {
    var url = parseYouTubeEmbed(embedUrl);
    return url?.pathname.match(/^\/embed\/([A-Za-z0-9_-]{11})\/?$/)?.[1] || null;
  }

  function parseYouTubeEmbed(embedUrl) {
    if (!embedUrl) return null;
    try {
      var url = new URL(embedUrl);
      return url.protocol === 'https:' && !url.port && !url.username && !url.password &&
        YOUTUBE_HOSTS.includes(url.hostname) ? url : null;
    } catch (e) {
      return null;
    }
  }

  function destroyYTPlayer() {
    ytReady = false;
    ytHost = null;
    ytActiveGeneration = 0;
    ytActiveVideoId = null;
    if (ytPlayer) {
      try { ytPlayer.destroy(); } catch (e) { /* already destroyed */ }
      ytPlayer = null;
    }
  }

  function clearPlaybackTimers() {
    clearTimeout(playbackTimer);
    clearTimeout(startGuardTimer);
    clearTimeout(autoSkipTimer);
    playbackTimer = null;
    startGuardTimer = null;
    autoSkipTimer = null;
  }

  function resetPlayback(keepYouTubeInstance) {
    renderGeneration += 1;
    memberMotionCleanup?.();
    memberMotionCleanup = null;
    memberAnimation?.destroy();
    memberAnimation = null;
    mutedAutoplayRetryUsed = false;
    clearPlaybackTimers();
    playbackStatus = null;
    if (!keepYouTubeInstance) {
      var nativeMedia = stage?.querySelector('video');
      if (nativeMedia) {
        nativeMedia.pause();
        nativeMedia.removeAttribute('src');
        nativeMedia.load();
      }
      requestYouTubePlay = null;
      destroyYTPlayer();
      stage.replaceChildren();
    }
    if (playBtn) playBtn.hidden = true;
    if (statusEl) {
      statusEl.hidden = true;
      statusEl.textContent = '';
    }
  }

  function currentModeName() {
    if (!isOpen) return 'closed';
    if (mallHidden) return 'mall';
    if (theater) return 'theater';
    if (wikitube) return 'wikitube';
    if (floating) return tucked ? 'tucked' : 'floating';
    return 'full-video';
  }

  function playerFocusTarget() {
    if (theater) return stage?.querySelector('iframe') || topBar?.querySelector('[data-action="back"]');
    if (floating || wikitube || container?.classList.contains('video-player-full-video')) return gestureGrip;
    return topBar?.querySelector('[data-action="back"]');
  }

  function updateFrameGripLabel() {
    if (!gestureGrip) return;
    var label = floating ? 'Video controls; drag to move, swipe right to hide' : 'Video controls; pinch to change view';
    if (container?.classList.contains('video-player-full-video')) {
      var action = videoOptions().fullVideoSwipeRight || 'next';
      if (action !== 'none') label = 'Video controls; swipe right for ' + (action === 'previous' ? 'previous' : 'next') + ' video';
    }
    gestureGrip.setAttribute('aria-label', label);
    gestureGrip.title = label;
  }

  function videoOptions() {
    return window.mallStateRestore?.getVideoOptions?.() || {
      autoplayNext: true, frameDestination: 'wikitube', collapseDestination: 'mall', revealSelectedPlayer: true,
      tileTapDestination: 'floating', pinchOutDestination: 'wikitube',
      fullVideoSwipeRight: 'next', tuckedSwipeRight: 'next-hidden'
    };
  }

  function updateTuckHandleLabel() {
    if (!tuckHandle) return;
    var title = currentQueue[currentIndex]?.title || 'video';
    var playing = playbackStatus?.state === 'playing';
    tuckHandle.classList.toggle('is-playing', playing);
    tuckHandle.setAttribute('aria-label', 'Restore player · ' + title);
  }

  function reportYouTube(state, message, code, providerState) {
    var video = currentQueue[currentIndex];
    playbackStatus = {
      provider: 'youtube',
      state: state,
      videoId: video?.video_id || video?.videoId || video?.id || null,
      mode: currentModeName(),
      tucked: tucked,
      queueHalted: queueHalted
    };
    if (code !== undefined) playbackStatus.code = code;
    if (providerState !== undefined) playbackStatus.providerState = providerState;
    statusEl.textContent = state === 'paused' ? '' : message || '';
    statusEl.hidden = !statusEl.textContent;
    var needsPlayButton = ['manual-play', 'autoplay-blocked', 'provider-unknown'].includes(state);
    playBtn.hidden = !requestYouTubePlay || !needsPlayButton;
    updateTuckHandleLabel();
    syncFloatingGeometry();
    if (state !== 'playing') {
      container.classList.remove('chrome-hidden');
      clearTimeout(chromeTimer);
    }
    window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: { ...playbackStatus } }));
  }

  function reportHTML5(state, message, code) {
    var video = currentQueue[currentIndex];
    playbackStatus = {
      provider: memberAnimation ? 'image-animation' : 'html5',
      state: state,
      videoId: video?.video_id || video?.videoId || video?.id || null,
      mode: currentModeName(),
      tucked: tucked,
      queueHalted: queueHalted
    };
    if (code != null) playbackStatus.nativeErrorCode = code;
    if (memberAnimation) {
      playbackStatus.fallback = 'approved-animated-webp';
      playbackStatus.nativeErrorCode = 4;
    }
    statusEl.textContent = state === 'paused' ? '' : message || '';
    statusEl.hidden = !statusEl.textContent;
    playBtn.hidden = !['manual-play', 'autoplay-blocked', 'playback-error'].includes(state);
    updateTuckHandleLabel();
    syncFloatingGeometry();
    window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: { ...playbackStatus } }));
  }

  function getPlaybackSnapshot() {
    if (!playbackStatus) return null;
    var positionSeconds = null;
    try {
      if (playbackStatus.provider === 'youtube') {
        var time = ytPlayer?.getCurrentTime?.();
        if (Number.isFinite(time)) positionSeconds = time;
      } else {
        var ve = stage?.querySelector('video');
        if (ve && Number.isFinite(ve.currentTime)) positionSeconds = ve.currentTime;
      }
    } catch (e) { /* provider may already be gone */ }
    return {
      ...playbackStatus,
      mode: currentModeName(),
      tucked: tucked,
      queueIndex: currentIndex,
      queueLength: currentQueue.length,
      queueHalted: queueHalted,
      failedIndices: Array.from(failedQueueIndices),
      positionSeconds: positionSeconds
    };
  }

  function pausePlayback() {
    playbackIntentEpoch++;
    autoplayRequested = false;
    clearPlaybackTimers();
    try { ytPlayer?.pauseVideo?.(); } catch (e) { /* provider not ready */ }
    stage?.querySelector('video')?.pause();
    memberAnimation?.pause();
  }

  function playNativeMedia() {
    if (memberAnimation) { memberAnimation.play(); return Promise.resolve(); }
    return stage?.querySelector('video')?.play();
  }

  function displayedMediaArea() {
    if (!isOpen || mallHidden || tucked || document.hidden || !stage?.isConnected ||
        !container.classList.contains('open')) return null;
    var style = window.getComputedStyle(container);
    if (style.display === 'none' || style.visibility === 'hidden') return null;
    var rect = stage.getBoundingClientRect();
    var bounds = container.classList.contains('video-player-queue-docked') && mediaPanel.getBoundingClientRect();
    var width = Math.max(0, Math.min(rect.right, window.innerWidth, bounds?.right ?? Infinity) -
      Math.max(rect.left, 0, bounds?.left ?? 0));
    var height = Math.max(0, Math.min(rect.bottom, window.innerHeight, bounds?.bottom ?? Infinity) -
      Math.max(rect.top, 0, bounds?.top ?? 0));
    return { rect: rect, area: width * height };
  }

  function isPlaybackDisplayed() {
    var view = displayedMediaArea();
    return !!view && view.rect.width >= 200 && view.rect.height >= 200 && view.area > 0;
  }

  function pauseHiddenPlayback() {
    if (!isOpen || isPlaybackDisplayed()) return;
    // Repeated geometry observations are not fresh Pause intent. Keep a
    // catalog-only hidden Next request valid once its provider is stopped.
    if (!autoplayRequested) {
      try {
        if (ytPlayer && [2, 5, -1].includes(ytPlayer.getPlayerState?.())) return;
      } catch (error) { /* Unknown provider state still takes the pause path. */ }
      var media = stage?.querySelector('video');
      if (!memberAnimation?.isPlaying() && !stage?.querySelector('iframe') && (!media || media.paused)) return;
    }
    pausePlayback();
  }

  function normalizeResumeSeconds(sec, durationSec) {
    if (sec == null || typeof sec !== 'number' || isNaN(sec)) return null;
    if (sec < MIN_RESUME_SECONDS) return null;
    var dur = typeof durationSec === 'number' && durationSec > 0 ? durationSec : 0;
    if (dur > 0 && sec >= dur * COMPLETE_RATIO) return null;
    return Math.round(sec * 10) / 10;
  }

  function mergeHistoryResume(foundupId, video, positionSec, durationSec) {
    var videoId = video && (video.video_id || video.videoId || video.id || '');
    if (!foundupId || !videoId || !video) return;
    var pos = normalizeResumeSeconds(positionSec, durationSec);
    var history = getWatchHistory();
    var changed = false;
    for (var i = 0; i < history.length; i++) {
      if (history[i].foundupId === foundupId && history[i].videoId === videoId) {
        if (pos == null) {
          if ('playbackPosition' in history[i]) {
            delete history[i].playbackPosition;
            changed = true;
          }
        } else if (history[i].playbackPosition !== pos) {
          history[i].playbackPosition = pos;
          changed = true;
        }
        break;
      }
    }
    if (changed) setWatchHistory(history);
  }

  function flushCurrentPlaybackPosition() {
    if (!isOpen || currentIndex < 0 || !currentFoundUpId || !stage) return;
    var video = currentQueue[currentIndex];
    if (!video) return;
    if (video.embed_url || video.embedUrl) return;
    var vid = stage.querySelector('video');
    if (!vid) return;
    var t = vid.currentTime;
    var d = vid.duration;
    if (!isFinite(t)) t = 0;
    if (!isFinite(d)) d = 0;
    mergeHistoryResume(currentFoundUpId, video, t, d);
  }

  // ─── Layout & Floating Clearance Sync ───
  function syncFloatingGeometry() {
    if (typeof document === 'undefined') return;
    var root = document.documentElement;
    if (!isOpen || mallHidden || (!floating && !theater)) {
      root.style.removeProperty('--floating-player-clearance');
      root.removeAttribute('data-floating-player');
      return;
    }
    var header = document.querySelector('.mall-header');
    var headerBottom = header && header.offsetParent !== null
      ? Math.max(0, Math.round(header.getBoundingClientRect().bottom))
      : 0;
    if (theater) {
      container.style.setProperty('--theater-top', (headerBottom ? headerBottom + 6 : 12) + 'px');
      root.style.removeProperty('--floating-player-clearance');
      root.removeAttribute('data-floating-player');
      return;
    }
    var topPx = Math.max(8, headerBottom ? headerBottom + 6 : 8);
    if (floatingPosition) {
      var viewport = window.visualViewport;
      var left = viewport?.offsetLeft || 0;
      var viewportTop = viewport?.offsetTop || 0;
      var width = viewport?.width || window.innerWidth;
      var height = viewport?.height || window.innerHeight;
      var box = container.getBoundingClientRect();
      var dock = document.querySelector('.mall-member-search-dock:not([hidden])');
      var dockBox = dock?.getBoundingClientRect();
      var bottom = dockBox && dockBox.height ? Math.min(viewportTop + height - 8, dockBox.top - 8) : viewportTop + height - 8;
      floatingPosition.x = Math.max(left + 8, Math.min(floatingPosition.x, left + width - box.width - 8));
      topPx = Math.max(topPx, viewportTop + 8);
      floatingPosition.y = Math.max(topPx, Math.min(floatingPosition.y, bottom - box.height));
      topPx = floatingPosition.y;
      container.style.setProperty('--floating-left', floatingPosition.x + 'px');
      container.classList.add('has-floating-position');
    }
    container.style.setProperty('--floating-top', topPx + 'px');
    if (tuckHandle) {
      tuckHandle.style.setProperty('--floating-top', topPx + 'px');
      tuckHandle.style.setProperty('--floating-height', container.getBoundingClientRect().height + 'px');
    }
    root.setAttribute('data-floating-player', tucked ? 'tucked' : 'open');
    if (tucked) {
      root.style.setProperty('--floating-player-clearance', '0px');
      return;
    }
    var wrapper = document.querySelector('.mall-tile-field-wrapper');
    var isLandscapeCompact = floatingLandscapeQuery
      ? floatingLandscapeQuery.matches
      : window.innerWidth > window.innerHeight && window.innerHeight <= 500;
    if (!wrapper || isLandscapeCompact) {
      root.style.setProperty('--floating-player-clearance', '0px');
      return;
    }
    var wrapperRect = wrapper.getBoundingClientRect();
    var playerRect = container.getBoundingClientRect();
    var overlap = Math.max(0, Math.round(playerRect.bottom - wrapperRect.top + 8));
    root.style.setProperty('--floating-player-clearance', overlap + 'px');
  }

  // ─── Initialize DOM ───
  function ensureDOM() {
    if (container) return;

    container = document.createElement('div');
    container.id = 'videoPlayerFullscreen';
    container.className = 'video-player-fullscreen';
    container.setAttribute('aria-label', 'WikiTube video player');
    container.setAttribute('role', 'dialog');
    container.innerHTML = [
      '<div class="video-player-top-bar">',
      '  <div class="video-player-top-bar-left">',
      '    <button type="button" class="video-player-btn" data-action="back" aria-label="Back">',
      '      <svg viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>',
      '    </button>',
      '    <div class="video-player-caption">',
      '      <span class="video-player-title"></span>',
      '      <a class="video-player-source" target="_blank" rel="noopener noreferrer" hidden></a>',
      '    </div>',
      '  </div>',
      '  <div class="video-player-top-bar-right">',
      '    <button type="button" class="video-player-btn" data-action="prev" aria-label="Previous video" title="Previous video" hidden>',
      '      <svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="next" aria-label="Next video" title="Next video" hidden>',
      '      <svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="tuck" aria-label="Tuck player" title="Tuck to edge" hidden>',
      '      <svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/><path d="M19 5v14"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="float" aria-label="Floating player" title="Minimize to floating player" hidden>',
      '      <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><rect x="11" y="6" width="8" height="6" rx="1" fill="currentColor"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="expand" aria-label="Open WikiTube" title="Open WikiTube" hidden>',
      '      <svg viewBox="0 0 24 24"><path d="M14 4h6v6m0-6-6 6M10 20H4v-6m0 6 6-6"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn video-player-enter-btn" data-action="enter" aria-label="Enter FoundUp">',
      '      <svg viewBox="0 0 24 24"><path d="M15 3h6v6M14 10l6.1-6.1M9 21H3v-6M10 14l-6.1 6.1"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="save" aria-label="Save">',
      '      <svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="share" aria-label="Share">',
      '      <svg viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/></svg>',
      '    </button>',
      '    <button type="button" class="video-player-btn" data-action="more" aria-label="More options">',
      '      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>',
      '    </button>',
      '  </div>',
      '</div>',
      '<div class="video-player-stage"></div>',
      '<p class="video-player-status" role="status" hidden></p>',
      '<button class="video-player-manual-play" type="button" hidden>Play video</button>',
      '<form class="video-player-queue-search" role="search" hidden>',
      '  <input type="search" aria-label="Search videos" placeholder="Search videos" maxlength="300">',
      '  <button type="submit" aria-label="Play search result" title="Play search result">',
      '    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 4.5 4.5"/></svg>',
      '  </button>',
      '</form>',
      '<div class="video-player-edge-trigger"></div>',
      '<div class="video-player-queue-rail">',
      '  <div class="video-player-queue-track"></div>',
      '  <p class="video-player-queue-empty" role="status" hidden>No videos match your search.</p>',
      '</div>',
      '<div class="video-player-gesture-hint"></div>'
    ].join('\n');

    document.body.appendChild(container);

    tuckHandle = document.createElement('button');
    tuckHandle.type = 'button';
    tuckHandle.className = 'video-player-tuck-handle';
    tuckHandle.setAttribute('aria-label', 'Restore player');
    tuckHandle.title = 'Restore player';
    tuckHandle.hidden = true;
    tuckHandle.innerHTML = [
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 6-6 6 6 6"/></svg>',
      '<span class="video-player-tuck-bars" aria-hidden="true"><span></span><span></span><span></span></span>'
    ].join('');
    document.body.appendChild(tuckHandle);

    stage = container.querySelector('.video-player-stage');
    statusEl = container.querySelector('.video-player-status');
    playBtn = container.querySelector('.video-player-manual-play');
    playBtn.addEventListener('click', function () {
      autoplayRequested = true;
      queueHalted = false;
      if (requestYouTubePlay) {
        requestYouTubePlay();
      } else {
        playNativeMedia()?.catch(function () { reportHTML5('autoplay-blocked', 'Tap inside the video to start playback.'); });
      }
    });
    topBar = container.querySelector('.video-player-top-bar');
    queueRail = container.querySelector('.video-player-queue-rail');
    queueTrack = container.querySelector('.video-player-queue-track');
    queueSearchForm = container.querySelector('.video-player-queue-search');
    queueSearch = queueSearchForm.querySelector('input');
    queueSearchForm.addEventListener('submit', playSearchResult);
    queueEmpty = container.querySelector('.video-player-queue-empty');
    queueSearch.addEventListener('input', filterRail);
    edgeTrigger = container.querySelector('.video-player-edge-trigger');
    gestureHint = container.querySelector('.video-player-gesture-hint');
    titleEl = container.querySelector('.video-player-title');
    saveBtn = container.querySelector('[data-action="save"]');

    mediaPanel = document.createElement('div');
    mediaPanel.className = 'video-player-media-panel';
    topBar.before(mediaPanel);
    gestureGrip = document.createElement('div');
    gestureGrip.className = 'video-player-gesture-grip';
    gestureGrip.setAttribute('role', 'button');
    gestureGrip.tabIndex = 0;
    gestureGrip.setAttribute('aria-label', 'Video controls; drag to move, swipe right to hide');
    gestureGrip.title = 'Video controls · drag to move · swipe right to hide';
    var stageFrame = document.createElement('div');
    stageFrame.className = 'video-player-stage-frame';
    var dragSides = ['right'].map(function (side) {
      var rail = document.createElement('div');
      rail.className = 'video-player-gesture-side';
      rail.dataset.side = side;
      rail.setAttribute('aria-hidden', 'true');
      return rail;
    });
    // The visible grip is on the left so a right-swipe has usable travel inside
    // the viewport. The tucked restore rail remains at the right screen edge.
    stageFrame.append(gestureGrip, stage, dragSides[0]);
    mediaPanel.append(topBar, stageFrame, statusEl, playBtn);
    gestureGrip.addEventListener('click', function () {
      if (!suppressNextClick && performance.now() >= gestureClickBlockedUntil) { gestureGrip.focus({ preventScroll: true }); openVideoControls(); }
    });
    gestureGrip.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault(); event.stopPropagation(); openVideoControls();
      } else if (floating && /^Arrow(Left|Right|Up|Down)$/.test(event.key)) {
        event.preventDefault(); event.stopPropagation();
        var rect = container.getBoundingClientRect();
        floatingPosition = { x: rect.left + (event.key === 'ArrowRight' ? 12 : event.key === 'ArrowLeft' ? -12 : 0),
          y: rect.top + (event.key === 'ArrowDown' ? 12 : event.key === 'ArrowUp' ? -12 : 0) };
        syncFloatingGeometry();
      }
    });
    [gestureGrip].concat(dragSides).forEach(bindFloatingDrag);

    memberQueueDock = window.mallVideoProjection?.createMemberDock?.(
      'Search this queue',
      playMemberSearchResult,
      function () {
        if (scopedPlayer) return window.mallVideoProjection?.openScopedRedDog?.(currentFoundUpId);
        close();
        window.redDog?.open?.();
        document.querySelector('#accountPlane.open button:not([hidden])')?.focus();
      }
    );

    queuePanel = document.createElement('div');
    queuePanel.className = 'video-player-queue-panel';
    queueRail.before(queuePanel);
    queuePanel.append(queueRail);

    if (memberQueueDock) {
      memberQueueDock.element.hidden = true;
      memberQueueDock.input.addEventListener('input', filterRail);
      memberQueueDock.input.addEventListener('change', filterRail);
      queuePanel.prepend(memberQueueDock.element);
      var viewport = window.visualViewport;
      if (viewport) {
        viewport.addEventListener('resize', alignQueueKeyboard);
        viewport.addEventListener('scroll', alignQueueKeyboard);
        memberQueueDock.input.addEventListener('focus', alignQueueKeyboard);
        memberQueueDock.input.addEventListener('blur', alignQueueKeyboard);
      }
    }

    topBar.addEventListener('click', handleTopBarClick);
    queueTrack.addEventListener('click', handleRailClick);
    edgeTrigger.addEventListener('touchstart', showRail, { passive: true });
    edgeTrigger.addEventListener('mouseenter', showRail);

    bindPlayerGestures();
    bindTuckHandleGestures();

    window.addEventListener('resize', function () {
      if (isOpen) {
        syncFloatingGeometry();
        pauseHiddenPlayback();
      }
    });
    window.visualViewport?.addEventListener('resize', syncFloatingGeometry);
    window.visualViewport?.addEventListener('scroll', syncFloatingGeometry);
    // Follow the same breakpoint as the floating-player and selected-grid CSS.
    // Its change event updates geometry when the responsive mode changes, even
    // when window resize/box observation is delivered later by WebKit.
    if (typeof window.matchMedia === 'function') {
      floatingLandscapeQuery = window.matchMedia('(orientation: landscape) and (max-height: 500px)');
      floatingLandscapeQuery.addEventListener('change', function () {
        if (isOpen && (floating || theater)) syncFloatingGeometry();
      });
    }
    // Responsive boxes can settle after the window resize event (notably on
    // WebKit rotation). Re-measure the existing layout without restarting media.
    // Observe only the header/player; grid padding is an output, not an input.
    if (typeof ResizeObserver !== 'undefined') {
      var geometryObserver = new ResizeObserver(function () {
        if (isOpen && (floating || theater)) syncFloatingGeometry();
      });
      geometryObserver.observe(container);
      var floatingHeader = document.querySelector('.mall-header');
      if (floatingHeader) geometryObserver.observe(floatingHeader);
    }
    // One event-driven media visibility observer; chrome/rail timers stay separate.
    if (typeof IntersectionObserver !== 'undefined') {
      new IntersectionObserver(pauseHiddenPlayback, { threshold: [0, 0.5] }).observe(stage);
    }

    // Keyboard: dismiss innermost control before shell Escape handler
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !isOpen || mallHidden || e.isComposing) return;
      // The active native dialog owns its own Escape/cancel lifecycle.
      if (e.target?.closest?.('dialog[open]')) return;
      var cardBack = e.target?.closest?.('.mall-card-back');
      if (cardBack && !cardBack.hidden && !cardBack.inert) return;
      if (memberQueueDock?.dialog.open) {
        e.preventDefault();
        e.stopPropagation();
        memberQueueDock.dialog.close();
        return;
      }
      if (memberQueueDock && !memberQueueDock.element.hidden && e.target === memberQueueDock.input) {
        e.preventDefault();
        e.stopPropagation();
        memberQueueDock.input.blur();
        playerFocusTarget()?.focus({ preventScroll: true });
        return;
      }
      if (wikitube || (memberQueueDock && !memberQueueDock.element.hidden)) {
        e.preventDefault();
        e.stopPropagation();
        close();
        return;
      }
      if (floating) {
        e.preventDefault();
        e.stopPropagation();
        close();
        return;
      }
      if (returnTile && !scopedPlayer) handleKeydown(e);
    }, true);

    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('visibilitychange', function () {
      if (isOpen && document.hidden) pausePlayback();
    });
    window.addEventListener('pagehide', function (event) {
      if (!isOpen) return;
      flushCurrentPlaybackPosition();
      pausePlayback();
      if (!event.persisted) close({ restore: false });
    });
  }

  function alignQueueKeyboard() {
    var viewport = window.visualViewport;
    var keyboard = viewport && memberQueueDock?.element.contains(document.activeElement) && viewport.scale === 1
      ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
    container.style.setProperty('--video-player-keyboard', keyboard + 'px');
  }

  // Loan the existing shared dock on phone and desktop, including scoped TV. The
  // mounted provider and player stage never move.
  function borrowScopedPhoneDock() {
    if (scopedDockLoan || !matchesQuery) return;
    var dock = window.mallVideoProjection?.getScopedPhoneDock?.(currentFoundUpId, { includeDesktop: true });
    if (!dock?.useSearchContext || !dock.element.isConnected) return;
    var marker = document.createComment('scoped phone dock return');
    var host = document.createElement('div');
    host.className = 'video-player-shared-dock-host';
    dock.element.before(marker);
    var hidden = dock.element.hidden;
    dock.hide();
    memberQueueDock?.hide();
    scopedDockLoan = { dock: dock, marker: marker, host: host, hidden: hidden, previous: memberQueueDock,
      restoreContext: dock.useSearchContext(function () {
        if (theater) playSearchResult();
        else playMemberSearchResult();
      }, 'Search this queue', theater ? queueSearch.value : scopedQueueQuery) };
    memberQueueDock = dock;
    dock.input.addEventListener('input', filterRail);
    dock.input.addEventListener('change', filterRail);
    dock.input.addEventListener('focus', alignQueueKeyboard);
    dock.input.addEventListener('blur', alignQueueKeyboard);
    host.append(dock.element);
    container.append(host);
    dock.element.hidden = false;
    alignQueueKeyboard();
  }

  function restoreScopedPhoneDock() {
    if (!scopedDockLoan) return;
    var loan = scopedDockLoan;
    scopedQueueQuery = loan.dock.input.value.trim().slice(0, 300);
    loan.dock.hide();
    loan.dock.input.removeEventListener('input', filterRail);
    loan.dock.input.removeEventListener('change', filterRail);
    loan.dock.input.removeEventListener('focus', alignQueueKeyboard);
    loan.dock.input.removeEventListener('blur', alignQueueKeyboard);
    loan.marker.replaceWith(loan.dock.element);
    loan.restoreContext();
    loan.dock.element.hidden = loan.hidden || (loan.dock.element.id === 'videoScopePhoneDock' &&
      !window.mallVideoProjection?.isPhoneDockLayout?.());
    loan.dock.fitInput?.();
    loan.host.remove();
    memberQueueDock = loan.previous;
    if (memberQueueDock) memberQueueDock.setValue(scopedQueueQuery);
    scopedDockLoan = null;
    alignQueueKeyboard();
  }

  // ─── Mode Transitions (provider DOM stays mounted) ───
  function releaseModalInert() {
    restoreScopedPhoneDock();
    if (previousOverflow !== null) {
      document.body.style.overflow = previousOverflow;
      previousOverflow = null;
    }
    inertElements.forEach(function (element) { element.inert = false; });
    inertElements = [];
    container.removeAttribute('aria-modal');
  }

  function currentEntryId() {
    var item = window.mallTileField?.getCatalog?.().find(function (entry) {
      return (entry.foundup_id || entry.id) === currentFoundUpId;
    });
    if (item) {
      currentEntryIdentity = window.mallVideoProjection?.canonicalEntryId
        ? window.mallVideoProjection.canonicalEntryId(item)
        : (Object.prototype.hasOwnProperty.call(item, 'canonical_foundup_id') ? item.canonical_foundup_id : currentFoundUpId);
    }
    // A filtered-out active lane retains its explicit null or canonical alias.
    if (currentEntryIdentity !== undefined) return currentEntryIdentity;
    return window.mallVideoProjection?.isOpenMallHost?.(window.location) ? null : currentFoundUpId;
  }

  function syncTopBarButtons() {
    var backBtn = topBar.querySelector('[data-action="back"]');
    var expandBtn = topBar.querySelector('[data-action="expand"]');
    var tuckBtn = topBar.querySelector('[data-action="tuck"]');
    var floatBtn = topBar.querySelector('[data-action="float"]');
    var prevBtn = topBar.querySelector('[data-action="prev"]');
    var nextBtn = topBar.querySelector('[data-action="next"]');
    var hasMultiQueue = currentQueue.length > 1;
    topBar.querySelector('[data-action="enter"]').hidden = scopedPlayer || !currentEntryId();

    if (theater) {
      backBtn.hidden = true;
      expandBtn.hidden = true;
      tuckBtn.hidden = true;
      floatBtn.hidden = true;
      prevBtn.hidden = true;
      nextBtn.hidden = true;
    } else if (floating) {
      backBtn.hidden = false;
      backBtn.setAttribute('aria-label', 'Close player');
      backBtn.title = 'Close player';
      expandBtn.hidden = false;
      var destination = videoOptions().frameDestination === 'full-video' ? 'Open Full Video' : 'Open WikiTube';
      expandBtn.setAttribute('aria-label', destination);
      expandBtn.title = destination;
      tuckBtn.hidden = false;
      floatBtn.hidden = true;
      prevBtn.hidden = true;
      nextBtn.hidden = true;
    } else {
      // WikiTube fullscreen mode
      backBtn.hidden = false;
      backBtn.setAttribute('aria-label', 'Back');
      backBtn.title = 'Return to grid';
      expandBtn.hidden = true;
      tuckBtn.hidden = true;
      floatBtn.hidden = false;
      floatBtn.setAttribute('aria-label', !wikitube && videoOptions().collapseDestination === 'wikitube'
        ? 'Collapse to WikiTube' : 'Return to Mall');
      prevBtn.hidden = !hasMultiQueue;
      nextBtn.hidden = !hasMultiQueue;
    }
    updateFrameGripLabel();
  }

  function applyFloatingPresentation() {
    releaseModalInert();
    untuck({ silent: true });
    inline = true;
    floating = true;
    theater = false;
    wikitube = false;
    container.classList.add('video-player-inline', 'video-player-floating');
    container.classList.remove('video-player-theater', 'video-player-wikitube', 'video-player-queue-docked', 'chrome-hidden');
    container.classList.remove('video-player-full-video');
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'Floating video player');
    queueSearchForm.hidden = true;
    memberQueueDock?.hide();
    clearTimeout(chromeTimer);
    syncTopBarButtons();
    syncFloatingGeometry();
  }

  function applyWikiTubePresentation(attemptImmediatePlay, fullVideo) {
    untuck({ silent: true });
    inline = false;
    floating = false;
    theater = false;
    wikitube = fullVideo !== true;
    container.classList.remove('video-player-inline', 'video-player-floating', 'video-player-theater', 'chrome-hidden');
    container.classList.toggle('video-player-wikitube', wikitube);
    container.classList.toggle('video-player-full-video', fullVideo === true);
    queuePanel.hidden = false;
    container.setAttribute('role', 'dialog');
    container.setAttribute('aria-label', fullVideo === true ? 'Full Video in app' : 'WikiTube video player');
    queueSearchForm.hidden = true;

    if (previousOverflow === null) previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Keep the one phone dock actionable inside the modal's inert boundary.
    borrowScopedPhoneDock();

    if (returnTile || matchesQuery || currentQueue.length) {
      container.setAttribute('aria-modal', 'true');
      var member = document.getElementById('memberArea');
      if (member && !member.contains(container) && !member.inert) {
        member.inert = true;
        inertElements.push(member);
      }
    }

    if (memberQueueDock && matchesQuery && (!scopedPlayer || memberQueueDock.setScoped)) {
      memberQueueDock.setScoped?.(scopedPlayer);
      memberQueueDock.element.hidden = false;
      memberQueueDock.fitInput?.();
      container.classList.add('video-player-queue-docked');
      filterRail();
    } else {
      renderRail();
      queueRail.classList.add('visible');
    }

    syncTopBarButtons();
    syncFloatingGeometry();
    resetChromeTimer();
    playerFocusTarget()?.focus({ preventScroll: true });

    if (attemptImmediatePlay && playbackStatus?.state !== 'playing' && playbackStatus?.state !== 'starting') {
      autoplayRequested = true;
      queueHalted = false;
      failedQueueIndices.delete(currentIndex);
      if (requestYouTubePlay) {
        requestYouTubePlay();
      } else {
        var ve = stage.querySelector('video');
        if (memberAnimation || (ve && ve.paused)) {
          playNativeMedia()?.catch(function () {
            reportHTML5('autoplay-blocked', 'Tap Play video or tap inside the player to start playback.');
          });
        }
      }
    }
    if (playbackStatus) {
      playbackStatus.mode = currentModeName();
      playbackStatus.tucked = tucked;
    }
    window.dispatchEvent(new CustomEvent('videoPlayerModeChange', {
      detail: { mode: currentModeName(), foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
  }

  function setTheater(enabled, tile) {
    if (!isOpen || mallHidden) return false;
    if (tile) returnTile = tile;
    if (enabled) {
      releaseModalInert();
      untuck({ silent: true });
      inline = true;
      floating = false;
      wikitube = false;
      theater = true;
      queuePanel.hidden = false;
      container.classList.remove('video-player-full-video');
      container.classList.add('video-player-inline', 'video-player-theater');
      container.classList.remove('video-player-floating', 'video-player-wikitube', 'video-player-queue-docked', 'chrome-hidden');
      container.setAttribute('role', 'region');
      container.setAttribute('aria-label', 'Video theater');
      memberQueueDock?.hide();
      borrowScopedPhoneDock();
      container.classList.toggle('video-player-queue-docked', !!scopedDockLoan);
      var active = document.activeElement;
      var back = topBar.querySelector('[data-action="back"]');
      syncTopBarButtons();
      queueSearchForm.hidden = !!scopedDockLoan || !matchesQuery;
      if (active === back) {
        var searchFocus = scopedDockLoan ? memberQueueDock.input : queueSearchForm.hidden ? null : queueSearch;
        searchFocus?.focus({ preventScroll: true });
      }
      filterRail();
      renderRail();
      syncFloatingGeometry();
      return true;
    }
    if (!theater) return false;
    var activeBefore = document.activeElement;
    applyFloatingPresentation();
    if (queueSearchForm.contains(activeBefore) || queueRail.contains(activeBefore)) {
      gestureGrip?.focus({ preventScroll: true });
    }
    return true;
  }

  function openWikiTube() {
    if (!isOpen || mallHidden || wikitube || theater) return false;
    applyWikiTubePresentation(true);
    return true;
  }

  function openFullVideo() {
    if (!isOpen || mallHidden || theater) return false;
    // Reuse the app's existing fixed player, provider frame and inert/focus owner.
    // This never requests or intercepts native YouTube/browser fullscreen.
    applyWikiTubePresentation(true, true);
    return true;
  }

  function openFrameDestination() {
    return videoOptions().frameDestination === 'full-video' ? openFullVideo() : openWikiTube();
  }

  function openPinchDestination() {
    return videoOptions().pinchOutDestination === 'full-video' || wikitube
      ? openFullVideo() : openWikiTube();
  }

  function returnFromGesture(preference) {
    var destination = videoOptions()[preference];
    if (!destination) return pinchReturn();
    if (destination === 'wikitube') {
      if (wikitube) return false;
      applyWikiTubePresentation(false);
      return true;
    }
    return returnToMall();
  }

  function openVideoControls() {
    var dock = window.mallVideoProjection?.getScopedPhoneDock?.(currentFoundUpId, { includeDesktop: true }) || memberQueueDock;
    dock?.showVideoOptions?.();
  }

  function bindFloatingDrag(surface) {
    surface.addEventListener('pointerdown', function (event) {
      if (!event.isPrimary || event.button !== 0 || !isOpen || !floating || tucked) return;
      var rect = container.getBoundingClientRect();
      floatingDrag = { id: event.pointerId, x: event.clientX, y: event.clientY,
        left: rect.left, top: rect.top, time: performance.now(), moved: false };
      surface.setPointerCapture?.(event.pointerId);
    });
    surface.addEventListener('pointermove', function (event) {
      if (!floatingDrag || floatingDrag.id !== event.pointerId || pinchActive || !floating || tucked) return;
      var dx = event.clientX - floatingDrag.x, dy = event.clientY - floatingDrag.y;
      if (Math.abs(dx) + Math.abs(dy) < 6) return;
      event.preventDefault();
      floatingDrag.moved = true;
      floatingPosition = { x: floatingDrag.left + dx, y: floatingDrag.top + dy };
      syncFloatingGeometry();
    });
    function finish(event) {
      if (!floatingDrag || floatingDrag.id !== event.pointerId) return;
      var drag = floatingDrag;
      floatingDrag = null;
      if (drag.moved) {
        suppressNextClick = true;
        setTimeout(function () { suppressNextClick = false; }, 0);
      }
      if (event.type !== 'pointerup' || pinchActive) return;
      var dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (performance.now() - drag.time < 450 && dx >= TUCK_SWIPE_PX && dx > Math.abs(dy) * 1.4) tuck();
      else if (performance.now() - drag.time < 450 && Math.abs(dy) >= 50 && Math.abs(dy) > Math.abs(dx) * 1.3) handlePlayerSwipeEnd(dx, dy, surface);
    }
    surface.addEventListener('pointerup', finish);
    surface.addEventListener('pointercancel', finish);
    surface.addEventListener('lostpointercapture', function () { floatingDrag = null; });
  }

  function collapseAppVideo() {
    if (!isOpen || mallHidden) return false;
    if (container.classList.contains('video-player-full-video')) {
      if (videoOptions().collapseDestination === 'wikitube') {
        applyWikiTubePresentation(false);
        return true;
      }
      return returnToMall();
    }
    return returnToMall();
  }

  function returnToMall(options) {
    if (!isOpen || mallHidden) return false;
    flushCurrentPlaybackPosition();
    var frame = stage.querySelector('iframe');
    // An opaque provider (or a YouTube frame before its pause API is ready)
    // cannot be kept hidden with a promise that its audio has stopped.
    var retainProvider = !frame || (container.classList.contains('provider-youtube') && ytReady &&
      typeof ytPlayer?.pauseVideo === 'function');
    var unavailable = !retainProvider ? {
      provider: 'unsupported', state: 'continuity-unavailable', mode: 'closed', retained: false,
      foundupId: currentFoundUpId, videoId: getPlaybackSnapshot()?.videoId || currentQueue[currentIndex]?.video_id || null,
      message: 'This provider cannot be paused safely in the Mall. Its player was closed; select the tile to reopen it.'
    } : null;
    mallReturnMode = currentModeName();
    // Set the guard before the field renders its caller. A render must not
    // mistake the retained session for a discarded inline player.
    mallHidden = true;
    pausePlayback();
    // Remove unsupported frames before hiding any surface. Retention is refused
    // rather than leaving an unobservable player running behind the Mall.
    if (!retainProvider) resetPlayback(false);
    clearTimeout(chromeTimer);
    clearTimeout(railTimer);
    untuck({ silent: true });
    container.classList.add('video-player-mall');
    container.hidden = true;
    container.inert = true;
    container.setAttribute('aria-hidden', 'true');
    memberQueueDock?.hide();
    releaseModalInert();
    syncFloatingGeometry();
    var caller = onReturnToMall?.(options || {});
    if (caller === false) {
      // The source owner changed generation; a stale caller is not a successful
      // return. Dispose of its resources rather than focus a positional tile.
      close({ restore: false });
      return false;
    }
    if (caller?.nodeType === 1) returnTile = caller;
    if (!onReturnToMall && returnTile?.isConnected) returnTile.focus({ preventScroll: true });
    if (!retainProvider) {
      close({ restore: false, dismissPlayback: true });
      window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: unavailable }));
      return false;
    }
    if (playbackStatus) playbackStatus.mode = 'mall';
    window.dispatchEvent(new CustomEvent('videoPlayerModeChange', {
      detail: { mode: 'mall', foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
    return true;
  }

  function resumeFromMall(options) {
    if (!isOpen || !mallHidden) return false;
    // The field validates identity/generation and restores its selected lane
    // while the player is still hidden. Missing callers never select by index.
    var caller = onResumeFromMall?.(options || {});
    if (caller === false) return false;
    if (caller?.nodeType === 1) returnTile = caller;
    var destination = options?.tileActivation ? videoOptions().tileTapDestination : mallReturnMode;
    mallHidden = false;
    container.classList.remove('video-player-mall');
    container.hidden = false;
    container.inert = false;
    container.removeAttribute('aria-hidden');
    if (destination === 'theater') setTheater(true, returnTile);
    else if (destination === 'full-video') applyWikiTubePresentation(false, true);
    else if (destination === 'wikitube') applyWikiTubePresentation(false);
    else applyFloatingPresentation();
    materializeHiddenSelection();
    refreshQueue();
    // Browser Forward is a paused restoration. An intentional selection may
    // play through the existing provider guard, without reloading the iframe.
    autoplayRequested = options?.autoplay === true;
    if (autoplayRequested) {
      if (requestYouTubePlay) requestYouTubePlay();
      else playNativeMedia()?.catch(function() {});
    }
    if (playbackStatus) playbackStatus.mode = currentModeName();
    window.dispatchEvent(new CustomEvent('videoPlayerModeChange', {
      detail: { mode: currentModeName(), foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
    return true;
  }

  function expandInline() {
    return openWikiTube();
  }

  function collapseToFloating() {
    if (!isOpen || mallHidden || (!wikitube && !container.classList.contains('video-player-full-video'))) return false;
    applyFloatingPresentation();
    gestureGrip?.focus({ preventScroll: true });
    if (playbackStatus) {
      playbackStatus.mode = currentModeName();
      playbackStatus.tucked = tucked;
    }
    window.dispatchEvent(new CustomEvent('videoPlayerModeChange', {
      detail: { mode: 'floating', foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
    return true;
  }

  // ─── Tuck & Restore (Floating Player Edge Dock) ───
  function tuck() {
    if (!isOpen || mallHidden || !floating || tucked) return false;
    tucked = true;
    pausePlayback();
    container.classList.add('is-tucked');
    tuckHandle.hidden = false;
    updateTuckHandleLabel();
    syncFloatingGeometry();
    tuckHandle.focus({ preventScroll: true });
    container.inert = true;
    container.setAttribute('aria-hidden', 'true');
    if (playbackStatus) {
      playbackStatus.mode = currentModeName();
      playbackStatus.tucked = true;
    }
    window.dispatchEvent(new CustomEvent('videoPlayerTuck', {
      detail: { tucked: true, foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
    return true;
  }

  function untuck(opts) {
    if (!tucked) {
      if (tuckHandle) tuckHandle.hidden = true;
      container?.classList.remove('is-tucked');
      return false;
    }
    var focusInsideHandle = document.activeElement === tuckHandle;
    if (opts?.immediate) {
      container.classList.add('player-reveal-immediate');
      requestAnimationFrame(function () { container?.classList.remove('player-reveal-immediate'); });
    }
    tucked = false;
    container.classList.remove('is-tucked');
    container.inert = false;
    container.removeAttribute('aria-hidden');
    tuckHandle.hidden = true;
    syncFloatingGeometry();
    materializeHiddenSelection();
    if (!opts?.silent && focusInsideHandle) {
      gestureGrip?.focus({ preventScroll: true });
    }
    if (playbackStatus) {
      playbackStatus.mode = currentModeName();
      playbackStatus.tucked = false;
    }
    if (!opts?.silent) {
      window.dispatchEvent(new CustomEvent('videoPlayerTuck', {
        detail: { tucked: false, foundupId: currentFoundUpId, videoIndex: currentIndex }
      }));
    }
    return true;
  }

  function materializeHiddenSelection() {
    if (!hiddenSelectionPending || !isOpen || mallHidden || tucked) return;
    hiddenSelectionPending = false;
    autoplayRequested = false;
    renderVideo(currentQueue[currentIndex], false);
    recordWatch(currentFoundUpId, currentQueue[currentIndex], currentIndex);
  }

  // ─── Open or Switch Selected Media ───
  function open(foundupId, queue, startIndex, resumeOpts) {
    if (!queue || !queue.length) return;
    ensureDOM();
    // Account/history callers use this public entry directly, without field
    // activation options. Validate and restore a hidden caller before changing
    // callbacks or presentation; failed continuity becomes a fresh visible open.
    var resumedHiddenSession = false;
    if (mallHidden) {
      if (currentFoundUpId === foundupId && resumeOpts?.preserveInstance !== false) {
        resumedHiddenSession = resumeFromMall({ autoplay: false });
      }
      if (!resumedHiddenSession) close({ restore: false });
    }
    if (foundupId !== currentFoundUpId) currentEntryIdentity = undefined;

    var targetIndex = Math.max(0, Math.min(startIndex || 0, queue.length - 1));
    var tileActivation = resumeOpts?.tileActivation === true;
    var preferences = videoOptions();
    var tileDestination = ['floating', 'wikitube', 'full-video'].indexOf(preferences.tileTapDestination) !== -1
      ? preferences.tileTapDestination : 'floating';
    var wantTheater = !tileActivation && resumeOpts?.theater === true;
    // Field activation is distinct from queue selection, automatic startup and
    // frame actions. Keep a deliberately parked player parked before applying it.
    var keepParked = tucked && preferences.revealSelectedPlayer === false &&
      (tileActivation || (!wantTheater && (resumeOpts?.floating === true || !!resumeOpts?.inlineMount)));
    var wantFloating = keepParked || (!wantTheater && (tileActivation
      ? tileDestination === 'floating' : (resumeOpts?.floating === true || !!resumeOpts?.inlineMount)));
    var wantFullVideo = tileActivation && !keepParked && tileDestination === 'full-video';
    var canReuseOpenPlayer = isOpen && currentFoundUpId === foundupId &&
      (ytReady || (resumedHiddenSession && !stage.querySelector('iframe'))) &&
      (resumeOpts?.preserveInstance !== false);
    // Compare actual provider identity while the old queue still names the
    // playing clip. A reordered/refreshed queue can move it to another index.
    var previousVideo = currentQueue[currentIndex];
    var nextVideo = queue[targetIndex];
    var previousVideoId = extractYouTubeVideoId(previousVideo?.embed_url || previousVideo?.embedUrl);
    var nextEmbed = parseYouTubeEmbed(nextVideo?.embed_url || nextVideo?.embedUrl);
    var nextVideoId = extractYouTubeVideoId(nextVideo?.embed_url || nextVideo?.embedUrl);
    var sameRetainedFile = resumedHiddenSession && !stage.querySelector('iframe') &&
      ((previousVideo?.source_url || previousVideo?.sourceUrl) &&
       (previousVideo.source_url || previousVideo.sourceUrl) === (nextVideo?.source_url || nextVideo?.sourceUrl));
    var sameTileMedia = (tileActivation || resumedHiddenSession) && canReuseOpenPlayer &&
      ((previousVideoId && previousVideoId === nextVideoId && ytActiveVideoId === nextVideoId && ytHost === nextEmbed?.origin) || sameRetainedFile);

    // If switching videos within an already-open player for the same FoundUp, keep live <iframe>!
    if (canReuseOpenPlayer) {
      currentQueue = queue;
      if (sameTileMedia) currentIndex = targetIndex;
      filteredIndices = null;
      if (!resumedHiddenSession) railQuery = null;
      matchesQuery = resumeOpts?.matchesQuery || matchesQuery;
      if (resumeOpts?.returnTile || resumeOpts?.returnFocusTo) {
        returnTile = resumeOpts.returnTile || resumeOpts.returnFocusTo;
      }
      if (resumeOpts?.onClose) onClose = resumeOpts.onClose;
      if (resumeOpts?.onSelectChange) onSelectChange = resumeOpts.onSelectChange;
      if (!resumedHiddenSession || Object.prototype.hasOwnProperty.call(resumeOpts || {}, 'onQueueEnd')) onQueueEnd = resumeOpts?.onQueueEnd || null;
      if (!resumedHiddenSession || Object.prototype.hasOwnProperty.call(resumeOpts || {}, 'onPinchReturn')) onPinchReturn = resumeOpts?.onPinchReturn || null;
      if (!resumedHiddenSession || Object.prototype.hasOwnProperty.call(resumeOpts || {}, 'onReturnToMall')) onReturnToMall = resumeOpts?.onReturnToMall || null;
      if (!resumedHiddenSession || Object.prototype.hasOwnProperty.call(resumeOpts || {}, 'onResumeFromMall')) onResumeFromMall = resumeOpts?.onResumeFromMall || null;
      autoplayRequested = !keepParked && resumeOpts?.autoplay !== false;
      muteOnStart = wantTheater || resumeOpts?.muted === true;
      failedQueueIndices.clear();
      consecutiveAutoSkips = 0;
      queueHalted = false;
      if (tucked && !keepParked) untuck({ silent: true });
      if (wantFullVideo) {
        if (!container.classList.contains('video-player-full-video')) applyWikiTubePresentation(false, true);
      } else if (wantTheater && !theater) setTheater(true, returnTile);
      else if (wantFloating && !floating) applyFloatingPresentation();
      else if (!wantTheater && !wantFloating && !wikitube) applyWikiTubePresentation(false);
      if (sameTileMedia) {
        titleEl.textContent = nextVideo.title || '';
        var sameFrame = stage.querySelector('iframe');
        if (sameFrame) sameFrame.title = 'YouTube video \u2014 ' + titleEl.textContent;
        if (playbackStatus) playbackStatus.videoId = nextVideo.video_id || nextVideo.videoId || nextVideo.id || null;
        if (resumedHiddenSession) refreshQueue();
        else renderRail();
        updateRailSelection();
        updateSaveButtonState(isVideoSaved(currentFoundUpId, nextVideo));
        onSelectChange?.(currentIndex, nextVideo);
        resetChromeTimer();
        if (autoplayRequested && playbackStatus?.state !== 'playing') {
          if (requestYouTubePlay) requestYouTubePlay();
          else playNativeMedia()?.catch(function() {});
        }
        window.dispatchEvent(new CustomEvent('videoPlayerNavigate', {
          detail: { foundupId: currentFoundUpId, videoIndex: currentIndex }
        }));
        return;
      }
      goToVideo(targetIndex, { explicitUserSelect: true });
      return;
    }

    if (isOpen) close({ restore: false, preserveQueueOwner: currentFoundUpId === foundupId });

    var rs = null;
    if (resumeOpts != null && resumeOpts !== undefined) {
      if (typeof resumeOpts === 'number') {
        rs = resumeOpts;
      } else if (typeof resumeOpts === 'object' && typeof resumeOpts.resumeSeconds === 'number') {
        rs = resumeOpts.resumeSeconds;
      }
    }
    pendingResumeSeconds = normalizeResumeSeconds(rs, 0);

    scopedPlayer = !!resumeOpts?.returnTile || resumeOpts?.scoped === true;
    returnTile = resumeOpts?.returnTile || resumeOpts?.returnFocusTo || null;
    var browseField = resumeOpts?.returnFocusTo?.closest('.mall-tile-field-wrapper');
    var rowTrack = resumeOpts?.returnFocusTo?.closest('.mall-category-track');
    returnScroll = browseField ? {
      field: browseField,
      top: browseField.scrollTop,
      left: browseField.scrollLeft,
      height: browseField.clientHeight,
      tileTop: returnTile.offsetTop,
      rowTrack: rowTrack,
      rowLeft: rowTrack?.scrollLeft
    } : null;

    onClose = resumeOpts?.onClose || null;
    onSelectChange = resumeOpts?.onSelectChange || null;
    onQueueEnd = resumeOpts?.onQueueEnd || null;
    onPinchReturn = resumeOpts?.onPinchReturn || null;
    onReturnToMall = resumeOpts?.onReturnToMall || null;
    onResumeFromMall = resumeOpts?.onResumeFromMall || null;
    autoplayRequested = !keepParked && resumeOpts?.autoplay !== false;
    muteOnStart = wantTheater || resumeOpts?.muted === true;
    matchesQuery = resumeOpts?.matchesQuery ||
      (document.getElementById('redDogAnchor')?.querySelector(':scope > .mall-member-search-dock')
        ? window.mallTileField?.matchesVideoQuery : null);
    queueSearch.value = resumeOpts?.query || '';
    scopedQueueQuery = resumeOpts?.queueQuery || '';
    if (memberQueueDock) memberQueueDock.input.value = resumeOpts?.queueQuery || '';
    filteredIndices = null;
    railQuery = null;
    failedQueueIndices.clear();
    consecutiveAutoSkips = 0;
    queueHalted = false;

    container.classList.toggle('scoped-player', scopedPlayer);
    container.classList.toggle('desktop-poster-player', !!returnScroll);
    mediaPanel.scrollTop = 0;

    currentFoundUpId = foundupId;
    currentQueue = queue;
    currentIndex = targetIndex;
    isOpen = true;
    container.classList.add('open');

    if (wantFullVideo) {
      applyWikiTubePresentation(false, true);
      filterRail();
    } else if (wantTheater) {
      setTheater(true, returnTile);
    } else if (wantFloating) {
      applyFloatingPresentation();
      if (memberQueueDock && memberQueueDock.input.value.trim() && matchesQuery) {
        var initialQuery = memberQueueDock.input.value.trim().slice(0, 300);
        var matchingIndices = currentQueue.reduce(function (acc, video, idx) {
          if (matchesQuery(video, initialQuery)) acc.push(idx);
          return acc;
        }, []);
        if (matchingIndices.length) {
          railQuery = initialQuery;
          filteredIndices = matchingIndices;
        }
      }
      renderRail();
    } else {
      applyWikiTubePresentation(false);
      filterRail();
    }

    if (keepParked) tuck();
    renderVideo(currentQueue[currentIndex], false);
    syncFloatingGeometry();

    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[currentIndex]));
    recordWatch(currentFoundUpId, currentQueue[currentIndex], currentIndex);
    onSelectChange?.(currentIndex, currentQueue[currentIndex]);

    window.dispatchEvent(new CustomEvent('videoPlayerOpen', {
      detail: { foundupId: foundupId, videoIndex: currentIndex, mode: currentModeName() }
    }));
  }

  function selectVideo(index, opts) {
    if (!isOpen || mallHidden || index < 0 || index >= currentQueue.length) return false;
    if (opts?.returnTile) returnTile = opts.returnTile;
    var keepParked = tucked && videoOptions().revealSelectedPlayer === false;
    if (tucked && !keepParked) untuck({ silent: true });
    autoplayRequested = !keepParked && opts?.autoplay !== false;
    failedQueueIndices.clear();
    consecutiveAutoSkips = 0;
    queueHalted = false;
    if (index === currentIndex) {
      if (autoplayRequested && playbackStatus?.state !== 'playing') {
        requestYouTubePlay?.();
      }
      return true;
    }
    goToVideo(index, { explicitUserSelect: true });
    return true;
  }

  // ─── Close and Return to Grid ───
  function close(options) {
    if (!isOpen) return;
    var restore = options?.restore !== false;
    var wasMallHidden = mallHidden;

    flushCurrentPlaybackPosition();
    pausePlayback();
    pendingResumeSeconds = null;

    isOpen = false;
    hiddenSelectionPending = false;
    mallHidden = false;
    mallReturnMode = null;
    container.hidden = false;
    container.inert = false;
    container.removeAttribute('aria-hidden');
    untuck({ silent: true });
    container.classList.remove(
      'open',
      'video-player-inline',
      'video-player-floating',
      'video-player-theater',
      'video-player-wikitube',
      'video-player-full-video',
      'video-player-mall',
      'video-player-queue-docked',
      'chrome-hidden',
      'is-tucked'
    );
    inline = false;
    floating = false;
    theater = false;
    wikitube = false;
    queueSearchForm.hidden = true;
    memberQueueDock?.hide();
    releaseModalInert();
    syncFloatingGeometry();

    resetPlayback(false);
    clearTimeout(railTimer);
    clearTimeout(chromeTimer);
    failedQueueIndices.clear();
    consecutiveAutoSkips = 0;
    queueHalted = false;

    currentQueue = [];
    currentFoundUpId = null;
    currentEntryIdentity = undefined;
    currentIndex = -1;

    var afterClose = onClose;
    onClose = null;
    onSelectChange = null;
    onQueueEnd = null;
    onPinchReturn = null;
    onReturnToMall = null;
    onResumeFromMall = null;
    queueContinuation = null;
    if (afterClose) afterClose(restore, { preserveQueueOwner: options?.preserveQueueOwner === true, dismissPlayback: options?.dismissPlayback === true });

    if (returnTile) {
      var tile = returnTile.isConnected ? returnTile : Array.from(document.querySelectorAll('#mallTileField .mall-tile')).find(function(candidate) {
        return returnTile.dataset.videoId ? candidate.dataset.videoId === returnTile.dataset.videoId :
          candidate.dataset.foundupId === returnTile.dataset.foundupId;
      });
      // Mall return already restored its caller. Closing a hidden session must
      // not apply the selected-lane scroll snapshot to the visible root grid.
      if (restore && !wasMallHidden) {
        tile?.focus({ preventScroll: true });
        if (returnScroll) {
          var field = returnScroll.field;
          var top = returnScroll.top;
          if (tile && field.contains(tile) &&
              (tile.offsetTop !== returnScroll.tileTop || field.clientHeight !== returnScroll.height)) {
            var anchor = Math.max(0, returnScroll.tileTop - top);
            top = tile.offsetTop - Math.min(anchor, Math.max(0, field.clientHeight - tile.offsetHeight));
          }
          field.scrollTo({ top: top, left: returnScroll.left, behavior: 'instant' });
          returnScroll.rowTrack?.scrollTo({ left: returnScroll.rowLeft, behavior: 'instant' });
        }
      }
      returnTile = null;
    }
    returnScroll = null;

    window.dispatchEvent(new CustomEvent('videoPlayerClose', { detail: { restore: restore } }));
  }

  // ─── Queue Navigation & Bounded Sequential Auto-Advance ───
  function activeSequence() {
    return filteredIndices || currentQueue.map(function (_, index) { return index; });
  }

  function goToVideo(index, navOpts) {
    if (mallHidden || index < 0 || index >= currentQueue.length) return;
    var explicitUserSelect = !!navOpts?.explicitUserSelect;
    var fromAutoAdvance = !!navOpts?.fromAutoAdvance;
    if (!navOpts?.preserveFailures) {
      failedQueueIndices.clear();
      consecutiveAutoSkips = 0;
      queueHalted = false;
    }
    if (explicitUserSelect || fromAutoAdvance || theater || wikitube || floating ||
        container.classList.contains('video-player-queue-docked')) {
      if (index === currentIndex && !explicitUserSelect && !fromAutoAdvance) return;
      if (!explicitUserSelect) autoplayRequested = true;
      try { muteOnStart = ytPlayer?.isMuted?.() ?? muteOnStart; } catch (e) { /* provider not ready */ }
    }
    flushCurrentPlaybackPosition();
    pendingResumeSeconds = null;
    if (navOpts?.selectionOnly && tucked) {
      pausePlayback();
      resetPlayback(false);
    }
    currentIndex = index;
    if (navOpts?.selectionOnly && tucked) {
      // Select from the catalog while parked; defer provider work until visible.
      hiddenSelectionPending = true;
      updateVideoCaption(currentQueue[index]);
      playbackStatus = { provider: parseYouTubeEmbed(currentQueue[index].embed_url || currentQueue[index].embedUrl) ? 'youtube' : 'html5',
        state: 'selected-hidden', videoId: currentQueue[index].video_id || currentQueue[index].id || null,
        mode: currentModeName(), tucked: true, pendingSelection: true };
      updateTuckHandleLabel();
      window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: { ...playbackStatus } }));
    } else {
      hiddenSelectionPending = false;
      renderVideo(currentQueue[index], true);
    }
    updateRailSelection();
    resetChromeTimer();

    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[index]));
    if (!hiddenSelectionPending) recordWatch(currentFoundUpId, currentQueue[index], index);
    onSelectChange?.(currentIndex, currentQueue[index]);

    window.dispatchEvent(new CustomEvent('videoPlayerNavigate', {
      detail: { foundupId: currentFoundUpId, videoIndex: index }
    }));
  }

  // A scoped data owner may append one bounded page at a loaded queue boundary.
  // Closing, pausing, hiding or changing selection invalidates deferred playback.
  function continueQueue(explicit, selectionOnly) {
    var hiddenSelection = selectionOnly === true;
    if (queueContinuation) return hiddenSelection;
    if (!onQueueEnd || filteredIndices || !(hiddenSelection ? isOpen && tucked && !mallHidden : canStartYouTube())) return false;
    var owner = currentFoundUpId;
    var queue = currentQueue;
    var index = currentIndex;
    var generation = renderGeneration;
    var intent = playbackIntentEpoch;
    var query = railQuery;
    var load = onQueueEnd;
    var task = Promise.resolve().then(function () { return load(); });
    queueContinuation = task;
    task.then(function (added) {
      if (!added || !isOpen || currentFoundUpId !== owner || currentQueue !== queue ||
          currentIndex !== index || renderGeneration !== generation ||
          playbackIntentEpoch !== intent || railQuery !== query || filteredIndices ||
          !(hiddenSelection ? tucked && !mallHidden : canStartYouTube()) ||
          (!explicit && !videoOptions().autoplayNext)) return;
      var next = index + 1;
      if (next >= currentQueue.length) return;
      refreshQueue();
      autoplayRequested = !hiddenSelection;
      goToVideo(next, { explicitUserSelect: explicit, fromAutoAdvance: !explicit, preserveFailures: !explicit, selectionOnly: hiddenSelection });
      showHint(hiddenSelection ? 'Next selected · hidden' : 'Next');
    }).catch(function () {
      if (isOpen && currentFoundUpId === owner) showHint('Could not load more videos. Try Next again.');
    }).finally(function () {
      if (queueContinuation === task) queueContinuation = null;
    });
    return true;
  }

  function refreshQueue() {
    if (!isOpen || mallHidden) return;
    if (railQuery && matchesQuery) {
      filteredIndices = currentQueue.reduce(function (indices, video, index) {
        if (matchesQuery(video, railQuery)) indices.push(index);
        return indices;
      }, []);
    }
    renderRail();
    updateRailSelection();
  }

  function pinchReturn() {
    if (onPinchReturn && onPinchReturn() !== false) return;
    close();
  }

  function nextVideo(options) {
    if (mallHidden) return;
    var selectionOnly = options?.keepHidden === true && tucked;
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    var next = pos >= 0 ? seq[pos + 1] : seq[0];
    if (next !== undefined && next < currentQueue.length) {
      autoplayRequested = !selectionOnly;
      goToVideo(next, { explicitUserSelect: true, selectionOnly: selectionOnly });
      showHint(selectionOnly ? 'Next selected · hidden' : 'Next');
    } else if (!continueQueue(true, selectionOnly)) {
      showHint('End of queue');
    }
  }

  function prevVideo() {
    if (mallHidden) return;
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    var previous = pos >= 0 ? seq[pos - 1] : seq[seq.length - 1];
    if (previous !== undefined && previous >= 0) {
      autoplayRequested = true;
      goToVideo(previous, { explicitUserSelect: true });
      showHint('Previous');
    }
  }

  function handleVideoEnded() {
    if (!isPlaybackDisplayed()) { pausePlayback(); return; }
    if (!videoOptions().autoplayNext) {
      autoplayRequested = false;
      queueHalted = true;
      showHint('Autoplay next is off');
      return;
    }
    consecutiveAutoSkips = 0;
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    for (var step = pos + 1; step < seq.length; step++) {
      var candidate = seq[step];
      if (!failedQueueIndices.has(candidate)) {
        autoplayRequested = true;
        goToVideo(candidate, { fromAutoAdvance: true, preserveFailures: true });
        showHint('Next');
        return;
      }
    }
    if (!continueQueue(false)) showHint('End of queue');
  }

  function getAutoSkipDelayMs() {
    var override = window.__pfmallWikiTubeSkipDelayMs;
    return typeof override === 'number' && override >= 0 ? override : DEFAULT_AUTO_SKIP_MS;
  }

  function scheduleWikiTubeRecovery(baseMessage, errorState, code, provider) {
    var report = provider === 'html5' ? reportHTML5 : reportYouTube;
    failedQueueIndices.add(currentIndex);
    if (!isPlaybackDisplayed()) {
      pausePlayback();
      queueHalted = true;
      report(errorState, baseMessage, code);
      return;
    }
    if ((!wikitube && !container.classList.contains('video-player-full-video')) || !videoOptions().autoplayNext) {
      report(errorState, baseMessage, code);
      return;
    }
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    var nextCandidate = undefined;
    for (var i = pos + 1; i < seq.length; i++) {
      if (!failedQueueIndices.has(seq[i])) {
        nextCandidate = seq[i];
        break;
      }
    }
    if (nextCandidate !== undefined && consecutiveAutoSkips < MAX_CONSECUTIVE_AUTO_SKIPS) {
      consecutiveAutoSkips += 1;
      report(errorState, baseMessage + ' Advancing to next video…', code);
      clearTimeout(autoSkipTimer);
      var expectedGen = renderGeneration;
      autoSkipTimer = setTimeout(function () {
        autoSkipTimer = null;
        if (!isOpen || (!wikitube && !container.classList.contains('video-player-full-video')) || renderGeneration !== expectedGen || !videoOptions().autoplayNext) return;
        if (!isPlaybackDisplayed()) { pausePlayback(); return; }
        autoplayRequested = true;
        goToVideo(nextCandidate, { fromAutoAdvance: true, preserveFailures: true });
      }, getAutoSkipDelayMs());
    } else {
      queueHalted = true;
      report(errorState, baseMessage + ' Queue stopped — no playable videos remaining.', code);
    }
  }

  function canStartYouTube() {
    var view = displayedMediaArea();
    return !!view && view.rect.width >= 200 && view.rect.height >= 200 &&
      view.area > view.rect.width * view.rect.height / 2;
  }

  var YOUTUBE_ERRORS = {
    2: ['configuration', 'YouTube rejected the video configuration.'],
    5: ['playback-error', 'YouTube could not play this video in this browser.'],
    100: ['unavailable', 'This video is unavailable on YouTube.'],
    101: ['embedding-disabled', 'YouTube refused to play this embedded video.'],
    150: ['embedding-disabled', 'YouTube refused to play this embedded video.'],
    153: ['client-identification', 'YouTube could not identify this embedded player.']
  };

  function armPlayStartGuard(generation) {
    clearTimeout(startGuardTimer);
    startGuardTimer = setTimeout(function () {
      if (!isOpen || generation !== renderGeneration) return;
      if (playbackStatus && (playbackStatus.state === 'starting' || playbackStatus.state === 'ready')) {
        var pState = null;
        try { pState = ytPlayer?.getPlayerState?.(); } catch (e) { /* ignore */ }
        // YT.PlayerState.BUFFERING === 3 means network is actively loading stream; wait for playbackTimer
        if (pState === 3) return;
        autoplayRequested = false;
        reportYouTube('provider-unknown', 'YouTube did not start. Try Play video, its native Play control or open the source.');
      }
    }, PLAY_START_GUARD_MS);
  }

  function reuseYouTubeInstance(embed, videoId) {
    if (!ytPlayer || !ytReady || ytHost !== embed.origin) return false;
    if (typeof ytPlayer.loadVideoById !== 'function' || typeof ytPlayer.cueVideoById !== 'function') return false;
    var iframe = stage.querySelector('iframe');
    if (!iframe || !iframe.isConnected) return false;

    resetPlayback(true);
    var generation = renderGeneration;
    ytActiveGeneration = generation;
    ytActiveVideoId = videoId;
    iframe.title = 'YouTube video · ' + titleEl.textContent;

    requestYouTubePlay = function () {
      if (!isOpen || generation !== renderGeneration) return;
      if (!canStartYouTube()) {
        autoplayRequested = false;
        clearPlaybackTimers();
        reportYouTube('manual-play', 'Bring the video into view before playing.');
        return;
      }
      if (document.activeElement === playBtn) {
        var focusTarget = playerFocusTarget();
        focusTarget?.focus({ preventScroll: true });
      }
      reportYouTube('starting', 'Starting video…');
      armPlayStartGuard(generation);
      try {
        if (muteOnStart) ytPlayer.mute?.();
        else ytPlayer.unMute?.();
        ytPlayer.playVideo();
      } catch (e) {
        reportYouTube('provider-unknown', 'YouTube did not start. Try Play video or open the source.');
      }
    };

    try {
      if (muteOnStart) ytPlayer.mute?.();
      if (autoplayRequested && canStartYouTube()) {
        reportYouTube('starting', 'Starting video…');
        armPlayStartGuard(generation);
        ytPlayer.loadVideoById(videoId);
      } else {
        ytPlayer.cueVideoById(videoId);
        reportYouTube('manual-play', 'The video is ready to play.');
      }
      return true;
    } catch (e) {
      destroyYTPlayer();
      stage.replaceChildren();
      return false;
    }
  }

  function renderYouTube(embed, videoId, allowReuse) {
    if (allowReuse && reuseYouTubeInstance(embed, videoId)) return;

    resetPlayback(false);
    var openGeneration = renderGeneration;
    ytActiveGeneration = openGeneration;
    ytActiveVideoId = videoId;
    var shouldAutoplayNow = autoplayRequested && canStartYouTube();
    var src = new URL('/embed/' + videoId, embed.origin);
    src.searchParams.set('enablejsapi', '1');
    src.searchParams.set('playsinline', '1');
    src.searchParams.set('controls', '1');
    src.searchParams.set('rel', '0');
    if (shouldAutoplayNow) {
      src.searchParams.set('autoplay', '1');
      if (muteOnStart) src.searchParams.set('mute', '1');
    }
    if (/^https?:$/.test(window.location.protocol)) src.searchParams.set('origin', window.location.origin);

    var iframe = document.createElement('iframe');
    iframe.title = 'YouTube video · ' + titleEl.textContent;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.src = src.href;
    stage.appendChild(iframe);
    ytHost = embed.origin;

    function current() {
      return isOpen && ytActiveGeneration === renderGeneration && iframe.isConnected;
    }
    function waitForPlayback(state, message) {
      clearTimeout(playbackTimer);
      playbackTimer = setTimeout(function () {
        if (!current()) return;
        autoplayRequested = false;
        reportYouTube(state, message);
      }, YOUTUBE_TIMEOUT_MS);
    }
    function failed(state, message, code) {
      if (!current()) return;
      clearPlaybackTimers();
      autoplayRequested = false;
      if (code !== undefined) {
        scheduleWikiTubeRecovery(message, state, code);
      } else {
        reportYouTube(state, message, code);
      }
    }

    reportYouTube('loading', 'Loading YouTube player…');
    waitForPlayback('timeout', 'YouTube did not finish loading. Try its Play control or open the source.');

    ensureYouTubeAPI().then(function () {
      if (!isOpen || openGeneration !== renderGeneration || !iframe.isConnected) return;
      ytPlayer = new window.YT.Player(iframe, {
        events: {
          onReady: function (ev) {
            if (!current()) return;
            ytReady = true;
            clearTimeout(playbackTimer);
            if (muteOnStart) ev.target.mute();
            reportYouTube('ready');
            requestYouTubePlay = function () {
              if (!current()) return;
              if (!canStartYouTube()) {
                autoplayRequested = false;
                clearPlaybackTimers();
                reportYouTube('manual-play', 'Bring the video into view before playing.');
                return;
              }
              waitForPlayback('provider-unknown', 'YouTube did not start. Try its Play control or open the source.');
              armPlayStartGuard(ytActiveGeneration);
              if (document.activeElement === playBtn) {
                var focusTarget = playerFocusTarget();
                focusTarget?.focus({ preventScroll: true });
              }
              reportYouTube('starting', 'Starting video…');
              try { ev.target.playVideo(); }
              catch (e) { failed('provider-unknown', 'YouTube did not start. Try again or open the source.'); }
            };
            var alreadyPlaying = false;
            try { alreadyPlaying = ev.target.getPlayerState?.() === 1; } catch (e) { /* ignore */ }
            if (alreadyPlaying) {
              if (!isPlaybackDisplayed()) {
                pausePlayback();
                reportYouTube('paused', 'Playback paused while the player is hidden.', undefined, 2);
                return;
              }
              consecutiveAutoSkips = 0;
              queueHalted = false;
              reportYouTube('playing', '', undefined, 1);
            } else if (autoplayRequested && canStartYouTube()) {
              requestYouTubePlay();
            } else {
              reportYouTube('manual-play', 'The video is ready to play.');
            }
          },
          onStateChange: function (ev) {
            if (!current()) return;
            var state = ev.data;
            if (state === 1) {
              if (!isPlaybackDisplayed()) {
                pausePlayback();
                reportYouTube('paused', 'Playback paused while the player is hidden.', undefined, 2);
                return;
              }
              clearPlaybackTimers();
              consecutiveAutoSkips = 0;
              queueHalted = false;
              failedQueueIndices.delete(currentIndex);
              reportYouTube('playing', '', undefined, 1);
              resetChromeTimer();
            } else if (state === 2 && requestYouTubePlay) {
              playbackIntentEpoch++;
              autoplayRequested = false;
              clearPlaybackTimers();
              reportYouTube('paused', 'Playback paused.', undefined, 2);
            } else if (state === 0) {
              if (!isPlaybackDisplayed()) {
                pausePlayback();
                reportYouTube('paused', 'Playback paused while the player is hidden.', undefined, 2);
                return;
              }
              clearPlaybackTimers();
              reportYouTube('ended', '', undefined, 0);
              handleVideoEnded();
            } else {
              window.dispatchEvent(new CustomEvent('mallVideoPlayback', {
                detail: { provider: 'youtube', state: 'provider-state', videoId: ytActiveVideoId, providerState: state }
              }));
            }
          },
          onError: function (ev) {
            var result = YOUTUBE_ERRORS[ev.data] || ['provider-unknown', 'YouTube could not start this video.'];
            failed(result[0], result[1] + ' Open the source to check it on YouTube.', ev.data);
          },
          onAutoplayBlocked: function () {
            // Iframe autoplay and API play can report independently. A late
            // rejection must not overwrite successful, paused or failed playback.
            if (!current() || !autoplayRequested || queueHalted || !canStartYouTube() ||
                !['loading', 'ready', 'starting'].includes(playbackStatus?.state)) return;
            clearPlaybackTimers();
            // A browser can reject audible play after asynchronous iframe READY.
            // Retry this visible, still-requested start once with sound muted;
            // provider errors, paused/hidden playback and stale frames never retry.
            if (!mutedAutoplayRetryUsed && !muteOnStart && ytReady && requestYouTubePlay &&
                ['starting', 'ready'].includes(playbackStatus?.state) &&
                typeof ytPlayer?.mute === 'function') {
              mutedAutoplayRetryUsed = true;
              try {
                if (!ytPlayer.isMuted?.()) {
                  muteOnStart = true;
                  ytPlayer.mute();
                  requestYouTubePlay();
                  return;
                }
              } catch (e) { /* retain truthful manual recovery if muting fails */ }
            }
            autoplayRequested = false;
            queueHalted = true;
            reportYouTube('autoplay-blocked', 'Your browser blocked automatic playback. Use Play video to try again.');
          }
        }
      });
    }).catch(function () {
      failed('timeout', 'YouTube controls may still work. Try Play in the video or open the source.');
    });
  }

  // Typed local media is optional; it cannot exempt YouTube from its guards.
  function isMemberCardVideo(video) {
    var card = video?.member_card;
    var match = /^\/member\/vote\/comics\/([a-z0-9-]+)-card-loop\.mp4$/.exec(video?.source_url || '');
    if (!card || typeof card !== 'object' || Array.isArray(card) || !match || video.embed_url || video.embedUrl) return false;
    var prefix = '/member/vote/comics/' + match[1] + '-card-';
    return ['name', 'chamber', 'constituency'].every(function(key) {
      return typeof card[key] === 'string' && card[key].length > 0 && card[key].length <= 160;
    }) && card.still_url === prefix + 'still.webp' && card.animation_url === prefix + 'loop.webp' &&
      card.udp_score === null && card.cu_score === null && /^#[A-Za-z]{1,50}OUT$/.test(card.hashtag || '');
  }

  function createMemberCardMedia(video) {
    var card = video.member_card;
    var generation = renderGeneration;
    var panel = document.createElement('article');
    panel.className = 'video-player-member-card';
    var heading = document.createElement('header');
    var name = document.createElement('h2');
    name.textContent = card.name;
    var office = document.createElement('p');
    office.textContent = [card.chamber, card.constituency].join(' · ');
    heading.append(name, office);
    var media = document.createElement('video');
    media.controls = true;
    media.loop = true;
    media.muted = true;
    media.playsInline = true;
    media.preload = 'none';
    media.poster = card.still_url;
    media.src = video.source_url;
    media.setAttribute('aria-label', 'Animated AI caricature of ' + card.name);
    var footer = document.createElement('footer');
    var hashtag = document.createElement('p');
    hashtag.className = 'video-player-member-hashtag';
    hashtag.append(document.createTextNode(card.hashtag.slice(0, -3)));
    var out = document.createElement('strong');
    out.textContent = 'OUT';
    hashtag.append(out);
    var scores = document.createElement('p');
    scores.className = 'video-player-member-scores';
    scores.textContent = 'UDP: Pending · CU: Pending';
    footer.append(hashtag, scores);
    try {
      var official = new URL(card.official_url);
      if (official.protocol === 'https:' && !official.username && !official.password && !official.port &&
          /\.(?:house|senate)\.gov$/.test(official.hostname)) {
        var link = document.createElement('a');
        link.href = official.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Official congressional profile';
        footer.append(link);
      }
    } catch (error) { /* No profile is invented for invalid metadata. */ }
    panel.append(heading, media, footer);
    stage.append(panel);
    function current() { return isOpen && generation === renderGeneration && panel.isConnected; }
    function fitCard() {
      if (!current() || stage.clientWidth <= 0 || stage.clientHeight <= 0) return;
      var width = Math.min(stage.clientWidth, stage.clientHeight * 9 / 16);
      panel.style.width = width + 'px';
      panel.style.height = width * 16 / 9 + 'px';
    }
    var motion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    function reduceMotion() {
      if (!current() || !motion?.matches) return;
      media.autoplay = false;
      pausePlayback();
      media.load();
    }
    motion?.addEventListener('change', reduceMotion);
    var observer = typeof ResizeObserver === 'function' ? new ResizeObserver(fitCard) : null;
    observer?.observe(stage);
    window.addEventListener('resize', fitCard);
    var frame = requestAnimationFrame(fitCard);
    fitCard();
    memberMotionCleanup = function () {
      motion?.removeEventListener('change', reduceMotion);
      observer?.disconnect();
      window.removeEventListener('resize', fitCard);
      cancelAnimationFrame(frame);
    };
    function imageFallback(requested) {
      if (!current() || memberAnimation) return;
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'video-player-member-animation';
      var image = document.createElement('img');
      image.alt = 'Animated AI caricature of ' + card.name;
      button.append(image);
      var running = false;
      function active() { return current() && memberAnimation === controller; }
      function pause() {
        if (!active()) return;
        playbackIntentEpoch++;
        autoplayRequested = false;
        clearPlaybackTimers();
        running = false;
        image.src = card.still_url;
        button.setAttribute('aria-label', 'Play card animation');
        reportHTML5('paused', '');
      }
      function play() {
        if (!active() || !isPlaybackDisplayed()) return;
        autoplayRequested = true;
        running = true;
        image.src = card.animation_url;
        button.setAttribute('aria-label', 'Pause card animation');
        reportHTML5('loading', 'Preparing card animation…');
      }
      var controller = { play: play, pause: pause, isPlaying: function () { return running; },
        destroy: function () { running = false; image.removeAttribute('src'); button.replaceChildren(); } };
      memberAnimation = controller;
      media.pause();
      media.removeAttribute('src');
      media.load();
      media.replaceWith(button);
      button.addEventListener('click', function () { if (running) pause(); else play(); });
      image.addEventListener('load', function () {
        if (!active() || !running) return;
        if (!isPlaybackDisplayed()) { pause(); return; }
        queueHalted = false;
        reportHTML5('playing', '');
      });
      image.addEventListener('error', function () {
        if (!active()) return;
        running = false;
        reportHTML5('playback-error', 'This card animation could not be loaded.');
      });
      if (requested && isPlaybackDisplayed()) play();
      else pause();
    }
    return { media: media, motion: motion, imageFallback: imageFallback };
  }

  // ─── Render Video ───
  function updateVideoCaption(video) {
    var sourceLink = topBar.querySelector('.video-player-source');
    var originalUrl = scopedPlayer ? scopedSourceUrl(video) : '';
    sourceLink.hidden = !originalUrl;
    if (originalUrl) {
      sourceLink.href = originalUrl;
      sourceLink.textContent = [video.source_label, video.editorial_label, video.timestamp?.slice(0, 10)]
        .filter(Boolean).join(' · ');
      sourceLink.setAttribute('aria-label', 'Original Short on YouTube · ' + sourceLink.textContent);
    }

    titleEl.textContent = video.title || '';
    return originalUrl;
  }

  function renderVideo(video, allowReuse) {
    if (!video) return;
    var originalUrl = updateVideoCaption(video);
    var sourceLink = topBar.querySelector('.video-player-source');

    var embedUrl = video.embed_url || video.embedUrl;
    var sourceUrl = video.source_url || video.sourceUrl;
    var youtube = parseYouTubeEmbed(embedUrl);
    var ytId = extractYouTubeVideoId(embedUrl);
    var memberCard = isMemberCardVideo(video);
    container.classList.toggle('member-card-player', memberCard);
    container.classList.toggle('provider-youtube', !!youtube);

    if (ytId) {
      pendingResumeSeconds = null; // cannot read playback time from YouTube embed; resume N/A
      if (!originalUrl) {
        var isShortSource = typeof sourceUrl === 'string' && sourceUrl.indexOf('/shorts/' + ytId) !== -1;
        sourceLink.href = isShortSource ? 'https://www.youtube.com/shorts/' + ytId : 'https://www.youtube.com/watch?v=' + ytId;
        sourceLink.textContent = 'Source on YouTube';
        sourceLink.setAttribute('aria-label', 'Open source on YouTube');
        sourceLink.hidden = false;
      }
      renderYouTube(youtube, ytId, allowReuse);
    } else if (youtube || (scopedPlayer && embedUrl)) {
      resetPlayback(false);
      pendingResumeSeconds = null;
      scheduleWikiTubeRecovery('The YouTube video ID is invalid.', 'configuration', 2);
    } else if (embedUrl) {
      resetPlayback(false);
      pendingResumeSeconds = null;
      stage.innerHTML = '<iframe src="' + esc(embedUrl) + '?autoplay=1&rel=0" allowfullscreen allow="autoplay; encrypted-media"></iframe>';
    } else if (sourceUrl && sourceUrl.match(/\.(mp4|webm|ogg)$/i)) {
      resetPlayback(false);
      var resumeTarget = pendingResumeSeconds;
      pendingResumeSeconds = null;
      var nativeCard = memberCard ? createMemberCardMedia(video) : null;
      var nativeAutoplay = autoplayRequested && !nativeCard?.motion?.matches;
      if (memberCard && !nativeAutoplay) autoplayRequested = false;
      if (!nativeCard) stage.innerHTML = '<video src="' + esc(sourceUrl) + '"' + (muteOnStart ? ' muted' : '') +
        (nativeAutoplay ? ' autoplay' : '') + ' controls playsinline></video>';
      var ve = nativeCard?.media || stage.querySelector('video');
      if (ve) {
        ve.autoplay = nativeAutoplay;
        var nativeGeneration = renderGeneration;
        function currentNative() { return isOpen && nativeGeneration === renderGeneration && ve.isConnected && !memberAnimation; }
        ve.addEventListener('playing', function () {
          if (!currentNative()) return;
          if (!isPlaybackDisplayed()) { pausePlayback(); return; }
          consecutiveAutoSkips = 0;
          queueHalted = false;
          reportHTML5('playing', '');
        });
        ve.addEventListener('pause', function () {
          if (!currentNative()) return;
          if (!ve.ended) {
            playbackIntentEpoch++;
            autoplayRequested = false;
            reportHTML5('paused', 'Playback paused.');
          }
        });
        ve.addEventListener('ended', function () {
          if (!currentNative()) return;
          reportHTML5('ended', '');
          handleVideoEnded();
        });
        ve.addEventListener('error', function () {
          if (!currentNative()) return;
          if (nativeCard && ve.error?.code === 4) {
            nativeCard.imageFallback(autoplayRequested);
            return;
          }
          scheduleWikiTubeRecovery('Media file could not be loaded.', 'playback-error', ve.error?.code, 'html5');
        });
        if (nativeAutoplay) {
          var playPromise = ve.play?.();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(function (error) {
              if (!currentNative()) return;
              // Some engines reject play() before dispatching MEDIA_ERR_SRC_NOT_SUPPORTED.
              // Preserve the visible request for the approved image fallback.
              if (nativeCard && error?.name === 'NotSupportedError' && ve.error?.code === 4) {
                nativeCard.imageFallback(autoplayRequested);
                return;
              }
              if (nativeCard?.motion?.matches) return;
              autoplayRequested = false;
              queueHalted = true;
              reportHTML5('autoplay-blocked', 'Your browser blocked automatic playback. Use Play video to try again.');
            });
          }
        } else {
          reportHTML5('manual-play', 'The video is ready to play.');
        }

        if (resumeTarget != null) {
          function applyResumeSeek() {
            if (!currentNative()) return;
            var dur = ve.duration;
            if (!isFinite(dur)) dur = 0;
            var n = normalizeResumeSeconds(resumeTarget, dur);
            if (n == null) return;
            var cap = dur > 0 ? Math.min(n, Math.max(MIN_RESUME_SECONDS, dur - 0.25)) : n;
            try { ve.currentTime = cap; } catch (err) { /* clamp edge */ }
          }
          ve.addEventListener('loadedmetadata', function onLm() {
            ve.removeEventListener('loadedmetadata', onLm);
            applyResumeSeek();
          });
          ve.addEventListener('canplay', function onCp() {
            ve.removeEventListener('canplay', onCp);
            applyResumeSeek();
          });
        }
      }
    } else {
      resetPlayback(false);
      pendingResumeSeconds = null;
      stage.innerHTML = '<div class="video-player-loading">Loading video...</div>';
    }
  }

  // ─── Render Rail ───
  function filterRail() {
    if (mallHidden) return;
    var input = theater ? queueSearch : null;
    if (memberQueueDock && !memberQueueDock.element.hidden) input = memberQueueDock.input;
    var query = input ? input.value.trim().slice(0, 300) : scopedQueueQuery;
    if (theater && input !== queueSearch) queueSearch.value = query;
    // This queue context is independent of the Mall's restored search input.
    // Keep it even when the queue dock is released or hidden in Floating/Mall.
    scopedQueueQuery = query;
    if (query === railQuery) return;
    playbackIntentEpoch++;
    railQuery = query;
    filteredIndices = query && matchesQuery ? currentQueue.reduce(function (indices, video, index) {
      if (matchesQuery(video, query)) indices.push(index);
      return indices;
    }, []) : null;
    renderRail();
    queueTrack.scrollLeft = 0;
  }

  function playSearchResult(event) {
    event?.preventDefault();
    if (!theater) return;
    filterRail();
    if (!filteredIndices?.length) return;

    var result = filteredIndices[filteredIndices.indexOf(currentIndex) + 1] ?? filteredIndices[0];
    autoplayRequested = true;
    if (result !== currentIndex) goToVideo(result, { explicitUserSelect: true });
    else if (playbackStatus?.state !== 'playing') requestYouTubePlay?.();
  }

  function playMemberSearchResult() {
    filterRail();
    if (!filteredIndices?.length || ['playing', 'loading', 'starting', 'provider-state'].includes(playbackStatus?.state)) return;
    var media = stage.querySelector('video');
    if (memberAnimation?.isPlaying() || (media && !media.paused && !media.ended)) return;
    var first = filteredIndices[0];
    autoplayRequested = true;
    if (first !== currentIndex) goToVideo(first, { explicitUserSelect: true });
    else if (requestYouTubePlay) requestYouTubePlay();
    else playNativeMedia()?.catch(function () {});
  }

  function renderRail() {
    var indices = activeSequence();
    queueEmpty.hidden = indices.length !== 0;
    queueTrack.innerHTML = indices.map(function (i) {
      var video = currentQueue[i];
      var thumb = video.thumbnail_url || video.thumbnailUrl || video.poster_url || video.posterUrl || '';
      var title = video.title || 'Video ' + (i + 1);
      var selected = i === currentIndex;
      return [
        '<button type="button" class="video-player-queue-item' + (selected ? ' active' : '') +
          '" data-index="' + i + '"' + (selected ? ' aria-current="true"' : '') + '>',
        '  <img class="video-player-queue-thumb" src="' + esc(thumb) + '" alt="" loading="lazy">',
        '  <span class="video-player-queue-label">' + esc(title) + '</span>',
        '</button>'
      ].join('');
    }).join('');
  }

  function updateRailSelection() {
    var items = queueTrack.querySelectorAll('.video-player-queue-item');
    items.forEach(function (item) {
      var selected = Number(item.dataset.index) === currentIndex;
      item.classList.toggle('active', selected);
      if (selected) item.setAttribute('aria-current', 'true');
      else item.removeAttribute('aria-current');
    });

    var activeItem = queueTrack.querySelector('.video-player-queue-item.active');
    if (activeItem) {
      queueTrack.scrollTo({
        left: activeItem.offsetLeft - (queueTrack.clientWidth - activeItem.offsetWidth) / 2,
        behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
      });
    }
  }

  // ─── Unified Visibility Controller ───
  function showRail() {
    queueRail.classList.add('visible');
    resetChromeTimer();
  }

  function hideRail() {
    queueRail.classList.remove('visible');
  }

  function shouldHoldChromeOpen() {
    if (!isOpen || inline || floating || theater) return true;
    if (container.classList.contains('video-player-full-video')) return true;
    if (playbackStatus && playbackStatus.state !== 'playing') return true;
    if (memberQueueDock?.dialog.open) return true;
    if (memberQueueDock && memberQueueDock.element.contains(document.activeElement)) return true;
    return false;
  }

  function toggleChrome() {
    if (inline || floating || theater) return;
    container.classList.toggle('chrome-hidden');
    if (container.classList.contains('chrome-hidden')) {
      hideRail();
    } else {
      resetChromeTimer();
    }
  }

  function resetChromeTimer() {
    container.classList.remove('chrome-hidden');
    clearTimeout(chromeTimer);
    clearTimeout(railTimer);
    if (shouldHoldChromeOpen()) return;
    chromeTimer = setTimeout(function () {
      if (!shouldHoldChromeOpen()) {
        container.classList.add('chrome-hidden');
        hideRail();
      }
    }, CHROME_AUTO_HIDE_MS);
  }

  function showHint(text) {
    gestureHint.textContent = text;
    gestureHint.classList.add('show');
    setTimeout(function () {
      gestureHint.classList.remove('show');
    }, 800);
  }

  // ─── Intentional Pinch & Swipe Disambiguation ───
  function getPinchDistance(touches) {
    if (!touches || touches.length < 2) return 0;
    var dx = touches[0].clientX - touches[1].clientX;
    var dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function isInteractiveInputTarget(target) {
    return !!target?.closest?.('input, textarea, select, button, a, iframe, video, dialog[open], .video-player-stage');
  }

  function isHorizontalScrollTarget(target) {
    return !!target?.closest?.('.video-player-queue-track');
  }

  function bindPlayerGestures() {
    container.addEventListener('click', function (e) {
      if (suppressNextClick) {
        suppressNextClick = false;
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);

    container.addEventListener('touchstart', function (e) {
      if (!isOpen || theater || tucked) return;
      if (isInteractiveInputTarget(e.target)) return;

      if (e.touches.length === 2) {
        pinchActive = true;
        pinchConsumed = false;
        swipeTracking = false;
        initialPinchDistance = getPinchDistance(e.touches);
        return;
      }

      if (e.touches.length === 1 && !pinchActive) {
        if (isHorizontalScrollTarget(e.target)) {
          swipeTracking = false;
          return;
        }
        swipeStartX = e.touches[0].clientX;
        swipeStartY = e.touches[0].clientY;
        swipeStartTime = performance.now();
        swipeTracking = true;
      }
    }, { passive: true });

    container.addEventListener('touchmove', function (e) {
      if (!isOpen || theater || tucked) return;
      if (isInteractiveInputTarget(e.target)) return;

      if (e.touches.length === 2) {
        if (!pinchActive) {
          pinchActive = true;
          pinchConsumed = false;
          swipeTracking = false;
          initialPinchDistance = getPinchDistance(e.touches);
        }
        if (initialPinchDistance < PINCH_MIN_START_PX) {
          initialPinchDistance = getPinchDistance(e.touches);
          return;
        }
        e.preventDefault();
        if (pinchConsumed) return;

        var currentDist = getPinchDistance(e.touches);
        var delta = currentDist - initialPinchDistance;
        var scale = currentDist / initialPinchDistance;

        if ((floating || wikitube) && scale >= PINCH_OUT_RATIO && delta >= PINCH_MIN_DELTA_PX) {
          pinchConsumed = true;
          openPinchDestination();
        } else if ((floating || wikitube || container.classList.contains('video-player-full-video')) && scale <= PINCH_IN_RATIO && -delta >= PINCH_MIN_DELTA_PX) {
          pinchConsumed = true;
          returnFromGesture('pinchInDestination');
        }
        return;
      }

      if (swipeTracking && floating && e.touches.length === 1) {
        var dx = e.touches[0].clientX - swipeStartX;
        var dy = e.touches[0].clientY - swipeStartY;
        if (dx > 18 && Math.abs(dx) > Math.abs(dy) * 1.4) {
          e.preventDefault();
        }
      }
    }, { passive: false });

    container.addEventListener('touchend', function (e) {
      if (pinchActive) {
        if (e.touches.length < 2) {
          pinchActive = false;
          initialPinchDistance = 0;
          setTimeout(function () { pinchConsumed = false; }, 80);
        }
        return;
      }
      if (!swipeTracking || !e.changedTouches?.length) return;
      swipeTracking = false;
      var t = e.changedTouches[0];
      if (e.target?.closest?.('.video-player-gesture-grip, .video-player-gesture-side') && performance.now() - swipeStartTime >= 450) return;
      handlePlayerSwipeEnd(t.clientX - swipeStartX, t.clientY - swipeStartY, e.target);
    }, { passive: true });

    container.addEventListener('touchcancel', function () {
      pinchActive = false;
      pinchConsumed = false;
      swipeTracking = false;
      initialPinchDistance = 0;
    }, { passive: true });

    // iOS Safari GestureEvent fallback (fires when WebKit synthesizes pinch scale)
    container.addEventListener('gesturechange', function (e) {
      if (!isOpen || theater || tucked || pinchConsumed || typeof e.scale !== 'number') return;
      if (isInteractiveInputTarget(e.target)) return;
      e.preventDefault();
      if ((floating || wikitube) && e.scale >= PINCH_OUT_RATIO) {
        pinchConsumed = true;
        openPinchDestination();
      } else if ((floating || wikitube || container.classList.contains('video-player-full-video')) && e.scale <= PINCH_IN_RATIO) {
        pinchConsumed = true;
        returnFromGesture('pinchInDestination');
      }
    });
    container.addEventListener('gestureend', function () {
      setTimeout(function () { pinchConsumed = false; }, 80);
    });

    // Desktop mouse-drag swipe on floating chrome
    topBar.addEventListener('mousedown', function (e) {
      if (e.button !== 0 || !isOpen || !floating || tucked) return;
      if (isInteractiveInputTarget(e.target)) return;
      var downX = e.clientX;
      var downY = e.clientY;
      function onUp(upEv) {
        var dx = upEv.clientX - downX;
        var dy = upEv.clientY - downY;
        if (Math.abs(dx) >= TUCK_SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.4 && dx > 0) {
          suppressNextClick = true;
          tuck();
        }
      }
      document.addEventListener('mouseup', onUp, { once: true });
    });

    // Desktop pinch parity: Ctrl/Cmd + wheel
    container.addEventListener('wheel', function (e) {
      if (!isOpen || theater || tucked) return;
      if (!e.ctrlKey && !e.metaKey) return;
      // App navigation is confined to noninteractive player chrome. Leave
      // provider controls and ordinary browser zoom gestures alone.
      if (isInteractiveInputTarget(e.target) || !e.target?.closest?.('.video-player-top-bar, .video-player-gesture-grip')) return;
      e.preventDefault();
      if (e.deltaY < 0 && floating) {
        openPinchDestination();
      } else if (e.deltaY > 0 && (floating || wikitube)) {
        returnFromGesture('pinchInDestination');
      }
    }, { passive: false });
  }

  var chromeTapHandlers = {
    onTap: function () {
      toggleChrome();
    }
  };

  function handlePlayerSwipeEnd(dx, dy, target) {
    var absDx = Math.abs(dx);
    var absDy = Math.abs(dy);

    if (absDx < 15 && absDy < 15) {
      if (wikitube && !target?.closest?.('button, a, input, textarea, select, .video-player-queue-panel')) {
        chromeTapHandlers.onTap();
      }
      return;
    }

    resetChromeTimer();
    var dir = absDx > absDy ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');

    if (dir === 'up' && absDy >= 50 && absDy > absDx * 1.3 &&
        !isHorizontalScrollTarget(target) && videoOptions().swipeUpDestination) {
      returnFromGesture('swipeUpDestination');
      return;
    }

    if (floating && !tucked) {
      if (dir === 'right' && dx >= TUCK_SWIPE_PX && absDx > absDy * 1.4) {
        tuck();
      }
      return;
    }

    // Only the app Full Video presentation uses this horizontal queue gesture.
    // WikiTube keeps its existing save/dismiss grammar; provider touches never
    // reach this handler. A deliberate swipe is independent of natural autoplay.
    if (container.classList.contains('video-player-full-video') &&
        dir === 'right' && absDx >= Math.max(72, Math.min(140, container.clientWidth * .2)) &&
        absDx > absDy * 1.4 && !isHorizontalScrollTarget(target)) {
      var action = videoOptions().fullVideoSwipeRight || 'next';
      if (action === 'none') return;
      gestureClickBlockedUntil = performance.now() + 400;
      if (action === 'previous') prevVideo();
      else nextVideo();
      return;
    }

    if (wikitube && !isHorizontalScrollTarget(target)) {
      if ((dir === 'up' || dir === 'down') && absDy >= 50 && absDy > absDx * 1.3) {
        if (dir === 'up') nextVideo();
        else if (dir === 'down') close();
      } else if ((dir === 'left' || dir === 'right') && absDx >= 50 && absDx > absDy * 1.3 && !target?.closest?.('.video-player-queue-panel')) {
        if (dir === 'left') {
          var wasSaved = toggleSave();
          window.dispatchEvent(new CustomEvent('videoPlayerSave', {
            detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex], saved: wasSaved }
          }));
        } else if (dir === 'right') {
          showHint('Dismissed');
          window.dispatchEvent(new CustomEvent('videoPlayerDismiss', {
            detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex] }
          }));
        }
      }
    }
  }

  function bindTuckHandleGestures() {
    var handleStartX = 0;
    var handleStartY = 0;
    var handleTracking = false;

    tuckHandle.addEventListener('click', function (event) {
      if (performance.now() < gestureClickBlockedUntil) { event.preventDefault(); return; }
      untuck();
    });

    tuckHandle.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) { handleTracking = false; return; }
      handleStartX = e.touches[0].clientX;
      handleStartY = e.touches[0].clientY;
      handleTracking = true;
    }, { passive: true });

    tuckHandle.addEventListener('touchmove', function (e) {
      if (!handleTracking || e.touches.length !== 1) { handleTracking = false; return; }
      var dx = e.touches[0].clientX - handleStartX;
      var dy = e.touches[0].clientY - handleStartY;
      if (dx <= -UNTUCK_SWIPE_PX && Math.abs(dx) > Math.abs(dy)) {
        e.preventDefault();
        handleTracking = false;
        untuck();
      }
    }, { passive: false });

    tuckHandle.addEventListener('touchend', function (e) {
      if (!handleTracking || !e.changedTouches?.length) return;
      handleTracking = false;
      var dx = e.changedTouches[0].clientX - handleStartX;
      var dy = e.changedTouches[0].clientY - handleStartY;
      if (Math.abs(dx) < 15 && Math.abs(dy) < 15) {
        // Some touch sequences deliver no compatibility click. Restore on the
        // deliberate touch tap itself, and fence any later click echo.
        if (performance.now() < gestureClickBlockedUntil) return;
        e.preventDefault();
        gestureClickBlockedUntil = performance.now() + 400;
        untuck();
      } else if (dx <= -UNTUCK_SWIPE_PX && Math.abs(dx) > Math.abs(dy)) {
        untuck();
      } else if (dx >= Math.max(16, Math.min(32, tuckHandle.clientWidth * .5)) && Math.abs(dx) > Math.abs(dy) * 1.4) {
        var action = videoOptions().tuckedSwipeRight || 'next-hidden';
        if (action === 'none') return;
        e.preventDefault();
        gestureClickBlockedUntil = performance.now() + 400;
        if (action === 'next-hidden') { nextVideo({ keepHidden: true }); return; }
        untuck({ immediate: true });
        if (action === 'next-reveal') nextVideo();
      }
    }, { passive: false });
    tuckHandle.addEventListener('touchcancel', function () { handleTracking = false; });
  }

  // ─── Event Handlers ───
  function handleTopBarClick(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;

    var action = btn.dataset.action;
    resetChromeTimer();

    switch (action) {
      case 'back':
        close();
        break;
      case 'expand':
        openFrameDestination();
        break;
      case 'float':
        collapseAppVideo();
        break;
      case 'tuck':
        tuck();
        break;
      case 'prev':
        prevVideo();
        break;
      case 'next':
        nextVideo();
        break;
      case 'enter':
        // Enter FoundUp: on open landing (play.foundups.com), pass through the foundups.com Member Portal;
        // inside admitted Mall, navigate to canonical /f/{foundup_id} route (WSP 104).
        var entryId = currentEntryId();
        if (entryId && !scopedPlayer) {
          var openMall = window.mallVideoProjection?.isOpenMallHost?.(window.location);
          var destination = openMall
            ? window.mallVideoProjection.memberPortalUrl(entryId)
            : '/f/' + encodeURIComponent(entryId);
          if (openMall) window.mallStateRestore?.save?.();
          close();
          if (openMall && typeof window.location?.assign === 'function') {
            window.location.assign(destination);
          } else {
            window.location.href = destination;
          }
        }
        break;
      case 'save':
        var wasSaved = toggleSave();
        window.dispatchEvent(new CustomEvent('videoPlayerSave', {
          detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex], saved: wasSaved }
        }));
        break;
      case 'share':
        shareVideo();
        window.dispatchEvent(new CustomEvent('videoPlayerShare', {
          detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex] }
        }));
        break;
      case 'more':
        showHint('More options');
        break;
    }
  }

  function handleRailClick(e) {
    var item = e.target.closest('.video-player-queue-item');
    if (!item) return;

    var index = parseInt(item.dataset.index, 10);
    if (!isNaN(index)) {
      autoplayRequested = true;
      failedQueueIndices.clear();
      consecutiveAutoSkips = 0;
      queueHalted = false;
      if (index === currentIndex && requestYouTubePlay &&
          (theater || wikitube || container.classList.contains('video-player-queue-docked')) &&
          playbackStatus?.state !== 'playing') {
        requestYouTubePlay();
        return;
      }
      goToVideo(index, { explicitUserSelect: true });
    }
  }

  function handleKeydown(e) {
    if (!isOpen || mallHidden || theater) return;
    if (e.defaultPrevented || e.isComposing || e.target?.closest?.('dialog[open]')) return;
    if (e.target?.closest?.('.mall-card-back')) return;
    if (e.key !== 'Escape' && (inline || e.target?.closest?.('button, a, input, textarea, select'))) return;

    switch (e.key) {
      case 'Escape':
        close();
        break;
      case 'ArrowUp':
      case 'ArrowLeft':
        prevVideo();
        break;
      case 'ArrowDown':
      case 'ArrowRight':
        nextVideo();
        break;
      case ' ':
        e.preventDefault();
        toggleChrome();
        break;
    }
  }

  // ─── Save (localStorage) ───
  function getSavedVideos() {
    try {
      return JSON.parse(localStorage.getItem(SAVED_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function setSavedVideos(saved) {
    try {
      localStorage.setItem(SAVED_KEY, JSON.stringify(saved));
    } catch (e) { /* quota exceeded or private mode */ }
  }

  function getSaveKey(foundupId, video) {
    var videoId = video.video_id || video.videoId || video.id || '';
    return foundupId + '::' + videoId;
  }

  function isVideoSaved(foundupId, video) {
    var saved = getSavedVideos();
    return !!saved[getSaveKey(foundupId, video)];
  }

  function toggleSave() {
    if (!currentFoundUpId || currentIndex < 0) return false;

    var video = currentQueue[currentIndex];
    var key = getSaveKey(currentFoundUpId, video);
    var saved = getSavedVideos();

    if (saved[key]) {
      delete saved[key];
      setSavedVideos(saved);
      updateSaveButtonState(false);
      showHint('Removed');
      return false;
    } else {
      saved[key] = {
        foundupId: currentFoundUpId,
        videoId: video.video_id || video.videoId || video.id,
        title: video.title,
        thumbnail: video.thumbnail_url || video.thumbnailUrl,
        savedAt: new Date().toISOString()
      };
      setSavedVideos(saved);
      updateSaveButtonState(true);
      showHint('Saved');
      return true;
    }
  }

  function updateSaveButtonState(isSaved) {
    if (!saveBtn) return;
    saveBtn.classList.toggle('saved', isSaved);
    saveBtn.setAttribute('aria-pressed', String(isSaved));
  }

  // ─── Share (navigator.share or clipboard) ───
  function getShareUrl(video) {
    return video.embed_url || video.embedUrl || video.source_url || video.sourceUrl || '';
  }

  function scopedSourceUrl(video) {
    var id = video.video_id;
    var url = 'https://www.youtube.com/shorts/' + id;
    return /^[A-Za-z0-9_-]{11}$/.test(id) && video.source_url === url ? url : '';
  }

  function shareVideo() {
    if (!currentFoundUpId || currentIndex < 0) return;

    var video = currentQueue[currentIndex];
    var url = scopedPlayer ? scopedSourceUrl(video) : getShareUrl(video);

    if (!url) {
      showHint('No share link');
      return;
    }

    var shareData = {
      title: video.title || 'Video',
      url: url
    };

    if (navigator.share) {
      navigator.share(shareData)
        .then(function () { showHint('Shared'); })
        .catch(function (err) {
          if (err.name !== 'AbortError') {
            copyToClipboard(url);
          }
        });
    } else {
      copyToClipboard(url);
    }
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(function () { showHint('Link copied'); })
        .catch(function () { showHint('Copy failed'); });
    } else {
      var textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        showHint('Link copied');
      } catch (e) {
        showHint('Copy failed');
      }
      document.body.removeChild(textarea);
    }
  }

  // ─── Watch History (localStorage) ───
  function getWatchHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function setWatchHistory(history) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (e) { /* quota exceeded or private mode */ }
  }

  function recordWatch(foundupId, video, videoIndex) {
    var history = getWatchHistory();
    var videoId = video.video_id || video.videoId || video.id || '';

    var entry = {
      foundupId: foundupId,
      videoId: videoId,
      videoIndex: videoIndex,
      title: video.title,
      thumbnail: video.thumbnail_url || video.thumbnailUrl,
      timestamp: new Date().toISOString()
    };

    history = history.filter(function (h) {
      return !(h.foundupId === foundupId && h.videoId === videoId);
    });
    history.unshift(entry);
    if (history.length > HISTORY_MAX) {
      history = history.slice(0, HISTORY_MAX);
    }
    setWatchHistory(history);
  }

  // ─── Helpers ───
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  // ─── Public API ───
  // Changing next-clip behavior does not pause a deliberately selected current clip.
  window.mallStateRestore?.subscribeVideoOptions?.(function (options) {
    if (!options.autoplayNext) clearTimeout(autoSkipTimer);
    if (isOpen && topBar) syncTopBarButtons();
  });

  window.mallVideoPlayer = {
    openDesktopVideo: open,
    open: open,
    openFullVideo: openFullVideo,
    openPinchDestination: openPinchDestination,
    requestPlay: function () {
      if (!isPlaybackDisplayed() || !playBtn) return false;
      playBtn.click();
      return true;
    },
    openFrameDestination: openFrameDestination,
    collapseAppVideo: collapseAppVideo,
    returnToMall: returnToMall,
    resumeFromMall: resumeFromMall,
    isMallHidden: function () { return mallHidden; },
    getMode: currentModeName,
    isMemberCardVideo: isMemberCardVideo,
    selectVideo: selectVideo,
    refreshQueue: refreshQueue,
    close: close,
    expandInline: expandInline,
    openWikiTube: openWikiTube,
    collapseToFloating: collapseToFloating,
    tuck: tuck,
    untuck: untuck,
    isTucked: function () { return tucked; },
    isFloating: function () { return floating; },
    isWikiTube: function () { return wikitube; },
    setTheater: setTheater,
    isTheater: function () { return theater; },
    syncFloatingGeometry: syncFloatingGeometry,
    getQueueQuery: function () {
      if (mallHidden) return scopedQueueQuery;
      var input = memberQueueDock && !memberQueueDock.element.hidden ? memberQueueDock.input :
        theater && !queueSearchForm.hidden ? queueSearch : null;
      return input ? input.value.trim().slice(0, 300) : scopedQueueQuery;
    },
    getCurrentVideoId: function () {
      var video = currentIndex >= 0 ? currentQueue[currentIndex] : null;
      return video ? (video.video_id || video.videoId || video.id || null) : null;
    },
    getAttribution: function () {
      var source = topBar?.querySelector('.video-player-source');
      return isOpen && source && !source.hidden
        ? { title: titleEl.textContent, label: source.textContent, url: source.href } : null;
    },
    getPlaybackSnapshot: getPlaybackSnapshot,
    save: function () { if (isOpen && !mallHidden) saveBtn?.click(); },
    share: function () { if (isOpen && !mallHidden) topBar?.querySelector('[data-action="share"]')?.click(); },
    canEnterFoundUp: function () {
      var button = topBar?.querySelector('[data-action="enter"]');
      return isOpen && !!button && !button.hidden;
    },
    enterFoundUp: function () {
      var button = topBar?.querySelector('[data-action="enter"]');
      if (isOpen && !mallHidden && button && !button.hidden) button.click();
    },
    goToVideo: goToVideo,
    next: nextVideo,
    prev: prevVideo,
    isOpen: function () { return isOpen; },
    getFoundUpId: function () { return currentFoundUpId; },
    getCurrentIndex: function () { return currentIndex; },
    getQueueLength: function () { return currentQueue.length; },
    isCurrentSaved: function () {
      if (!currentFoundUpId || currentIndex < 0) return false;
      return isVideoSaved(currentFoundUpId, currentQueue[currentIndex]);
    },
    getSavedVideos: getSavedVideos,
    getSavedCount: function () {
      return Object.keys(getSavedVideos()).length;
    },
    getHistory: getWatchHistory,
    clearHistory: function () {
      setWatchHistory([]);
    }
  };
})();
