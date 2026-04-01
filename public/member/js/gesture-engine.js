/**
 * Gesture Engine — unified touch + mouse gesture detection.
 *
 * Creates gesture zones on elements that detect:
 *   - swipe-left, swipe-right, swipe-up, swipe-down
 *   - tap / click (single)
 *   - double-tap / double-click
 *
 * Desktop parity:
 *   - click = tap
 *   - double-click = double-tap
 *   - click-drag = swipe
 *
 * Both touch and mouse-drag produce the same callbacks.
 * No external dependencies.
 */
(function () {
  'use strict';

  var SWIPE_THRESHOLD = 50;
  var TAP_THRESHOLD = 15;
  var DOUBLE_TAP_DELAY = 300;
  var TAP_CONFIRM_DELAY = 300; // Wait to confirm single vs double tap

  /**
   * Attach gesture detection to an element.
   * @param {HTMLElement} el - Target element
   * @param {Object} handlers - { onSwipe(direction), onTap(), onDoubleTap() }
   * @returns {{ destroy: Function }}
   */
  function gestureZone(el, handlers) {
    var startX = 0;
    var startY = 0;
    var tracking = false;
    var lastTapTime = 0;
    var tapTimer = null;

    function handleEnd(endX, endY) {
      if (!tracking) return;
      tracking = false;

      var dx = endX - startX;
      var dy = endY - startY;
      var absDx = Math.abs(dx);
      var absDy = Math.abs(dy);

      // Tap (small movement) — check for single or double-tap
      if (absDx < TAP_THRESHOLD && absDy < TAP_THRESHOLD) {
        var now = Date.now();
        if (now - lastTapTime < DOUBLE_TAP_DELAY) {
          // Double-tap detected
          lastTapTime = 0;
          if (tapTimer) {
            clearTimeout(tapTimer);
            tapTimer = null;
          }
          if (handlers.onDoubleTap) handlers.onDoubleTap();
        } else {
          // Potential single tap — wait to confirm not a double-tap
          lastTapTime = now;
          if (handlers.onTap) {
            if (tapTimer) clearTimeout(tapTimer);
            tapTimer = setTimeout(function() {
              tapTimer = null;
              handlers.onTap();
            }, TAP_CONFIRM_DELAY);
          }
        }
        return;
      }

      // Swipe (must exceed threshold)
      if (absDx < SWIPE_THRESHOLD && absDy < SWIPE_THRESHOLD) return;

      var dir;
      if (absDx > absDy) {
        dir = dx > 0 ? 'right' : 'left';
      } else {
        dir = dy > 0 ? 'down' : 'up';
      }
      if (handlers.onSwipe) handlers.onSwipe(dir);
    }

    // ---- touch events ----
    function onTouchStart(e) {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      tracking = true;
    }

    function onTouchEnd(e) {
      var t = e.changedTouches[0];
      handleEnd(t.clientX, t.clientY);
    }

    // ---- mouse events (drag = swipe on desktop) ----
    function onMouseDown(e) {
      if (e.button !== 0) return;
      startX = e.clientX;
      startY = e.clientY;
      tracking = true;
      document.addEventListener('mouseup', onMouseUp, { once: true });
    }

    function onMouseUp(e) {
      handleEnd(e.clientX, e.clientY);
    }

    // Desktop double-click fallback
    function onDblClick() {
      if (handlers.onDoubleTap) handlers.onDoubleTap();
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true });
    el.addEventListener('touchend', onTouchEnd, { passive: true });
    el.addEventListener('mousedown', onMouseDown);
    el.addEventListener('dblclick', onDblClick);

    return {
      destroy: function () {
        if (tapTimer) {
          clearTimeout(tapTimer);
          tapTimer = null;
        }
        el.removeEventListener('touchstart', onTouchStart);
        el.removeEventListener('touchend', onTouchEnd);
        el.removeEventListener('mousedown', onMouseDown);
        el.removeEventListener('dblclick', onDblClick);
      }
    };
  }

  /**
   * Enable drag-to-scroll on a horizontal scrollable element.
   * Makes desktop mouse drag behave like touch swipe on a carousel.
   * @param {HTMLElement} track - The scrollable element
   * @returns {{ destroy: Function }}
   */
  function dragScroll(track) {
    var isDragging = false;
    var startX = 0;
    var scrollStart = 0;

    function onMouseDown(e) {
      if (e.button !== 0) return;
      isDragging = true;
      startX = e.clientX;
      scrollStart = track.scrollLeft;
      track.style.cursor = 'grabbing';
      track.style.scrollSnapType = 'none';
      e.preventDefault();
    }

    function onMouseMove(e) {
      if (!isDragging) return;
      track.scrollLeft = scrollStart - (e.clientX - startX);
    }

    function onMouseUp() {
      if (!isDragging) return;
      isDragging = false;
      track.style.cursor = '';
      track.style.scrollSnapType = 'x mandatory';
    }

    track.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    return {
      destroy: function () {
        track.removeEventListener('mousedown', onMouseDown);
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      }
    };
  }

  window.gestureZone = gestureZone;
  window.dragScroll = dragScroll;
})();
