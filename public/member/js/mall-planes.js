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
  var returnFocusId = null;  // foundup_id for focus return (stable across projections)

  var READINESS_LABELS = {
    ready: 'Ready',
    conditional: 'Conditional',
    discoverable_only: 'Discoverable Only'
  };

  var SOURCE_TYPE_CTA = {
    github_repo:      { label: 'View Repo',    icon: '\u2197', urlField: 'external_url' },
    external_app:     { label: 'Open App',      icon: '\u2197', urlField: 'external_url' },
    internal_service: { label: 'Open Service',  icon: '\u2197', urlField: 'external_url' }
  };
  var NON_VIDEO_SOURCE_TYPES = { github_repo: true, external_app: true, internal_service: true };

  // ---- open / close ----
  function openFoundUp(index) {
    if (index < 0 || index >= catalog.length) return;
    // Save focus return ID (stable across projection/filter changes)
    var item = catalog[index];
    returnFocusId = item.foundup_id || item.id || null;
    activeIndex = index;
    renderView(item);
    plane.classList.add('open');
    if (scrim) scrim.classList.add('open');
    document.body.classList.add('surface-open');
    isOpen = true;
    attachGestures();
    // Move focus to close button for keyboard users
    if (closeBtn) closeBtn.focus();
  }

  function closeView() {
    if (!isOpen) return;
    plane.classList.remove('open');
    if (scrim) scrim.classList.remove('open');
    document.body.classList.remove('surface-open');
    isOpen = false;
    if (gestureRef) { gestureRef.destroy(); gestureRef = null; }
    // Return focus to originating tile by stable ID (survives projection changes)
    if (returnFocusId) {
      var tileField = document.getElementById('mallTileField');
      if (tileField) {
        var tile = tileField.querySelector('.mall-tile[data-foundup-id="' + returnFocusId + '"]');
        if (tile && typeof tile.focus === 'function') tile.focus();
      }
      returnFocusId = null;
    }
  }

  function navigateFoundUp(delta) {
    var next = activeIndex + delta;
    if (next < 0 || next >= catalog.length) return;
    activeIndex = next;
    renderView(catalog[next]);
    // Update return focus ID to navigated item (stable identity)
    var navItem = catalog[next];
    returnFocusId = navItem.foundup_id || navItem.id || null;
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
    var isNonVideo = NON_VIDEO_SOURCE_TYPES[item.source_type] || false;
    var videoHint = (!isNonVideo && item.video_count) ? ' \u00b7 ' + item.video_count + ' videos' : '';

    // Source-type context for non-video entries
    var sourceContext = '';
    if (isNonVideo) {
      var sourceLabel = (item.source_type || '').replace(/_/g, ' ');
      var destination = item.external_url ? extractDomain(item.external_url) : '';
      var destHint = destination ? ' \u2192 ' + esc(destination) : '';
      sourceContext = '<p class="fv-source-context">' + esc(sourceLabel) + destHint + '</p>';
    }

    // Primary CTA: source-type action for non-video, or entry page for video
    var primaryCtaHtml = '';
    var secondaryLinkHtml = '';
    var ctaDef = SOURCE_TYPE_CTA[item.source_type];

    if (isNonVideo && ctaDef && item[ctaDef.urlField]) {
      // Non-video: primary CTA is the source action (View Repo, Open App, Open Service)
      primaryCtaHtml =
        '<a href="' + esc(item[ctaDef.urlField]) + '" target="_blank" rel="noopener noreferrer" class="fv-primary-cta">' +
          esc(ctaDef.label) + ' ' + ctaDef.icon +
        '</a>';
      // Secondary: demoted entry-page link
      secondaryLinkHtml =
        '<a href="/member/foundup.html?id=' + encodeURIComponent(item.foundup_id) + '" class="fv-secondary-link">More about ' + esc(displayName) + '</a>';
    } else {
      // Video-backed: primary CTA is entry page
      primaryCtaHtml =
        '<a href="/member/foundup.html?id=' + encodeURIComponent(item.foundup_id) + '" class="fv-primary-cta">Open FoundUp</a>';
    }

    body.innerHTML =
      '<div class="fv-hero theme-' + esc(item.theme || item.foundup_id || 'default') + '">' +
        '<div class="fv-token">' + esc(displayToken) + '</div>' +
        '<div class="fv-hero-label">' + esc(displayHero) + '</div>' +
        '<h2 class="fv-name">' + esc(displayName) + '</h2>' +
        '<span class="fv-badge fv-badge-' + esc(displayReadiness) + '">' +
          esc(READINESS_LABELS[displayReadiness] || displayReadiness) +
        '</span>' +
      '</div>' +
      sourceContext +
      '<p class="fv-tagline">' + esc(displayTagline) + esc(videoHint) + '</p>' +
      '<div class="fv-actions">' +
        primaryCtaHtml +
      '</div>' +
      (secondaryLinkHtml ? '<div class="fv-secondary-actions">' + secondaryLinkHtml + '</div>' : '') +
      '<p class="fv-hint">Swipe up to close \u00b7 Swipe sideways for next</p>';
  }

  // Extract domain from URL for destination hint
  function extractDomain(url) {
    try {
      var u = new URL(url);
      return u.hostname.replace(/^www\./, '');
    } catch (e) {
      return '';
    }
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
  function openFoundUpById(foundupId) {
    if (!foundupId) return;
    for (var i = 0; i < catalog.length; i++) {
      if ((catalog[i].foundup_id || catalog[i].id) === foundupId) {
        openFoundUp(i);
        return;
      }
    }
  }

  window.mallPlanes = {
    setCatalog: function (c) { catalog = c || []; },
    openFoundUp: openFoundUp,
    openFoundUpById: openFoundUpById,
    closeView: closeView,
    isOpen: function () { return isOpen; },
    getActiveIndex: function () { return activeIndex; }
  };
})();
