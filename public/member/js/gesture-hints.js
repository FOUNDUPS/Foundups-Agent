/**
 * Gesture Hints — one-time dismissible hint overlay for the Mall.
 *
 * Shows gesture guidance on first visit. Dismisses on tap/click.
 * Persisted in localStorage so hints only appear once.
 * Auto-dismisses after 6 seconds.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'pfmall_hints_dismissed';
  var container = document.getElementById('gestureHints');
  if (!container) return;

  // Check if already dismissed
  try {
    if (localStorage.getItem(STORAGE_KEY) === '1') {
      container.remove();
      return;
    }
  } catch (e) { /* localStorage unavailable — show hints anyway */ }

  // Show the hints
  container.style.display = 'flex';

  function dismiss() {
    container.classList.add('hint-dismiss');
    setTimeout(function () { container.remove(); }, 300);
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch (e) { /* ok */ }
  }

  container.addEventListener('click', dismiss);
  container.addEventListener('touchstart', dismiss, { passive: true });

  // Auto-dismiss after 6 seconds
  setTimeout(dismiss, 6000);
})();
