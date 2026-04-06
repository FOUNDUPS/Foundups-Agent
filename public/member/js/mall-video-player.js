/**
 * Mall Video Player — Fullscreen video layer with queue rail.
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

  // ─── State ───
  var container = null;
  var stage = null;
  var topBar = null;
  var queueRail = null;
  var queueTrack = null;
  var edgeTrigger = null;
  var gestureHint = null;
  var titleEl = null;
  var saveBtn = null;

  var isOpen = false;
  var currentQueue = [];       // Array of video objects from one FoundUp
  var currentFoundUpId = null; // Constrains queue
  var currentIndex = -1;
  var gestureRef = null;
  var railTimer = null;
  var chromeTimer = null;
  var initialPinchDistance = 0;

  // ─── localStorage Keys ───
  var SAVED_KEY = 'pfmall_saved_videos';
  var HISTORY_KEY = 'pfmall_watch_history';
  var HISTORY_MAX = 50; // Max history entries
  /** Local-only resume: omit sub-threshold & “finished” positions (HTML5 video only; embeds cannot read time). */
  var MIN_RESUME_SECONDS = 5;
  var COMPLETE_RATIO = 0.97;
  var pendingResumeSeconds = null;

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
      '    <span class="video-player-title"></span>',
      '  </div>',
      '  <div class="video-player-top-bar-right">',
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
      '<div class="video-player-edge-trigger"></div>',
      '<div class="video-player-queue-rail">',
      '  <div class="video-player-queue-track"></div>',
      '</div>',
      '<div class="video-player-gesture-hint"></div>'
    ].join('\n');

    document.body.appendChild(container);

    stage = container.querySelector('.video-player-stage');
    topBar = container.querySelector('.video-player-top-bar');
    queueRail = container.querySelector('.video-player-queue-rail');
    queueTrack = container.querySelector('.video-player-queue-track');
    edgeTrigger = container.querySelector('.video-player-edge-trigger');
    gestureHint = container.querySelector('.video-player-gesture-hint');
    titleEl = container.querySelector('.video-player-title');
    saveBtn = container.querySelector('[data-action="save"]');

    // Attach listeners
    topBar.addEventListener('click', handleTopBarClick);
    queueTrack.addEventListener('click', handleRailClick);
    edgeTrigger.addEventListener('touchstart', showRail, { passive: true });
    edgeTrigger.addEventListener('mouseenter', showRail);

    // Keyboard
    document.addEventListener('keydown', handleKeydown);
  }

  // ─── Open Fullscreen ───
  function open(foundupId, queue, startIndex, resumeOpts) {
    if (!queue || !queue.length) return;

    ensureDOM();

    var rs = null;
    if (resumeOpts != null && resumeOpts !== undefined) {
      if (typeof resumeOpts === 'number') {
        rs = resumeOpts;
      } else if (typeof resumeOpts === 'object' && typeof resumeOpts.resumeSeconds === 'number') {
        rs = resumeOpts.resumeSeconds;
      }
    }
    pendingResumeSeconds = normalizeResumeSeconds(rs, 0);

    currentFoundUpId = foundupId;
    currentQueue = queue;
    currentIndex = Math.max(0, Math.min(startIndex || 0, queue.length - 1));
    isOpen = true;

    container.classList.add('open');
    document.body.style.overflow = 'hidden';

    renderVideo(currentQueue[currentIndex]);
    renderRail();
    attachGestures();
    resetChromeTimer();

    // Update save button state
    updateSaveButtonState(isVideoSaved(currentFoundUpId, currentQueue[currentIndex]));

    // Record watch history
    recordWatch(currentFoundUpId, currentQueue[currentIndex], currentIndex);

    // Dispatch event for external listeners
    window.dispatchEvent(new CustomEvent('videoPlayerOpen', {
      detail: { foundupId: foundupId, videoIndex: currentIndex }
    }));
  }

  // ─── Close Fullscreen ───
  function close() {
    if (!isOpen) return;

    flushCurrentPlaybackPosition();
    pendingResumeSeconds = null;

    isOpen = false;
    container.classList.remove('open');
    document.body.style.overflow = '';

    // Stop video
    stage.innerHTML = '';

    // Cleanup
    if (gestureRef) { gestureRef.destroy(); gestureRef = null; }
    clearTimeout(railTimer);
    clearTimeout(chromeTimer);

    currentQueue = [];
    currentFoundUpId = null;
    currentIndex = -1;

    window.dispatchEvent(new CustomEvent('videoPlayerClose'));
  }

  // ─── Navigate Queue ───
  function goToVideo(index) {
    if (index < 0 || index >= currentQueue.length) return;
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
    if (currentIndex < currentQueue.length - 1) {
      goToVideo(currentIndex + 1);
      showHint('Next');
    } else {
      showHint('End of queue');
    }
  }

  function prevVideo() {
    if (currentIndex > 0) {
      goToVideo(currentIndex - 1);
      showHint('Previous');
    }
  }

  // ─── Render Video ───
  function renderVideo(video) {
    if (!video) return;

    titleEl.textContent = video.title || '';

    // Determine embed type
    var embedUrl = video.embed_url || video.embedUrl;
    var sourceUrl = video.source_url || video.sourceUrl;

    if (embedUrl) {
      pendingResumeSeconds = null;
      // YouTube/Vimeo embed — cannot read playback time from shell; resume N/A
      stage.innerHTML = '<iframe src="' + esc(embedUrl) + '?autoplay=1&rel=0" allowfullscreen allow="autoplay; encrypted-media"></iframe>';
    } else if (sourceUrl && sourceUrl.match(/\.(mp4|webm|ogg)$/i)) {
      // Direct video file — resume seek when pendingResumeSeconds is valid
      var resumeTarget = pendingResumeSeconds;
      pendingResumeSeconds = null;
      stage.innerHTML = '<video src="' + esc(sourceUrl) + '" autoplay controls playsinline></video>';
      var ve = stage.querySelector('video');
      if (ve && resumeTarget != null) {
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
    } else {
      pendingResumeSeconds = null;
      // Placeholder
      stage.innerHTML = '<div class="video-player-loading">Loading video...</div>';
    }
  }

  // ─── Render Rail ───
  function renderRail() {
    queueTrack.innerHTML = currentQueue.map(function (video, i) {
      var thumb = video.thumbnail_url || video.thumbnailUrl || video.poster_url || video.posterUrl || '';
      var title = video.title || 'Video ' + (i + 1);
      var activeClass = i === currentIndex ? ' active' : '';
      return [
        '<div class="video-player-queue-item' + activeClass + '" data-index="' + i + '">',
        '  <img class="video-player-queue-thumb" src="' + esc(thumb) + '" alt="" loading="lazy">',
        '  <div class="video-player-queue-label">' + esc(title) + '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function updateRailSelection() {
    var items = queueTrack.querySelectorAll('.video-player-queue-item');
    items.forEach(function (item, i) {
      item.classList.toggle('active', i === currentIndex);
    });

    // Scroll active into view
    var activeItem = queueTrack.querySelector('.video-player-queue-item.active');
    if (activeItem) {
      activeItem.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
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

    // Pinch detection (for pinch-in return)
    stage.addEventListener('touchstart', handlePinchStart, { passive: true });
    stage.addEventListener('touchmove', handlePinchMove, { passive: false });
  }

  function handlePinchStart(e) {
    if (e.touches.length === 2) {
      initialPinchDistance = getPinchDistance(e.touches);
    }
  }

  function handlePinchMove(e) {
    if (e.touches.length !== 2 || !initialPinchDistance) return;

    var currentDistance = getPinchDistance(e.touches);
    var scale = currentDistance / initialPinchDistance;

    if (scale < PINCH_THRESHOLD) {
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
      goToVideo(index);
    }
  }

  function handleKeydown(e) {
    if (!isOpen) return;

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
    // Priority: embed_url > source_url
    return video.embed_url || video.embedUrl || video.source_url || video.sourceUrl || '';
  }

  function shareVideo() {
    if (!currentFoundUpId || currentIndex < 0) return;

    var video = currentQueue[currentIndex];
    var url = getShareUrl(video);

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
