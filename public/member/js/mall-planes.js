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
  var returnFocusListingId = null;  // listing identity within that FoundUp

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
    returnFocusListingId = item.source_type === 'property_listing' ? item.listing_id : null;
    activeIndex = index;
    renderView(item);
    plane.removeAttribute('inert');
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
    plane.setAttribute('inert', '');
    if (scrim) scrim.classList.remove('open');
    document.body.classList.remove('surface-open');
    isOpen = false;
    if (gestureRef) { gestureRef.destroy(); gestureRef = null; }
    // Return focus to originating tile by stable ID (survives projection changes)
    if (returnFocusId) {
      var tileField = document.getElementById('mallTileField');
      if (tileField) {
        var tile;
        if (returnFocusListingId) {
          // Compare dataset values, never interpolate a source-controlled ID into CSS.
          var propertyTiles = tileField.querySelectorAll('.mall-tile[data-listing-id]');
          for (var i = 0; i < propertyTiles.length; i++) {
            if (propertyTiles[i].dataset.foundupId === returnFocusId &&
                propertyTiles[i].dataset.listingId === returnFocusListingId) {
              tile = propertyTiles[i];
              break;
            }
          }
        } else {
          tile = tileField.querySelector('.mall-tile[data-foundup-id="' + returnFocusId + '"]');
        }
        if (tile && typeof tile.focus === 'function') tile.focus();
      }
      returnFocusId = null;
      returnFocusListingId = null;
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
    returnFocusListingId = navItem.source_type === 'property_listing' ? navItem.listing_id : null;
    // Sync Mall carousel position
    if (window.mallPlanesSync) window.mallPlanesSync(next);
    // renderView replaces the source link. Keep property focus on a live control.
    if (navItem.source_type === 'property_listing' && closeBtn) closeBtn.focus();
  }

  // ---- render ----
  function renderView(item) {
    if (item.source_type === 'property_listing') {
      renderPropertyView(item);
      return;
    }
    plane.removeAttribute('data-content-type');
    plane.removeAttribute('aria-labelledby');
    plane.removeAttribute('aria-modal');
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

  /** HTTPS source navigation only. Text and dataset fields confer no authority. */
  function propertySourceUrl(value) {
    if (typeof value !== 'string' || value.length > 2048 || /[\u0000-\u0020\\]/.test(value)) return '';
    try {
      var url = new URL(value);
      return url.protocol === 'https:' && url.hostname && !url.username && !url.password ? url.href : '';
    } catch (err) {
      return '';
    }
  }

  function propertyMeasurement(value) {
    return typeof value === 'number' && Number.isFinite(value) && value > 0
      ? value.toLocaleString('en-US') + ' m\u00b2' : 'Not stated';
  }

  function propertyFact(label, value) {
    return '<div><dt>' + esc(label) + '</dt><dd>' + esc(value == null || value === '' ? 'Not stated' : String(value)) + '</dd></div>';
  }

  function propertyAttr(value) {
    return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function renderPropertyView(item) {
    var sourceUrl = propertySourceUrl(item.source_url);
    var price = typeof item.price_jpy === 'number' && Number.isFinite(item.price_jpy) && item.price_jpy >= 0
      ? '\u00a5' + item.price_jpy.toLocaleString('en-US') : 'Price on request';
    var location = [item.municipality, item.prefecture].filter(Boolean).join(' \u00b7 ');
    var condition = item.repair_level === 'major' ? 'Major repairs required' : 'Repair needs not stated';
    var status = item.availability === 'source_listed' ? 'Listed at source when checked' : 'Status not confirmed';
    plane.setAttribute('data-content-type', 'property');
    plane.setAttribute('role', 'dialog');
    plane.setAttribute('aria-modal', 'true');
    plane.setAttribute('aria-labelledby', 'fvPropertyTitle');
    // A property has no token/readiness/video controls. The original source owns
    // its photographs and inquiry contacts; no media or broker claim is inferred.
    body.innerHTML =
      '<div class="fv-property-header">' +
        '<p class="fv-property-location">' + esc(location) + '</p>' +
        '<h2 id="fvPropertyTitle" class="fv-name">' + esc(item.name || item.title || 'House listing') + '</h2>' +
        '<p class="fv-property-price">' + esc(price) + '<span>Asking price (JPY)</span></p>' +
      '</div>' +
      '<p class="fv-property-summary">' + esc(item.summary || 'Read the original listing for property details.') + '</p>' +
      '<dl class="fv-property-facts">' +
        propertyFact('Location', location) +
        propertyFact('Address at source', item.address_ja) +
        propertyFact('Land area', propertyMeasurement(item.land_area_m2)) +
        propertyFact('Building area (' + (item.building_area_label_ja || 'source measurement') + ')', propertyMeasurement(item.building_area_m2)) +
        propertyFact('Construction date', item.construction_date) +
        propertyFact('Floors', item.floors) +
        propertyFact('Repair needs', condition) +
      '</dl>' +
      '<p class="fv-property-note">The source building-area figure is not a verified measurement of usable floor space.</p>' +
      '<div class="fv-property-source">' +
        '<h3>Original listing</h3>' +
        '<p>' + esc(item.source_name || 'Property source') + ' \u00b7 Record ' + esc(item.source_item_id || 'not stated') + '</p>' +
        '<p>Checked ' + esc(item.last_checked || 'date not recorded') + ' \u00b7 ' + esc(status) + '</p>' +
        '<p>Confirm current availability, condition and purchase requirements with the contact on the original listing.</p>' +
      '</div>' +
      '<div class="fv-actions">' +
        (sourceUrl ? '<a class="fv-primary-cta" href="' + propertyAttr(sourceUrl) + '" target="_blank" rel="noopener noreferrer">Photos &amp; inquiry at source \u2197</a>'
          : '<p class="fv-property-note">The original listing link is unavailable.</p>') +
      '</div>' +
      '<p class="fv-hint">Swipe sideways for next \u00b7 Use Close to return</p>';
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
        var propertyView = catalog[activeIndex] && catalog[activeIndex].source_type === 'property_listing';
        // Single-finger vertical motion scrolls long property facts. It must not
        // dismiss their plane; the close button, scrim and Escape remain available.
        if (propertyView && (dir === 'up' || dir === 'down')) return;
        if (dir === 'up') closeView();
        else if (dir === 'left') navigateFoundUp(1);
        else if (dir === 'right') navigateFoundUp(-1);
      }
    });
  }

  // ---- keyboard ----
  document.addEventListener('keydown', function (e) {
    if (!isOpen) return;
    if (e.key === 'Tab' && catalog[activeIndex] && catalog[activeIndex].source_type === 'property_listing') {
      var controls = plane.querySelectorAll('button, a[href]');
      if (!controls.length) return;
      var first = controls[0];
      var last = controls[controls.length - 1];
      if (!plane.contains(document.activeElement)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
      return;
    }
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

  function openListingById(foundupId, listingId) {
    if (typeof foundupId !== 'string' || !foundupId || typeof listingId !== 'string' || !listingId) return false;
    var match = -1;
    for (var i = 0; i < catalog.length; i++) {
      var item = catalog[i];
      if (item.source_type === 'property_listing' && item.foundup_id === foundupId && item.listing_id === listingId) {
        if (match !== -1) return false;  // Duplicate identities are ambiguous.
        match = i;
      }
    }
    if (match === -1) return false;
    openFoundUp(match);
    return true;
  }

  window.mallPlanes = {
    setCatalog: function (c) { catalog = c || []; },
    openFoundUp: openFoundUp,
    openFoundUpById: openFoundUpById,
    openListingById: openListingById,
    closeView: closeView,
    isOpen: function () { return isOpen; },
    getActiveIndex: function () { return activeIndex; }
  };
})();
