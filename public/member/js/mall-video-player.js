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
  var requestYouTubePlay = null;

  var inline = false;
  var floating = false;
  var floatingLandscapeQuery = null;
  var theater = false;
  var wikitube = false;
  var tucked = false;
  var muteOnStart = false;
  var mutedAutoplayRetryUsed = false;
  var onClose = null;
  var onSelectChange = null;
  var onQueueEnd = null;
  var onPinchReturn = null;
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
    mutedAutoplayRetryUsed = false;
    clearPlaybackTimers();
    playbackStatus = null;
    if (!keepYouTubeInstance) {
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
    if (theater) return 'theater';
    if (wikitube) return 'wikitube';
    if (floating) return tucked ? 'tucked' : 'floating';
    return 'wikitube';
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
    statusEl.textContent = message || '';
    statusEl.hidden = !message;
    var needsPlayButton = ['manual-play', 'autoplay-blocked', 'provider-unknown', 'paused'].includes(state);
    playBtn.hidden = !requestYouTubePlay || !needsPlayButton;
    updateTuckHandleLabel();
    syncFloatingGeometry();
    if (state !== 'playing') {
      container.classList.remove('chrome-hidden');
      clearTimeout(chromeTimer);
    }
    window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: { ...playbackStatus } }));
  }

  function reportHTML5(state, message) {
    var video = currentQueue[currentIndex];
    playbackStatus = {
      provider: 'html5',
      state: state,
      videoId: video?.video_id || video?.videoId || video?.id || null,
      mode: currentModeName(),
      tucked: tucked,
      queueHalted: queueHalted
    };
    statusEl.textContent = message || '';
    statusEl.hidden = !message;
    playBtn.hidden = !['manual-play', 'autoplay-blocked', 'paused', 'playback-error'].includes(state);
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
  }

  function displayedMediaArea() {
    if (!isOpen || tucked || document.hidden || !stage?.isConnected ||
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
    if (isOpen && !isPlaybackDisplayed()) pausePlayback();
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
    if (!isOpen || (!floating && !theater)) {
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
    container.style.setProperty('--floating-top', topPx + 'px');
    if (tuckHandle) tuckHandle.style.setProperty('--floating-top', (topPx + 24) + 'px');
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
        var ve = stage.querySelector('video');
        if (ve) ve.play().catch(function () { reportHTML5('autoplay-blocked', 'Tap inside the video to start playback.'); });
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
    mediaPanel.append(topBar, stage, statusEl, playBtn);

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
        var alignWithKeyboard = function () {
          var keyboard = memberQueueDock.element.contains(document.activeElement) && viewport.scale === 1
            ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
          container.style.setProperty('--video-player-keyboard', keyboard + 'px');
        };
        viewport.addEventListener('resize', alignWithKeyboard);
        viewport.addEventListener('scroll', alignWithKeyboard);
        memberQueueDock.input.addEventListener('focus', alignWithKeyboard);
        memberQueueDock.input.addEventListener('blur', alignWithKeyboard);
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
      if (e.key !== 'Escape' || !isOpen || e.isComposing) return;
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
        topBar.querySelector('[data-action="back"]').focus({ preventScroll: true });
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
    window.addEventListener('pagehide', function () {
      if (!isOpen) return;
      flushCurrentPlaybackPosition();
      pausePlayback();
    });
  }

  // ─── Mode Transitions (Zero DOM Reparenting) ───
  function releaseModalInert() {
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
      expandBtn.setAttribute('aria-label', 'Open WikiTube');
      expandBtn.title = 'Open WikiTube';
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
      prevBtn.hidden = !hasMultiQueue;
      nextBtn.hidden = !hasMultiQueue;
    }
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
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'Floating video player');
    queueSearchForm.hidden = true;
    memberQueueDock?.hide();
    clearTimeout(chromeTimer);
    syncTopBarButtons();
    syncFloatingGeometry();
  }

  function applyWikiTubePresentation(attemptImmediatePlay) {
    untuck({ silent: true });
    inline = false;
    floating = false;
    theater = false;
    wikitube = true;
    container.classList.remove('video-player-inline', 'video-player-floating', 'video-player-theater', 'chrome-hidden');
    container.classList.add('video-player-wikitube');
    container.setAttribute('role', 'dialog');
    container.setAttribute('aria-label', 'WikiTube video player');
    queueSearchForm.hidden = true;

    if (previousOverflow === null) previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

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
    topBar.querySelector('[data-action="back"]').focus({ preventScroll: true });

    if (attemptImmediatePlay && playbackStatus?.state !== 'playing' && playbackStatus?.state !== 'starting') {
      autoplayRequested = true;
      queueHalted = false;
      failedQueueIndices.delete(currentIndex);
      if (requestYouTubePlay) {
        requestYouTubePlay();
      } else {
        var ve = stage.querySelector('video');
        if (ve && ve.paused) {
          ve.play().catch(function () {
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
      detail: { mode: 'wikitube', foundupId: currentFoundUpId, videoIndex: currentIndex }
    }));
  }

  function setTheater(enabled, tile) {
    if (!isOpen) return false;
    if (tile) returnTile = tile;
    if (enabled) {
      releaseModalInert();
      untuck({ silent: true });
      inline = true;
      floating = false;
      wikitube = false;
      theater = true;
      container.classList.add('video-player-inline', 'video-player-theater');
      container.classList.remove('video-player-floating', 'video-player-wikitube', 'video-player-queue-docked', 'chrome-hidden');
      container.setAttribute('role', 'region');
      container.setAttribute('aria-label', 'Video theater');
      memberQueueDock?.hide();
      var active = document.activeElement;
      var back = topBar.querySelector('[data-action="back"]');
      syncTopBarButtons();
      queueSearchForm.hidden = !matchesQuery;
      if (active === back && !queueSearchForm.hidden) queueSearch.focus({ preventScroll: true });
      filterRail();
      renderRail();
      syncFloatingGeometry();
      return true;
    }
    if (!theater) return false;
    var activeBefore = document.activeElement;
    applyFloatingPresentation();
    if (queueSearchForm.contains(activeBefore) || queueRail.contains(activeBefore)) {
      topBar.querySelector('[data-action="back"]').focus({ preventScroll: true });
    }
    return true;
  }

  function openWikiTube() {
    if (!isOpen || wikitube || theater) return false;
    applyWikiTubePresentation(true);
    return true;
  }

  function expandInline() {
    return openWikiTube();
  }

  function collapseToFloating() {
    if (!isOpen || !wikitube) return false;
    applyFloatingPresentation();
    topBar.querySelector('[data-action="expand"]')?.focus({ preventScroll: true });
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
    if (!isOpen || !floating || tucked) return false;
    tucked = true;
    pausePlayback();
    container.classList.add('is-tucked');
    tuckHandle.hidden = false;
    updateTuckHandleLabel();
    syncFloatingGeometry();
    if (container.contains(document.activeElement)) {
      tuckHandle.focus({ preventScroll: true });
    }
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
    tucked = false;
    container.classList.remove('is-tucked');
    tuckHandle.hidden = true;
    syncFloatingGeometry();
    if (!opts?.silent && focusInsideHandle) {
      topBar.querySelector('[data-action="tuck"]')?.focus({ preventScroll: true });
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

  // ─── Open or Switch Selected Media ───
  function open(foundupId, queue, startIndex, resumeOpts) {
    if (!queue || !queue.length) return;
    ensureDOM();
    if (foundupId !== currentFoundUpId) currentEntryIdentity = undefined;

    var targetIndex = Math.max(0, Math.min(startIndex || 0, queue.length - 1));
    var wantTheater = resumeOpts?.theater === true;
    var wantFloating = !wantTheater && (resumeOpts?.floating === true || !!resumeOpts?.inlineMount);
    var canReuseOpenPlayer = isOpen && currentFoundUpId === foundupId && ytReady &&
      (resumeOpts?.preserveInstance !== false);

    // If switching videos within an already-open player for the same FoundUp, keep live <iframe>!
    if (canReuseOpenPlayer && currentQueue.length === queue.length) {
      currentQueue = queue;
      if (resumeOpts?.returnTile || resumeOpts?.returnFocusTo) {
        returnTile = resumeOpts.returnTile || resumeOpts.returnFocusTo;
      }
      if (resumeOpts?.onClose) onClose = resumeOpts.onClose;
      if (resumeOpts?.onSelectChange) onSelectChange = resumeOpts.onSelectChange;
      onQueueEnd = resumeOpts?.onQueueEnd || null;
      onPinchReturn = resumeOpts?.onPinchReturn || null;
      autoplayRequested = resumeOpts?.autoplay !== false;
      muteOnStart = wantTheater || resumeOpts?.muted === true;
      failedQueueIndices.clear();
      consecutiveAutoSkips = 0;
      queueHalted = false;
      if (tucked) untuck({ silent: true });
      if (wantTheater && !theater) setTheater(true, returnTile);
      else if (wantFloating && !floating) applyFloatingPresentation();
      else if (!wantTheater && !wantFloating && !wikitube) applyWikiTubePresentation(false);
      goToVideo(targetIndex, { explicitUserSelect: true });
      return;
    }

    if (isOpen) close({ restore: false });

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
    autoplayRequested = resumeOpts?.autoplay !== false;
    muteOnStart = wantTheater || resumeOpts?.muted === true;
    matchesQuery = resumeOpts?.matchesQuery ||
      (document.getElementById('redDogAnchor')?.querySelector(':scope > .mall-member-search-dock')
        ? window.mallTileField?.matchesVideoQuery : null);
    queueSearch.value = resumeOpts?.query || '';
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

    if (wantTheater) {
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
    if (!isOpen || index < 0 || index >= currentQueue.length) return false;
    if (opts?.returnTile) returnTile = opts.returnTile;
    if (tucked) untuck({ silent: true });
    autoplayRequested = opts?.autoplay !== false;
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

    flushCurrentPlaybackPosition();
    pausePlayback();
    pendingResumeSeconds = null;

    isOpen = false;
    untuck({ silent: true });
    container.classList.remove(
      'open',
      'video-player-inline',
      'video-player-floating',
      'video-player-theater',
      'video-player-wikitube',
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
    queueContinuation = null;
    if (afterClose) afterClose(restore);

    if (returnTile) {
      var tile = returnTile.isConnected ? returnTile : document.querySelector(
        '#mallTileField .mall-tile[data-index="' + Number(returnTile.dataset.index) + '"]'
      );
      if (restore) {
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

    window.dispatchEvent(new CustomEvent('videoPlayerClose'));
  }

  // ─── Queue Navigation & Bounded Sequential Auto-Advance ───
  function activeSequence() {
    return filteredIndices || currentQueue.map(function (_, index) { return index; });
  }

  function goToVideo(index, navOpts) {
    if (index < 0 || index >= currentQueue.length) return;
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
    currentIndex = index;
    renderVideo(currentQueue[index], true);
    updateRailSelection();
    resetChromeTimer();

    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[index]));
    recordWatch(currentFoundUpId, currentQueue[index], index);
    onSelectChange?.(currentIndex, currentQueue[index]);

    window.dispatchEvent(new CustomEvent('videoPlayerNavigate', {
      detail: { foundupId: currentFoundUpId, videoIndex: index }
    }));
  }

  // A scoped data owner may append one bounded page at a loaded queue boundary.
  // Closing, pausing, hiding or changing selection invalidates deferred playback.
  function continueQueue(explicit) {
    if (!onQueueEnd || filteredIndices || queueContinuation || !canStartYouTube()) return false;
    var owner = currentFoundUpId;
    var queue = currentQueue;
    var index = currentIndex;
    var generation = renderGeneration;
    var intent = playbackIntentEpoch;
    var load = onQueueEnd;
    var task = Promise.resolve().then(function () { return load(); });
    queueContinuation = task;
    task.then(function (added) {
      if (!added || !isOpen || currentFoundUpId !== owner || currentQueue !== queue ||
          currentIndex !== index || renderGeneration !== generation ||
          playbackIntentEpoch !== intent || filteredIndices || !canStartYouTube()) return;
      var next = index + 1;
      if (next >= currentQueue.length) return;
      refreshQueue();
      autoplayRequested = true;
      goToVideo(next, { explicitUserSelect: explicit, fromAutoAdvance: !explicit, preserveFailures: !explicit });
      showHint('Next');
    }).catch(function () {
      if (isOpen && currentFoundUpId === owner) showHint('Could not load more videos. Try Next again.');
    }).finally(function () {
      if (queueContinuation === task) queueContinuation = null;
    });
    return true;
  }

  function refreshQueue() {
    if (!isOpen) return;
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

  function nextVideo() {
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    var next = pos >= 0 ? seq[pos + 1] : currentIndex + 1;
    if (next !== undefined && next < currentQueue.length) {
      autoplayRequested = true;
      goToVideo(next, { explicitUserSelect: true });
      showHint('Next');
    } else if (!continueQueue(true)) {
      showHint('End of queue');
    }
  }

  function prevVideo() {
    var seq = activeSequence();
    var pos = seq.indexOf(currentIndex);
    var previous = pos >= 0 ? seq[pos - 1] : currentIndex - 1;
    if (previous !== undefined && previous >= 0) {
      autoplayRequested = true;
      goToVideo(previous, { explicitUserSelect: true });
      showHint('Previous');
    }
  }

  function handleVideoEnded() {
    if (!isPlaybackDisplayed()) { pausePlayback(); return; }
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

  function scheduleWikiTubeRecovery(baseMessage, errorState, code) {
    failedQueueIndices.add(currentIndex);
    if (!isPlaybackDisplayed()) {
      pausePlayback();
      queueHalted = true;
      reportYouTube(errorState, baseMessage, code);
      return;
    }
    if (!wikitube) {
      reportYouTube(errorState, baseMessage, code);
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
      reportYouTube(errorState, baseMessage + ' Advancing to next video…', code);
      clearTimeout(autoSkipTimer);
      var expectedGen = renderGeneration;
      autoSkipTimer = setTimeout(function () {
        autoSkipTimer = null;
        if (!isOpen || !wikitube || renderGeneration !== expectedGen) return;
        if (!isPlaybackDisplayed()) { pausePlayback(); return; }
        autoplayRequested = true;
        goToVideo(nextCandidate, { fromAutoAdvance: true, preserveFailures: true });
      }, getAutoSkipDelayMs());
    } else {
      queueHalted = true;
      reportYouTube(errorState, baseMessage + ' Queue stopped — no playable videos remaining.', code);
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
        reportYouTube('autoplay-blocked', 'Your browser blocked automatic playback. Use Play video or tap inside the player.');
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
        var focusTarget = theater ? iframe : topBar.querySelector('[data-action="back"]');
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
                var focusTarget = theater ? iframe : topBar.querySelector('[data-action="back"]');
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

  // ─── Render Video ───
  function renderVideo(video, allowReuse) {
    if (!video) return;
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

    var embedUrl = video.embed_url || video.embedUrl;
    var sourceUrl = video.source_url || video.sourceUrl;
    var youtube = parseYouTubeEmbed(embedUrl);
    var ytId = extractYouTubeVideoId(embedUrl);
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
      stage.innerHTML = '<video src="' + esc(sourceUrl) + '"' + (muteOnStart ? ' muted' : '') +
        (autoplayRequested ? ' autoplay' : '') + ' controls playsinline></video>';
      var ve = stage.querySelector('video');
      if (ve) {
        ve.addEventListener('playing', function () {
          if (!isPlaybackDisplayed()) { pausePlayback(); return; }
          consecutiveAutoSkips = 0;
          queueHalted = false;
          reportHTML5('playing', '');
        });
        ve.addEventListener('pause', function () {
          if (!ve.ended) {
            playbackIntentEpoch++;
            autoplayRequested = false;
            reportHTML5('paused', 'Playback paused.');
          }
        });
        ve.addEventListener('ended', function () {
          reportHTML5('ended', '');
          handleVideoEnded();
        });
        ve.addEventListener('error', function () {
          scheduleWikiTubeRecovery('Media file could not be loaded.', 'playback-error', 5);
        });
        if (autoplayRequested) {
          var playPromise = ve.play?.();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(function () {
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
    var input = theater ? queueSearch : null;
    if (memberQueueDock && !memberQueueDock.element.hidden) input = memberQueueDock.input;
    var query = input ? input.value.trim().slice(0, 300) : '';
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
    event.preventDefault();
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
    if (media && !media.paused && !media.ended) return;
    var first = filteredIndices[0];
    autoplayRequested = true;
    if (first !== currentIndex) goToVideo(first, { explicitUserSelect: true });
    else if (requestYouTubePlay) requestYouTubePlay();
    else if (media) media.play().catch(function () {});
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

        if (floating && scale >= PINCH_OUT_RATIO && delta >= PINCH_MIN_DELTA_PX) {
          pinchConsumed = true;
          openWikiTube();
        } else if ((floating || wikitube) && scale <= PINCH_IN_RATIO && -delta >= PINCH_MIN_DELTA_PX) {
          pinchConsumed = true;
          pinchReturn();
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
      if (floating && e.scale >= PINCH_OUT_RATIO) {
        pinchConsumed = true;
        openWikiTube();
      } else if ((floating || wikitube) && e.scale <= PINCH_IN_RATIO) {
        pinchConsumed = true;
        pinchReturn();
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
      if (isInteractiveInputTarget(e.target) || !e.target?.closest?.('.video-player-top-bar')) return;
      e.preventDefault();
      if (e.deltaY < 0 && floating) {
        openWikiTube();
      } else if (e.deltaY > 0 && (floating || wikitube)) {
        pinchReturn();
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

    if (floating && !tucked) {
      if (dir === 'right' && dx >= TUCK_SWIPE_PX && absDx > absDy * 1.4) {
        tuck();
      }
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

    tuckHandle.addEventListener('click', function () {
      untuck();
    });

    tuckHandle.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) return;
      handleStartX = e.touches[0].clientX;
      handleStartY = e.touches[0].clientY;
      handleTracking = true;
    }, { passive: true });

    tuckHandle.addEventListener('touchmove', function (e) {
      if (!handleTracking || e.touches.length !== 1) return;
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
      if (dx <= -UNTUCK_SWIPE_PX && Math.abs(dx) > Math.abs(dy)) {
        untuck();
      }
    }, { passive: true });
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
        openWikiTube();
        break;
      case 'float':
        collapseToFloating();
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
    if (!isOpen || theater) return;
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
  window.mallVideoPlayer = {
    openDesktopVideo: open,
    open: open,
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
      var input = (memberQueueDock && (!memberQueueDock.element.hidden || returnScroll)) ? memberQueueDock.input : queueSearch;
      return input?.value.trim().slice(0, 300) || '';
    },
    getCurrentVideoId: function () {
      var video = currentIndex >= 0 ? currentQueue[currentIndex] : null;
      return video ? (video.video_id || video.videoId || video.id || null) : null;
    },
    getPlaybackSnapshot: getPlaybackSnapshot,
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
