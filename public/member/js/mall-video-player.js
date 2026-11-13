/**
 * Mall Video Player — shared in-context and immersive video playback.
 *
 * Manages:
 *   - Fullscreen video playback from FoundUp queue
 *   - Top action bar (back, share, save, info, more)
 *   - Bottom queue rail with auto-hide
 *   - Gesture navigation (swipe, pinch, tap)
 *   - Queue-constrained playback (no cross-FoundUp drift)
 *
 * Gestures:
 *   - swipe-up = next video in queue
 *   - swipe-down = exit fullscreen
 *   - pinch-in = exit fullscreen (via touch events)
 *   - tap = toggle chrome visibility
 *   - swipe-left = save hook (stub)
 *   - swipe-right = dismiss hook (stub)
 *
 * Depends on:
 *   - gesture-engine.js (window.gestureZone)
 *   - CSS: mall-video-player.css
 */
(function () {
  'use strict';

  // ─── Constants ───
  var RAIL_AUTO_HIDE_MS = 4000;
  var CHROME_AUTO_HIDE_MS = 3000;
  var PINCH_THRESHOLD = 0.7; // scale < this = exit
  var YOUTUBE_TIMEOUT_MS = 12000;
  var YOUTUBE_HOSTS = ['www.youtube.com', 'youtube.com', 'www.youtube-nocookie.com', 'youtube-nocookie.com'];

  // ─── State ───
  var container = null;
  var stage = null;
  var topBar = null;
  var queueRail = null;
  var queueTrack = null;
  var mediaPanel = null;
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
  var theater = false;
  var muteOnStart = false;
  var onClose = null;
  var autoplayRequested = true;
  var previousOverflow = null;
  var inertElements = [];
  var stageObserver = null;
  var renderGeneration = 0;
  var playbackTimer = null;
  var playbackStatus = null;

  var isOpen = false;
  var currentQueue = [];       // Array of video objects from one FoundUp
  var currentFoundUpId = null; // Constrains queue
  var currentIndex = -1;
  var gestureRef = null;
  var railTimer = null;
  var chromeTimer = null;
  var initialPinchDistance = 0;
  var pinchTarget = null;

  // ─── localStorage Keys ───
  var SAVED_KEY = 'pfmall_saved_videos';
  var returnTile = null;
  var memberQueueDock = null;
  var railQuery = null;
  var returnScroll = null;
  var scopedPlayer = false;
  var HISTORY_KEY = 'pfmall_watch_history';
  var HISTORY_MAX = 50; // Max history entries
  /** Local-only resume: omit sub-threshold & “finished” positions (HTML5 video only; embeds cannot read time). */
  var MIN_RESUME_SECONDS = 5;
  var COMPLETE_RATIO = 0.97;
  var pendingResumeSeconds = null;
  var ytPlayer = null;           // YouTube IFrame API player instance
  var ytLoad = null;

  // ─── YouTube IFrame API ───
  function ensureYouTubeAPI() {
    if (window.YT?.Player) return Promise.resolve();
    if (ytLoad) return ytLoad;
    ytLoad = new Promise(function(resolve, reject) {
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
    }).finally(function() { ytLoad = null; });
    return ytLoad;
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
    if (ytPlayer) {
      try { ytPlayer.destroy(); } catch (e) { /* already destroyed */ }
      ytPlayer = null;
    }
  }

  function resetPlayback() {
    renderGeneration += 1;
    clearTimeout(playbackTimer);
    playbackStatus = null;
    requestYouTubePlay = null;
    playBtn.hidden = true;
    statusEl.hidden = true;
    statusEl.textContent = '';
    destroyYTPlayer();
    stage.replaceChildren();
  }

  function reportYouTube(state, message, code, providerState) {
    var video = currentQueue[currentIndex];
    playbackStatus = { provider: 'youtube', state: state, videoId: video?.video_id || null };
    if (code !== undefined) playbackStatus.code = code;
    if (providerState !== undefined) playbackStatus.providerState = providerState;
    statusEl.textContent = message || '';
    statusEl.hidden = !message;
    playBtn.hidden = !requestYouTubePlay || !['manual-play', 'autoplay-blocked', 'provider-unknown', 'paused'].includes(state);
    if (inline && !theater && !returnScroll &&
        (state === 'manual-play' || state === 'autoplay-blocked') && !playBtn.hidden && canStartYouTube()) {
      playBtn.scrollIntoView({ block: 'nearest' });
    }
    window.dispatchEvent(new CustomEvent('mallVideoPlayback', { detail: { ...playbackStatus } }));
  }

  function getPlaybackSnapshot() {
    if (!playbackStatus) return null;
    var positionSeconds = null;
    try {
      var time = ytPlayer?.getCurrentTime?.();
      if (Number.isFinite(time)) positionSeconds = time;
    } catch (e) { /* provider may already be gone */ }
    return { ...playbackStatus, positionSeconds };
  }

  function pausePlayback() {
    autoplayRequested = false;
    try { ytPlayer?.pauseVideo?.(); } catch (e) { /* provider not ready */ }
    stage?.querySelector('video')?.pause();
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

  // ─── Initialize DOM ───
  function ensureDOM() {
    if (container) return;

    container = document.createElement('div');
    container.id = 'videoPlayerFullscreen';
    container.className = 'video-player-fullscreen';
    container.setAttribute('aria-label', 'Fullscreen video player');
    container.setAttribute('role', 'dialog');
    container.innerHTML = [
      '<div class="video-player-top-bar">',
      '  <div class="video-player-top-bar-left">',
      '    <button class="video-player-btn" data-action="back" aria-label="Back">',
      '      <svg viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>',
      '    </button>',
      '    <div class="video-player-caption">',
      '      <span class="video-player-title"></span>',
      '      <a class="video-player-source" target="_blank" rel="noopener noreferrer" hidden></a>',
      '    </div>',
      '  </div>',
      '  <div class="video-player-top-bar-right">',
      '    <button type="button" class="video-player-btn" data-action="expand" aria-label="Expand video" hidden>',
      '      <svg viewBox="0 0 24 24"><path d="M14 4h6v6m0-6-6 6M10 20H4v-6m0 6 6-6"/></svg>',
      '    </button>',
      '    <button class="video-player-btn video-player-enter-btn" data-action="enter" aria-label="Enter FoundUp">',
      '      <svg viewBox="0 0 24 24"><path d="M15 3h6v6M14 10l6.1-6.1M9 21H3v-6M10 14l-6.1 6.1"/></svg>',
      '    </button>',
      '    <button class="video-player-btn" data-action="save" aria-label="Save">',
      '      <svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
      '    </button>',
      '    <button class="video-player-btn" data-action="share" aria-label="Share">',
      '      <svg viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/></svg>',
      '    </button>',
      '    <button class="video-player-btn" data-action="more" aria-label="More options">',
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

    stage = container.querySelector('.video-player-stage');
    statusEl = container.querySelector('.video-player-status');
    playBtn = container.querySelector('.video-player-manual-play');
    playBtn.addEventListener('click', function() { requestYouTubePlay?.(); });
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
      function() {
        if (scopedPlayer) return window.mallVideoProjection?.openScopedRedDog?.(currentFoundUpId);
        close();
        window.redDog?.open?.();
        document.querySelector('#accountPlane.open button:not([hidden])')?.focus();
      }
    );
    var queuePanel = document.createElement('div');
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
        var alignWithKeyboard = function() {
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

    // Attach listeners
    topBar.addEventListener('click', handleTopBarClick);
    queueTrack.addEventListener('click', handleRailClick);
    edgeTrigger.addEventListener('touchstart', showRail, { passive: true });
    edgeTrigger.addEventListener('mouseenter', showRail);

    // Keyboard
    // Dismiss the innermost control before the shell's expanded-lane Escape handler.
    document.addEventListener('keydown', function(e) {
      if (e.key !== 'Escape' || !isOpen || e.isComposing) return;
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
      if (memberQueueDock && !memberQueueDock.element.hidden) {
        e.preventDefault();
        e.stopPropagation();
        close();
        return;
      }
      if (returnTile && !scopedPlayer) handleKeydown(e);
    }, true);
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('visibilitychange', function() {
      if (isOpen && document.hidden) pausePlayback();
    });
    window.addEventListener('pagehide', function() {
      if (!isOpen) return;
      flushCurrentPlaybackPosition();
      pausePlayback();
    });
  }

  function enterImmersive() {
    inline = false;
    topBar.querySelector('[data-action="back"]').hidden = false;
    container.classList.remove('video-player-inline');
    container.setAttribute('role', 'dialog');
    container.setAttribute('aria-label', 'Fullscreen video player');
    topBar.querySelector('[data-action="expand"]').hidden = true;
    topBar.querySelector('[data-action="back"]').setAttribute('aria-label', 'Back');
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (returnTile || matchesQuery) {
      container.setAttribute('aria-modal', 'true');
      var member = document.getElementById('memberArea');
      // An inline iframe keeps its parent when expanded. Inert its siblings,
      // rather than an ancestor that also contains the active player.
      if (member && member.contains(container)) {
        for (var node = container; node !== member; node = node.parentElement) {
          Array.from(node.parentElement.children).forEach(function(sibling) {
            if (sibling !== node && !sibling.inert) {
              sibling.inert = true;
              inertElements.push(sibling);
            }
          });
        }
      } else if (member && !member.inert) {
        member.inert = true;
        inertElements.push(member);
      }
    }
    attachGestures();
    if (memberQueueDock && matchesQuery && (!scopedPlayer || memberQueueDock.setScoped)) {
      memberQueueDock.setScoped?.(scopedPlayer);
      memberQueueDock.element.hidden = false;
      container.classList.add('video-player-queue-docked');
      filterRail();
    }
    resetChromeTimer();
    if (returnTile || matchesQuery) topBar.querySelector('[data-action="back"]').focus({ preventScroll: true });
  }

  function setTheater(enabled, tile) {
    if (!isOpen || !inline) return false;
    if (tile) returnTile = tile;
    theater = enabled;
    setPinchTarget(!enabled && returnTile ? topBar : null);
    container.classList.toggle('video-player-theater', enabled);
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', enabled ? 'Video theater' : 'Inline video player');
    topBar.querySelector('[data-action="expand"]').hidden = enabled;
    var back = topBar.querySelector('[data-action="back"]');
    var active = document.activeElement;
    back.hidden = enabled;
    back.setAttribute('aria-label', 'Close player');
    queueSearchForm.hidden = !enabled || !matchesQuery;
    if (enabled && active === back && !queueSearchForm.hidden) queueSearch.focus({ preventScroll: true });
    if (!enabled && (queueSearchForm.contains(active) || queueRail.contains(active))) back.focus({ preventScroll: true });
    filterRail();
    return true;
  }

  function expandInline() {
    if (!isOpen || !inline || theater) return false;
    stageObserver?.disconnect();
    stageObserver = null;
    enterImmersive();
    return true;
  }

  // ─── Open selected media ───
  function open(foundupId, queue, startIndex, resumeOpts) {
    if (!queue || !queue.length) return;

    ensureDOM();
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

    scopedPlayer = !!resumeOpts?.returnTile;
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
    autoplayRequested = resumeOpts?.autoplay !== false;
    muteOnStart = resumeOpts?.theater === true || resumeOpts?.muted === true;
    matchesQuery = resumeOpts?.matchesQuery ||
      (document.getElementById('redDogAnchor')?.querySelector(':scope > .mall-member-search-dock')
        ? window.mallTileField?.matchesVideoQuery : null);
    queueSearch.value = resumeOpts?.query || '';
    if (memberQueueDock) memberQueueDock.input.value = resumeOpts?.queueQuery || '';
    filteredIndices = null;
    railQuery = null;
    container.classList.toggle('scoped-player', scopedPlayer);
    container.classList.toggle('desktop-poster-player', !!returnScroll);
    mediaPanel.scrollTop = 0;

    currentFoundUpId = foundupId;
    currentQueue = queue;
    currentIndex = Math.max(0, Math.min(startIndex || 0, queue.length - 1));
    isOpen = true;

    container.classList.add('open');
    inline = !!resumeOpts?.inlineMount;
    if (inline) {
      var mount = resumeOpts.inlineMount;
      if (typeof mount === 'function') mount = mount();
      mount.appendChild(container);
      container.classList.add('video-player-inline');
      if (returnScroll) {
        container.setAttribute('role', 'region');
        container.setAttribute('aria-label', 'Inline video player');
        topBar.querySelector('[data-action="expand"]').hidden = false;
        var closeButton = topBar.querySelector('[data-action="back"]');
        closeButton.hidden = false;
        closeButton.setAttribute('aria-label', 'Close player');
        setPinchTarget(topBar);
        renderRail();
      } else {
        setTheater(resumeOpts?.theater === true);
      }
      if (!theater) {
        if (returnScroll) container.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
        else container.scrollIntoView({ block: 'nearest' });
        topBar.querySelector('[data-action="back"]').focus({ preventScroll: true });
      }
      if (typeof IntersectionObserver !== 'undefined') {
        var observer = new IntersectionObserver(function(entries) {
          if (stageObserver === observer && inline && entries.some(function(entry) { return entry.intersectionRatio <= 0.5; })) {
            pausePlayback();
          }
        }, { threshold: [0.5] });
        stageObserver = observer;
        stageObserver.observe(stage);
      }
    } else {
      enterImmersive();
      filterRail();
    }

    renderVideo(currentQueue[currentIndex]);
    if (inline) resumeOpts.alignInline?.();

    // Update save button state
    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[currentIndex]));

    // Record watch history
    recordWatch(currentFoundUpId, currentQueue[currentIndex], currentIndex);

    // Dispatch event for external listeners
    window.dispatchEvent(new CustomEvent('videoPlayerOpen', {
      detail: { foundupId: foundupId, videoIndex: currentIndex }
    }));
  }

  // ─── Close and return ───
  function close(options) {
    if (!isOpen) return;
    var restore = options?.restore !== false;

    flushCurrentPlaybackPosition();
    pendingResumeSeconds = null;

    isOpen = false;
    container.classList.remove('open', 'video-player-inline', 'video-player-theater', 'video-player-queue-docked');
    theater = false;
    queueSearchForm.hidden = true;
    memberQueueDock?.hide();
    if (previousOverflow !== null) document.body.style.overflow = previousOverflow;
    previousOverflow = null;
    inertElements.forEach(function(element) { element.inert = false; });
    inertElements = [];
    stageObserver?.disconnect();
    stageObserver = null;

    // Stop video
    resetPlayback();
    if (container.parentNode !== document.body) document.body.appendChild(container);
    inline = false;

    // Cleanup
    if (gestureRef) { gestureRef.destroy(); gestureRef = null; }
    setPinchTarget(null);
    clearTimeout(railTimer);
    clearTimeout(chromeTimer);

    currentQueue = [];
    currentFoundUpId = null;
    currentIndex = -1;

    var afterClose = onClose;
    onClose = null;
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
            // Density reflow can move the tile far beyond its old scroll offset.
            var anchor = Math.max(0, returnScroll.tileTop - top);
            top = tile.offsetTop - Math.min(anchor, Math.max(0, field.clientHeight - tile.offsetHeight));
          }
          field.scrollTo({ top: top, left: returnScroll.left, behavior: 'instant' });
          returnScroll.rowTrack?.scrollTo({ left: returnScroll.rowLeft, behavior: 'instant' });
        }
      }
      returnTile = null;
    }
    container.removeAttribute('aria-modal');
    returnScroll = null;

    window.dispatchEvent(new CustomEvent('videoPlayerClose'));
  }

  // ─── Navigate Queue ───
  function goToVideo(index) {
    if (index < 0 || index >= currentQueue.length) return;
    if (theater || returnScroll || container.classList.contains('video-player-queue-docked')) {
      if (index === currentIndex) return;
      autoplayRequested = true;
      try { muteOnStart = ytPlayer?.isMuted?.() ?? muteOnStart; } catch (e) { /* provider not ready */ }
    }
    flushCurrentPlaybackPosition();
    pendingResumeSeconds = null;
    currentIndex = index;
    renderVideo(currentQueue[index]);
    updateRailSelection();
    resetChromeTimer();

    // Update save button state
    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[index]));

    // Record watch history
    recordWatch(currentFoundUpId, currentQueue[index], index);

    window.dispatchEvent(new CustomEvent('videoPlayerNavigate', {
      detail: { foundupId: currentFoundUpId, videoIndex: index }
    }));
  }

  function nextVideo() {
    var next = filteredIndices ? filteredIndices[filteredIndices.indexOf(currentIndex) + 1] : currentIndex + 1;
    if (next !== undefined && next < currentQueue.length) {
      goToVideo(next);
      showHint('Next');
    } else {
      showHint('End of queue');
    }
  }

  function prevVideo() {
    var previous = filteredIndices ? filteredIndices[filteredIndices.indexOf(currentIndex) - 1] : currentIndex - 1;
    if (previous >= 0) {
      goToVideo(previous);
      showHint('Previous');
    }
  }

  function handleVideoEnded() {
    if (inline && !theater) return;
    autoplayRequested = true;
    nextVideo();
  }

  function canStartYouTube() {
    if (document.hidden) return false;
    var rect = stage.getBoundingClientRect();
    if (rect.width < 200 || rect.height < 200) return false;
    var bounds = inline ? container.closest('.mall-tile-field-wrapper')?.getBoundingClientRect()
      : container.classList.contains('video-player-queue-docked') && mediaPanel.getBoundingClientRect();
    var track = inline && container.closest('.mall-category-track')?.getBoundingClientRect();
    var width = Math.max(0, Math.min(rect.right, window.innerWidth, bounds?.right ?? Infinity, track?.right ?? Infinity) -
      Math.max(rect.left, 0, bounds?.left ?? 0, track?.left ?? 0));
    var height = Math.max(0, Math.min(rect.bottom, window.innerHeight, bounds?.bottom ?? Infinity, track?.bottom ?? Infinity) -
      Math.max(rect.top, 0, bounds?.top ?? 0, track?.top ?? 0));
    return width * height > rect.width * rect.height / 2;
  }

  var YOUTUBE_ERRORS = {
    2: ['configuration', 'YouTube rejected the video configuration.'],
    5: ['playback-error', 'YouTube could not play this video in this browser.'],
    100: ['unavailable', 'This video is unavailable on YouTube.'],
    101: ['embedding-disabled', 'YouTube refused to play this embedded video.'],
    150: ['embedding-disabled', 'YouTube refused to play this embedded video.'],
    153: ['client-identification', 'YouTube could not identify this embedded player.']
  };

  function renderYouTube(embed, videoId) {
    var generation = renderGeneration;
    var src = new URL('/embed/' + videoId, embed.origin);
    src.searchParams.set('enablejsapi', '1');
    src.searchParams.set('playsinline', '1');
    src.searchParams.set('controls', '1');
    src.searchParams.set('rel', '0');
    if (/^https?:$/.test(window.location.protocol)) src.searchParams.set('origin', window.location.origin);

    var iframe = document.createElement('iframe');
    iframe.title = 'YouTube video · ' + titleEl.textContent;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.src = src.href;
    stage.appendChild(iframe);

    function current() {
      return isOpen && generation === renderGeneration && iframe.isConnected;
    }
    function waitForPlayback(state, message) {
      clearTimeout(playbackTimer);
      playbackTimer = setTimeout(function() {
        if (!current()) return;
        autoplayRequested = false;
        reportYouTube(state, message);
      }, YOUTUBE_TIMEOUT_MS);
    }
    function failed(state, message, code) {
      if (!current()) return;
      clearTimeout(playbackTimer);
      autoplayRequested = false;
      reportYouTube(state, message, code);
    }
    reportYouTube('loading', 'Loading YouTube player…');
    waitForPlayback('timeout', 'YouTube did not finish loading. Try its Play control or open the source.');

    ensureYouTubeAPI().then(function() {
      if (!current()) return;
      ytPlayer = new window.YT.Player(iframe, {
        events: {
          onReady: function(ev) {
            if (!current()) return;
            clearTimeout(playbackTimer);
            if (muteOnStart) ev.target.mute();
            reportYouTube('ready');
            requestYouTubePlay = function() {
              if (!current()) return;
              if (!canStartYouTube()) stage.scrollIntoView({ block: 'nearest' });
              if (!canStartYouTube()) {
                reportYouTube('manual-play', 'Bring the video into view before playing.');
                return;
              }
              waitForPlayback('provider-unknown', 'YouTube did not start. Try its Play control or open the source.');
              if (document.activeElement === playBtn) {
                var focusTarget = theater ? iframe : topBar.querySelector('[data-action="back"]');
                focusTarget.focus({ preventScroll: true });
              }
              reportYouTube('starting', 'Starting video…');
              try { ev.target.playVideo(); }
              catch (e) { failed('provider-unknown', 'YouTube did not start. Try again or open the source.'); }
            };
            if (autoplayRequested && canStartYouTube()) {
              requestYouTubePlay();
            } else {
              reportYouTube('manual-play', 'The video is ready to play.');
            }
          },
          onStateChange: function(ev) {
            if (!current()) return;
            var state = ev.data;
            if (state === 1 || (state === 2 && requestYouTubePlay) || state === 0) {
              clearTimeout(playbackTimer);
              reportYouTube({ 1: 'playing', 2: 'paused', 0: 'ended' }[state],
                state === 2 ? 'Playback paused.' : '', undefined, state);
              if (state === 0) handleVideoEnded();
            } else {
              window.dispatchEvent(new CustomEvent('mallVideoPlayback', {
                detail: { provider: 'youtube', state: 'provider-state', videoId: videoId, providerState: state }
              }));
            }
          },
          onError: function(ev) {
            var result = YOUTUBE_ERRORS[ev.data] || ['provider-unknown', 'YouTube could not start this video.'];
            failed(result[0], result[1] + ' Open the source to check it on YouTube.', ev.data);
          },
          onAutoplayBlocked: function() {
            failed('autoplay-blocked', 'Your browser blocked automatic playback. Use Play video to try again.');
          }
        }
      });
    }).catch(function() {
      failed('timeout', 'YouTube controls may still work. Try Play in the video or open the source.');
    });
  }

  // ─── Render Video ───
  function renderVideo(video) {
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

    resetPlayback();
    titleEl.textContent = video.title || '';

    // Determine embed type
    var embedUrl = video.embed_url || video.embedUrl;
    var sourceUrl = video.source_url || video.sourceUrl;
    var youtube = parseYouTubeEmbed(embedUrl);
    var ytId = extractYouTubeVideoId(embedUrl);
    container.classList.toggle('provider-youtube', !!youtube);

    if (ytId) {
      pendingResumeSeconds = null; // cannot read playback time from YouTube embed; resume N/A
      if (!originalUrl) {
        sourceLink.href = 'https://www.youtube.com/watch?v=' + ytId;
        sourceLink.textContent = 'Source on YouTube';
        sourceLink.setAttribute('aria-label', 'Open source on YouTube');
        sourceLink.hidden = false;
      }
      renderYouTube(youtube, ytId);
    } else if (youtube || (scopedPlayer && embedUrl)) {
      pendingResumeSeconds = null;
      reportYouTube('configuration', 'The YouTube video ID is invalid.', 2);
    } else if (embedUrl) {
      pendingResumeSeconds = null;
      // Non-YouTube embed (Vimeo, etc.) — raw iframe, no ended detection
      stage.innerHTML = '<iframe src="' + esc(embedUrl) + '?autoplay=1&rel=0" allowfullscreen allow="autoplay; encrypted-media"></iframe>';
    } else if (sourceUrl && sourceUrl.match(/\.(mp4|webm|ogg)$/i)) {
      // Direct video file — resume seek when pendingResumeSeconds is valid
      var resumeTarget = pendingResumeSeconds;
      pendingResumeSeconds = null;
      stage.innerHTML = '<video src="' + esc(sourceUrl) + '"' + (muteOnStart ? ' muted' : '') +
        (autoplayRequested ? ' autoplay' : '') + ' controls playsinline></video>';
      var ve = stage.querySelector('video');
      if (ve) {
        // Queue autoplay: advance to next video when current ends
        ve.addEventListener('ended', handleVideoEnded);

        if (resumeTarget != null) {
          function applyResumeSeek() {
            var dur = ve.duration;
            if (!isFinite(dur)) dur = 0;
            var n = normalizeResumeSeconds(resumeTarget, dur);
            if (n == null) return;
            var cap = dur > 0 ? Math.min(n, Math.max(MIN_RESUME_SECONDS, dur - 0.25)) : n;
            try {
              ve.currentTime = cap;
            } catch (err) { /* clamp edge */ }
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
      pendingResumeSeconds = null;
      // Placeholder
      stage.innerHTML = '<div class="video-player-loading">Loading video...</div>';
    }
  }

  // ─── Render Rail ───
  function filterRail() {
    var input = theater ? queueSearch : null;
    if (memberQueueDock && !memberQueueDock.element.hidden) input = memberQueueDock.input;
    var query = input ? input.value.trim().slice(0, 300) : '';
    if (query === railQuery) return;
    railQuery = query;
    filteredIndices = query && matchesQuery ? currentQueue.reduce(function(indices, video, index) {
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
    if (result !== currentIndex) goToVideo(result);
    else if (playbackStatus?.state !== 'playing') requestYouTubePlay?.();
  }

  function playMemberSearchResult() {
    filterRail();
    if (!filteredIndices?.length || ['playing', 'loading', 'starting', 'provider-state'].includes(playbackStatus?.state)) return;
    var media = stage.querySelector('video');
    if (media && !media.paused && !media.ended) return;
    var first = filteredIndices[0];
    if (first !== currentIndex) goToVideo(first);
    else if (requestYouTubePlay) requestYouTubePlay();
    else if (media) media.play().catch(function() {});
  }

  function renderRail() {
    var indices = filteredIndices || currentQueue.map(function(_, index) { return index; });
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

    // Scroll active into view
    var activeItem = queueTrack.querySelector('.video-player-queue-item.active');
    if (activeItem) {
      queueTrack.scrollTo({
        left: activeItem.offsetLeft - (queueTrack.clientWidth - activeItem.offsetWidth) / 2,
        behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
      });
    }
  }

  // ─── Rail Visibility ───
  function showRail() {
    queueRail.classList.add('visible');
    clearTimeout(railTimer);
    railTimer = setTimeout(hideRail, RAIL_AUTO_HIDE_MS);
  }

  function hideRail() {
    queueRail.classList.remove('visible');
  }

  // ─── Chrome Visibility ───
  function toggleChrome() {
    container.classList.toggle('chrome-hidden');
    if (!container.classList.contains('chrome-hidden')) {
      resetChromeTimer();
    }
  }

  function resetChromeTimer() {
    container.classList.remove('chrome-hidden');
    clearTimeout(chromeTimer);
    if (inline) return;
    chromeTimer = setTimeout(function () {
      container.classList.add('chrome-hidden');
    }, CHROME_AUTO_HIDE_MS);
  }

  // ─── Gesture Hint ───
  function showHint(text) {
    gestureHint.textContent = text;
    gestureHint.classList.add('show');
    setTimeout(function () {
      gestureHint.classList.remove('show');
    }, 800);
  }

  // ─── Gestures ───
  function attachGestures() {
    if (gestureRef) gestureRef.destroy();
    if (!window.gestureZone) return;

    gestureRef = window.gestureZone(stage, {
      onSwipe: function (dir) {
        resetChromeTimer();
        if (dir === 'up') {
          nextVideo();
        } else if (dir === 'down') {
          close();
        } else if (dir === 'left') {
          // Save toggle
          var wasSaved = toggleSave();
          window.dispatchEvent(new CustomEvent('videoPlayerSave', {
            detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex], saved: wasSaved }
          }));
        } else if (dir === 'right') {
          // Dismiss hook (stub)
          showHint('Dismissed');
          window.dispatchEvent(new CustomEvent('videoPlayerDismiss', {
            detail: { foundupId: currentFoundUpId, video: currentQueue[currentIndex] }
          }));
        }
      },
      onTap: function () {
        toggleChrome();
      }
    });

    setPinchTarget(returnTile ? container : stage);
  }

  function setPinchTarget(target) {
    if (pinchTarget === target) return;
    pinchTarget?.removeEventListener('touchstart', handlePinchStart);
    pinchTarget?.removeEventListener('touchmove', handlePinchMove);
    initialPinchDistance = 0;
    pinchTarget = target;
    pinchTarget?.addEventListener('touchstart', handlePinchStart, { passive: true });
    pinchTarget?.addEventListener('touchmove', handlePinchMove, { passive: false });
  }

  function handlePinchStart(e) {
    initialPinchDistance = 0;
    if (e.target?.closest?.('.video-player-queue-panel, button, a, input')) return;
    if (e.touches.length === 2) {
      initialPinchDistance = getPinchDistance(e.touches);
    }
  }

  function handlePinchMove(e) {
    if (e.touches.length !== 2 || !initialPinchDistance) return;

    var currentDistance = getPinchDistance(e.touches);
    var scale = currentDistance / initialPinchDistance;

    if (inline && scale > 1 / PINCH_THRESHOLD) {
      e.preventDefault();
      expandInline();
    } else if (!inline && scale < PINCH_THRESHOLD) {
      e.preventDefault();
      close();
      initialPinchDistance = 0;
    }
  }

  function getPinchDistance(touches) {
    var dx = touches[0].clientX - touches[1].clientX;
    var dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
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
        expandInline();
        break;
      case 'enter':
        // Enter FoundUp: navigate to canonical /f/{foundup_id} route (WSP 104)
        if (currentFoundUpId && !scopedPlayer) {
          var destination = '/f/' + encodeURIComponent(currentFoundUpId);
          close();
          window.location.href = destination;
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
      if (index === currentIndex && requestYouTubePlay &&
          (theater || container.classList.contains('video-player-queue-docked')) &&
          playbackStatus?.state !== 'playing') {
        requestYouTubePlay();
        return;
      }
      goToVideo(index);
    }
  }

  function handleKeydown(e) {
    if (!isOpen || theater) return;
    if (e.defaultPrevented || e.isComposing || e.target?.closest?.('dialog[open]')) return;
    if (e.key !== 'Escape' && (inline || e.target?.closest?.('button, a, input, textarea, select'))) return;

    switch (e.key) {
      case 'Escape':
        if (returnTile && !scopedPlayer) {
          e.preventDefault();
          e.stopPropagation();
        }
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
    // Priority: embed_url > source_url
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

    // Try native share first
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
      // Fallback for older browsers
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

    // Remove duplicate if exists (same foundupId + videoId)
    history = history.filter(function (h) {
      return !(h.foundupId === foundupId && h.videoId === videoId);
    });

    // Add to front
    history.unshift(entry);

    // Trim to max
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
    /**
     * Open fullscreen player with a FoundUp's video queue.
     * @param {string} foundupId - The FoundUp ID (queue constraint)
     * @param {Array} queue - Array of video objects
     * @param {number} [startIndex=0] - Index to start at
     */
    open: open,

    /**
     * Close the fullscreen player.
     */
    close: close,
    expandInline: expandInline,
    setTheater: setTheater,
    isTheater: function() { return theater; },
    getQueueQuery: function() { return queueSearch?.value.trim().slice(0, 300) || ''; },
    getPlaybackSnapshot: getPlaybackSnapshot,

    /**
     * Navigate to a specific video in the current queue.
     * @param {number} index
     */
    goToVideo: goToVideo,

    /**
     * Go to next video in queue.
     */
    next: nextVideo,

    /**
     * Go to previous video in queue.
     */
    prev: prevVideo,

    /**
     * Check if player is open.
     * @returns {boolean}
     */
    isOpen: function () { return isOpen; },

    /**
     * Get current FoundUp ID (queue constraint).
     * @returns {string|null}
     */
    getFoundUpId: function () { return currentFoundUpId; },

    /**
     * Get current video index.
     * @returns {number}
     */
    getCurrentIndex: function () { return currentIndex; },

    /**
     * Get current queue length.
     * @returns {number}
     */
    getQueueLength: function () { return currentQueue.length; },

    /**
     * Check if current video is saved.
     * @returns {boolean}
     */
    isCurrentSaved: function () {
      if (!currentFoundUpId || currentIndex < 0) return false;
      return isVideoSaved(currentFoundUpId, currentQueue[currentIndex]);
    },

    /**
     * Get all saved videos.
     * @returns {Object} Map of saveKey → saved entry
     */
    getSavedVideos: getSavedVideos,

    /**
     * Get saved video count.
     * @returns {number}
     */
    getSavedCount: function () {
      return Object.keys(getSavedVideos()).length;
    },

    /**
     * Get watch history.
     * @returns {Array} Recent watch entries (newest first)
     */
    getHistory: getWatchHistory,

    /**
     * Clear watch history.
     */
    clearHistory: function () {
      setWatchHistory([]);
    }
  };
})();
