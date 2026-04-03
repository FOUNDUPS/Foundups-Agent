/**
 * Mall Planes — in-page FoundUp preview/handoff plane.
 *
 * Manages:
 *   - Opening a FoundUp preview when a tile is tapped
 *   - Swipe up to close, return to Mall
 *   - Swipe left/right to navigate between FoundUps
 *   - Desktop drag parity via gesture-engine.js
 *   - Keyboard: Escape to close, Arrow keys to navigate
 *
 * Handoff model:
 *   - Preview plane shows tile content with "Open FoundUp" CTA
 *   - CTA links to transitional entry: /member/foundup.html?id={id}
 *   - Future: in-scope /f/{id} routes when live
 *
 * Depends on:
 *   - gesture-engine.js (window.gestureZone, window.dragScroll)
 *   - HTML: #foundupViewPlane, #foundupViewBody, #foundupViewClose, #foundupViewScrim
 */
(function () {
  'use strict';

  var plane = document.getElementById('foundupViewPlane');
  var body = document.getElementById('foundupViewBody');
  var closeBtn = document.getElementById('foundupViewClose');
  var scrim = document.getElementById('foundupViewScrim');
  if (!plane || !body) return;

  var catalog = [];
  var activeIndex = -1;
  var isOpen = false;
  var gestureRef = null;

  var READINESS_LABELS = {
    ready: 'Ready',
    conditional: 'Conditional',
    discoverable_only: 'Discoverable Only'
  };

  // ---- open / close ----
  function openFoundUp(index) {
    if (index < 0 || index >= catalog.length) return;
    activeIndex = index;
    renderView(catalog[index]);
    plane.classList.add('open');
    if (scrim) scrim.classList.add('open');
    document.body.classList.add('surface-open');
    isOpen = true;
    attachGestures();
  }

  function closeView() {
    if (!isOpen) return;
    plane.classList.remove('open');
    if (scrim) scrim.classList.remove('open');
    document.body.classList.remove('surface-open');
    isOpen = false;
    if (gestureRef) { gestureRef.destroy(); gestureRef = null; }
  }

  function navigateFoundUp(delta) {
    var next = activeIndex + delta;
    if (next < 0 || next >= catalog.length) return;
    activeIndex = next;
    renderView(catalog[next]);
    // Sync Mall carousel position
    if (window.mallPlanesSync) window.mallPlanesSync(next);
  }

  // ---- render ----
  function renderView(item) {
    var displayName = item.name || item.title || item.entity || item.foundup_id;
    var displayToken = item.token_symbol || item.source_handle || '';
    var displayHero = item.hero_label || '';
    var displayTagline = item.tagline || (item.entity ? item.entity + (item.geo ? ' \u00b7 ' + item.geo : '') : '');
    var displayReadiness = item.launch_readiness || item.status || 'active';
    var routeHint = item.routing_prefix ? ' \u2192 ' + esc(item.routing_prefix) : '';
    var videoHint = item.video_count ? ' \u00b7 ' + item.video_count + ' videos' : '';
    body.innerHTML =
      '<div class="fv-hero theme-' + esc(item.theme || 'default') + '">' +
        '<div class="fv-token">' + esc(displayToken) + '</div>' +
        '<div class="fv-hero-label">' + esc(displayHero) + '</div>' +
        '<h2 class="fv-name">' + esc(displayName) + '</h2>' +
        '<span class="fv-badge fv-badge-' + esc(displayReadiness) + '">' +
          esc(READINESS_LABELS[displayReadiness] || displayReadiness) +
        '</span>' +
      '</div>' +
      '<p class="fv-tagline">' + esc(displayTagline) + esc(videoHint) + '</p>' +
      '<div class="fv-actions">' +
        '<a href="/member/foundup.html?id=' + encodeURIComponent(item.foundup_id) + '" class="fv-open-link">Open FoundUp' + routeHint + '</a>' +
      '</div>' +
      '<p class="fv-hint">Swipe up to close \u00b7 Swipe sideways for next</p>';
  }

  // ---- gestures ----
  function attachGestures() {
    if (gestureRef) gestureRef.destroy();
    if (!window.gestureZone) return;

    gestureRef = window.gestureZone(plane, {
      onSwipe: function (dir) {
        if (dir === 'up') closeView();
        else if (dir === 'left') navigateFoundUp(1);
        else if (dir === 'right') navigateFoundUp(-1);
      }
    });
  }

  // ---- keyboard ----
  document.addEventListener('keydown', function (e) {
    if (!isOpen) return;
    if (e.key === 'Escape') closeView();
    else if (e.key === 'ArrowLeft') navigateFoundUp(-1);
    else if (e.key === 'ArrowRight') navigateFoundUp(1);
  });

  // ---- close button / scrim ----
  if (closeBtn) closeBtn.addEventListener('click', closeView);
  if (scrim) scrim.addEventListener('click', closeView);

  // ---- drag-scroll for Mall track (desktop parity) ----
  var mallTrack = document.getElementById('mallTrack');
  if (mallTrack && window.dragScroll) {
    window.dragScroll(mallTrack);
  }

  // ---- escape helper ----
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  // ---- public API ----
  window.mallPlanes = {
    setCatalog: function (c) { catalog = c || []; },
    openFoundUp: openFoundUp,
    closeView: closeView,
    isOpen: function () { return isOpen; },
    getActiveIndex: function () { return activeIndex; }
  };
})();
