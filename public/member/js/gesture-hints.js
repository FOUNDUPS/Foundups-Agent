/**
 * Gesture Hints — One-time dismissible discovery overlay
 *
 * Shows gesture hints on first visit, dismisses on tap or after 6 seconds.
 * Uses localStorage to remember dismissal.
 */
(function() {
  'use strict';

  var STORAGE_KEY = 'pfmall_hints_dismissed';
  var AUTO_DISMISS_MS = 6000;

  function init() {
    var hints = document.getElementById('gestureHints');
    if (!hints) return;

    // Check if already dismissed
    try {
      if (localStorage.getItem(STORAGE_KEY) === 'true') {
        return; // Don't show again
      }
    } catch (e) {
      // localStorage unavailable, fail quietly
      return;
    }

    // Show hints overlay
    hints.style.display = 'flex';

    var dismissed = false;

    function dismiss() {
      if (dismissed) return;
      dismissed = true;

      // Fade out via CSS class
      hints.classList.add('hint-dismiss');

      // Store dismissal
      try {
        localStorage.setItem(STORAGE_KEY, 'true');
      } catch (e) {
        // Fail quietly
      }

      // Hide after transition completes
      setTimeout(function() {
        hints.style.display = 'none';
      }, 350);
    }

    // Tap/click anywhere to dismiss
    hints.addEventListener('click', dismiss);

    // Auto-dismiss after 6 seconds
    setTimeout(dismiss, 6000);
  }

  // Run after DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
