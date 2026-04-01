/**
 * Gesture Engine — unified touch + mouse gesture detection.
 *
 * Creates gesture zones on elements that detect:
 *   - swipe-left, swipe-right, swipe-up, swipe-down
 *   - tap / click (single)
 *   - double-tap / double-click
 *   - pinch-in / pinch-out (touch: two-finger, desktop: ctrl+wheel)
 *
 * Desktop parity:
 *   - click = tap
 *   - double-click = double-tap
 *   - click-drag = swipe
 *   - ctrl+wheel = pinch
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
  var PINCH_THRESHOLD = 30; // Minimum distance change for pinch

  /**
   * Attach gesture detection to an element.
   * @param {HTMLElement} el - Target element
   * @param {Object} handlers - { onSwipe(direction), onTap(), onDoubleTap(), onPinchIn(), onPinchOut() }
   * @returns {{ destroy: Function }}
   */
  function gestureZone(el, handlers) {
    var startX = 0;
    var startY = 0;
    var tracking = false;
    var lastTapTime = 0;
    var tapTimer = null;

    // Pinch tracking
    var pinchStartDistance = 0;
    var isPinching = false;

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
    function getTouchDistance(touches) {
      if (touches.length < 2) return 0;
      var dx = touches[1].clientX - touches[0].clientX;
      var dy = touches[1].clientY - touches[0].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    }

    function onTouchStart(e) {
      if (e.touches.length === 2) {
        // Two-finger touch: start pinch tracking
        isPinching = true;
        tracking = false;
        pinchStartDistance = getTouchDistance(e.touches);
        return;
      }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      tracking = true;
      isPinching = false;
    }

    function onTouchMove(e) {
      if (isPinching && e.touches.length === 2) {
        // Prevent scroll during pinch
        e.preventDefault();
      }
    }

    function onTouchEnd(e) {
      if (isPinching) {
        // Check pinch result
        var endDistance = pinchStartDistance;
        if (e.touches.length === 1) {
          // One finger lifted, use remaining touch + changed touch
          var dx = e.changedTouches[0].clientX - e.touches[0].clientX;
          var dy = e.changedTouches[0].clientY - e.touches[0].clientY;
          endDistance = Math.sqrt(dx * dx + dy * dy);
        } else if (e.touches.length === 0 && e.changedTouches.length === 2) {
          endDistance = getTouchDistance(e.changedTouches);
        }

        var delta = endDistance - pinchStartDistance;
        if (Math.abs(delta) > PINCH_THRESHOLD) {
          if (delta > 0 && handlers.onPinchOut) {
            handlers.onPinchOut();
          } else if (delta < 0 && handlers.onPinchIn) {
            handlers.onPinchIn();
          }
        }

        isPinching = false;
        pinchStartDistance = 0;
        return;
      }

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

    // Desktop pinch: ctrl+wheel
    function onWheel(e) {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      if (e.deltaY < 0 && handlers.onPinchOut) {
        handlers.onPinchOut();
      } else if (e.deltaY > 0 && handlers.onPinchIn) {
        handlers.onPinchIn();
      }
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true });
    el.addEventListener('touchmove', onTouchMove, { passive: false });
    el.addEventListener('touchend', onTouchEnd, { passive: true });
    el.addEventListener('mousedown', onMouseDown);
    el.addEventListener('dblclick', onDblClick);
    el.addEventListener('wheel', onWheel, { passive: false });

    return {
      destroy: function () {
        if (tapTimer) {
          clearTimeout(tapTimer);
          tapTimer = null;
        }
        el.removeEventListener('touchstart', onTouchStart);
        el.removeEventListener('touchmove', onTouchMove);
        el.removeEventListener('touchend', onTouchEnd);
        el.removeEventListener('mousedown', onMouseDown);
        el.removeEventListener('dblclick', onDblClick);
        el.removeEventListener('wheel', onWheel);
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
