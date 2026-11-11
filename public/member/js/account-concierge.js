/**
 * Red Dog Unified Plane — the user's personal agent surface.
 *
 * Red Dog IS the user panel. The user panel IS the concierge. One surface.
 *
 * Manages the unified plane that slides down from the top of the Mall.
 * Triggered by: Red Dog FAB button, avatar tap in header, or swipe-down gesture.
 * Closed by: swipe-up on the plane, tapping the scrim, or pressing Escape.
 *
 * Depends on:
 *   - #accountPlane, #accountPlaneScrim in the DOM
 *   - Clerk user object for avatar/profile
 *   - Mall catalog data for FoundUps grid
 *   - Firestore invite data for invite drawer
 */
(function () {
  'use strict';

  // ---- DOM refs ----
  var plane = document.getElementById('accountPlane');
  var scrim = document.getElementById('accountPlaneScrim');
  if (!plane || !scrim) return;

  // The old public alias remains supported. Product selection in /member/
  // composes this modal owner with the existing account controller below.
  if (plane.getAttribute('data-reddog-mode') === 'public-discovery') {
    initializePublicDiscovery();
    return;
  }
  var productDiscovery = plane.getAttribute('data-reddog-mode') === 'product-discovery';
  var discoveryAdmitted = !productDiscovery;
  var productDiscoveryController = null;
  var productProfileBound = false;

  var avatarTrigger = document.getElementById('mallAvatarTrigger');
  var redDogTrigger = document.getElementById('redDogBtn');
  var invitesToggle = plane.querySelector('[data-account-invites-toggle]');
  var invitesDrawer = plane.querySelector('[data-account-invites-drawer]');
  var signOutBtn = plane.querySelector('[data-account-signout]');

  var isOpen = false;

  // ---- verification alerts (skeleton) ----
  // In-memory storage only. No backend connection.
  // WSP 97: RedDog may notify/summarize/open panels. RedDog may NOT judge/deny/finalize.
  var verificationAlerts = {};
  var verificationAlertCount = 0;

  // ---- swipe tracking ----
  var touchStartY = 0;
  var touchCurrentY = 0;
  var isDragging = false;
  var SWIPE_THRESHOLD = 60;

  // ---- open / close ----
  function openPlane(event) {
    if (productDiscoveryController) {
      closeModes();
      dismissSummary();
      stopListening();
      productDiscoveryController.open(event);
      setAnchorState('active');
      return;
    }
    if (isOpen) return;
    isOpen = true;
    plane.classList.add('open');
    scrim.classList.add('open');
    document.body.classList.add('surface-open');
    setAnchorState('active');
  }

  function closePlane() {
    if (productDiscoveryController) return productDiscoveryController.close();
    if (!isOpen) return;
    isOpen = false;
    plane.classList.remove('open');
    scrim.classList.remove('open');
    document.body.classList.remove('surface-open');
    if (!listeningVisible) setAnchorState('idle');
  }

  function togglePlane(event) {
    if (isOpen) closePlane();
    else openPlane(event);
  }

  // ---- Red Dog anchor interaction grammar ----
  var anchor = document.getElementById('redDogAnchor');
  var summaryEl = document.getElementById('redDogSummary');
  var summaryContent = summaryEl && summaryEl.querySelector('[data-reddog-summary-content]');
  var listeningEl = document.getElementById('redDogListening');
  var stateRing = redDogTrigger && redDogTrigger.querySelector('[data-reddog-anchor-state]');

  var lastTapTime = 0;
  var tapTimer = null;
  var DOUBLE_TAP_WINDOW = 300;
  var holdTimer = null;
  var HOLD_THRESHOLD = 500;
  var isHolding = false;
  var summaryVisible = false;
  var listeningVisible = false;

  // Anchor state: idle | active | listening
  function setAnchorState(state) {
    if (stateRing) stateRing.setAttribute('data-reddog-anchor-state', state);
  }

  function showSummary() {
    if (productDiscovery && !discoveryAdmitted) return false;
    if (productDiscovery && isOpen) closePlane();
    if (!summaryEl || !summaryContent) return;
    // Build shell-owned summary from loaded data
    var lines = [];
    var grid = plane.querySelector('[data-account-foundups-grid]');
    var tileCount = grid ? grid.querySelectorAll('.account-foundup-tile').length : 0;
    var activeCount = grid ? grid.querySelectorAll('.status-active, .status-ready').length : 0;
    var countEl = plane.querySelector('[data-invite-count]');
    var inviteText = countEl ? countEl.textContent : '';

    if (tileCount > 0) {
      lines.push(tileCount + ' FoundUp' + (tileCount !== 1 ? 's' : '') + (activeCount > 0 ? ' \u00b7 ' + activeCount + ' active' : ''));
    } else {
      lines.push('No FoundUps loaded yet');
    }
    if (inviteText) {
      lines.push('Invites: ' + inviteText);
    }
    lines.push('Tap to open \u00b7 Hold to talk');

    summaryContent.innerHTML = lines.map(function (l) { return '<p>' + esc(l) + '</p>'; }).join('');
    summaryEl.hidden = false;
    summaryVisible = true;
    setAnchorState('active');

    // Auto-dismiss after 3s
    setTimeout(function () { dismissSummary(); }, 3000);
  }

  function dismissSummary() {
    if (!summaryEl) return;
    summaryEl.hidden = true;
    summaryVisible = false;
    if (!listeningVisible && !isOpen) setAnchorState('idle');
  }

  function startListening() {
    if (productDiscovery && !discoveryAdmitted) return false;
    if (productDiscovery && isOpen) closePlane();
    if (!listeningEl) return;
    isHolding = true;
    listeningVisible = true;
    listeningEl.hidden = false;
    dismissSummary();
    setAnchorState('listening');
    if (redDogTrigger) redDogTrigger.classList.add('red-dog-btn-listening');
  }

  function stopListening() {
    if (!listeningEl) return;
    isHolding = false;
    listeningVisible = false;
    listeningEl.hidden = true;
    if (redDogTrigger) redDogTrigger.classList.remove('red-dog-btn-listening');
    if (!isOpen) setAnchorState('idle');
  }

  // ---- Red Dog trigger (primary entry point) ----
  if (redDogTrigger) {
    // Pointer-based interactions for tap / double-tap / hold
    redDogTrigger.addEventListener('pointerdown', function (e) {
      if (productDiscovery && !discoveryAdmitted) return;
      e.stopPropagation();
      // Start hold timer
      holdTimer = setTimeout(function () {
        startListening();
      }, HOLD_THRESHOLD);
    });

    redDogTrigger.addEventListener('pointerup', function (e) {
      if (productDiscovery && !discoveryAdmitted) return;
      e.stopPropagation();
      clearTimeout(holdTimer);

      // If we were holding, stop listening — don't fire tap
      if (isHolding) {
        stopListening();
        return;
      }

      var now = Date.now();
      if (now - lastTapTime < DOUBLE_TAP_WINDOW) {
        // Double-tap: show quick summary
        clearTimeout(tapTimer);
        lastTapTime = 0;
        showSummary();
      } else {
        // Single tap: toggle plane (delayed to wait for possible double-tap)
        lastTapTime = now;
        tapTimer = setTimeout(function () {
          lastTapTime = 0;
          if (summaryVisible) { dismissSummary(); return; }
          togglePlane({ currentTarget: redDogTrigger });
        }, DOUBLE_TAP_WINDOW);
      }
    });

    redDogTrigger.addEventListener('pointerleave', function () {
      clearTimeout(holdTimer);
      if (isHolding) stopListening();
    });

    redDogTrigger.addEventListener('pointercancel', function () {
      clearTimeout(holdTimer);
      if (isHolding) stopListening();
    });

    // Prevent context menu on long press (mobile)
    redDogTrigger.addEventListener('contextmenu', function (e) {
      e.preventDefault();
    });

    if (productDiscovery) {
      // Guests open the form immediately; admitted pointer gestures retain the
      // shared tap/double-tap/hold grammar. Keyboard click has no pointerup.
      redDogTrigger.addEventListener('click', function (e) {
        if (!discoveryAdmitted || e.detail === 0) openPlane(e);
      });
    }
  }

  // ---- mode sheet (JS-injected into anchor) ----
  var modeSheetEl = null;
  var modesVisible = false;
  var currentMode = 'idle';

  var MODE_ACTIONS = [
    { id: 'summary',   label: 'Summary',     icon: '\u2139' },
    { id: 'listen',    label: 'Listen',       icon: '\uD83C\uDFA4' },
    { id: 'tools',     label: 'AI Tools',     icon: '\uD83D\uDD27' },
    { id: 'channels',  label: 'Channels',     icon: '\uD83D\uDCE1' },
    { id: 'foundups',  label: 'My FoundUps',  icon: '\uD83D\uDCE6' },
    { id: 'invites',   label: 'Invites',      icon: '\uD83D\uDCE8' },
    { id: 'saved',     label: 'Saved',         icon: '\uD83D\uDD16' },
    { id: 'history',   label: 'History',       icon: '\uD83D\uDCCB' },
    { id: 'options',   label: 'Options',      icon: '\u2699' }
  ];

  function injectModeSheet() {
    if (modeSheetEl || !anchor) return;
    modeSheetEl = document.createElement('div');
    modeSheetEl.className = 'reddog-mode-sheet';
    modeSheetEl.setAttribute('data-reddog-mode-sheet', '');
    modeSheetEl.hidden = true;

    var html = '<div class="reddog-mode-sheet-actions" data-reddog-mode-actions>';
    for (var i = 0; i < MODE_ACTIONS.length; i++) {
      var a = MODE_ACTIONS[i];
      html += '<button class="reddog-mode-action" data-reddog-mode="' + a.id + '" type="button">'
            + '<span class="reddog-mode-action-icon">' + a.icon + '</span>'
            + '<span class="reddog-mode-action-label">' + a.label + '</span>'
            + '</button>';
    }
    html += '</div>';
    modeSheetEl.innerHTML = html;

    // Insert before the button in the anchor
    anchor.insertBefore(modeSheetEl, redDogTrigger);

    // Wire action clicks
    modeSheetEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-reddog-mode]');
      if (!btn) return;
      var mode = btn.getAttribute('data-reddog-mode');
      executeMode(mode);
    });
  }

  function executeMode(mode) {
    if (productDiscovery && !discoveryAdmitted) return false;
    currentMode = mode;
    closeModes();

    switch (mode) {
      case 'summary':
        showSummary();
        break;
      case 'listen':
        startListening();
        break;
      case 'tools':
        openPlane();
        injectAITools();
        var toolsSection = plane.querySelector('[data-reddog-tools]');
        if (toolsSection) toolsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      case 'channels':
        openPlane();
        injectChannels();
        var channelsSection = plane.querySelector('[data-reddog-channels]');
        if (channelsSection) channelsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      case 'foundups':
        openPlane();
        var foundups = plane.querySelector('[data-reddog-foundups]');
        if (foundups) foundups.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      case 'invites':
        openPlane();
        var invites = plane.querySelector('[data-reddog-invites]');
        if (invites) invites.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (invitesToggle && invitesDrawer && !invitesDrawer.classList.contains('open')) {
          invitesDrawer.classList.add('open');
          invitesToggle.classList.add('expanded');
        }
        break;
      case 'saved':
        openPlane();
        injectSavedVideos();
        var savedSection = plane.querySelector('[data-reddog-saved]');
        if (savedSection) savedSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      case 'history':
        openPlane();
        injectWatchHistory();
        var historySection = plane.querySelector('[data-reddog-history]');
        if (historySection) historySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      case 'options':
        openPlane();
        var opts = plane.querySelector('[data-reddog-options]');
        if (opts) opts.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      default:
        break;
    }
  }

  function openModes() {
    if (productDiscovery && !discoveryAdmitted) return false;
    // The mode sheet lives in the shell, outside the search modal's focus trap.
    if (productDiscovery && isOpen) closePlane();
    injectModeSheet();
    if (!modeSheetEl || modesVisible) return;
    modesVisible = true;
    modeSheetEl.hidden = false;
    dismissSummary();
    stopListening();
    setAnchorState('active');
  }

  function closeModes() {
    if (!modeSheetEl || !modesVisible) return;
    modesVisible = false;
    modeSheetEl.hidden = true;
    if (!isOpen && !listeningVisible) setAnchorState('idle');
  }

  function toggleModes() {
    if (modesVisible) closeModes();
    else openModes();
  }

  // ---- local swipe-up on anchor to open mode sheet ----
  var anchorTouchStartY = 0;
  var anchorTouchCurrentY = 0;
  var anchorSwiping = false;
  var ANCHOR_SWIPE_THRESHOLD = 40;

  if (anchor && !productDiscovery) {
    anchor.addEventListener('touchstart', function (e) {
      // Only capture swipes that start on the anchor (not the button's pointer events)
      anchorTouchStartY = e.touches[0].clientY;
      anchorTouchCurrentY = anchorTouchStartY;
      anchorSwiping = true;
    }, { passive: true });

    anchor.addEventListener('touchmove', function (e) {
      if (!anchorSwiping) return;
      anchorTouchCurrentY = e.touches[0].clientY;
    }, { passive: true });

    anchor.addEventListener('touchend', function () {
      if (!anchorSwiping) return;
      anchorSwiping = false;
      var delta = anchorTouchStartY - anchorTouchCurrentY;
      if (delta > ANCHOR_SWIPE_THRESHOLD) {
        // Swipe up on anchor = open mode sheet
        if (modesVisible) closeModes();
        else openModes();
      } else if (delta < -ANCHOR_SWIPE_THRESHOLD) {
        // Swipe down on anchor = close mode sheet
        closeModes();
      }
      anchorTouchStartY = 0;
      anchorTouchCurrentY = 0;
    }, { passive: true });
  }

  // Close mode sheet on escape
  var origEscapeHandler = null;

  // Extend existing escape handler to also close mode sheet
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modesVisible) {
      closeModes();
    }
  });

  // Close mode sheet when plane opens (modes are a pre-plane action)
  var origOpenPlane = openPlane;

  // ---- avatar trigger (secondary entry point) ----
  if (avatarTrigger) {
    avatarTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      togglePlane(e);
    });
  }

  // ---- scrim closes plane ----
  scrim.addEventListener('click', closePlane);

  // ---- escape key ----
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen) closePlane();
  });

  // ---- swipe-down to open (on Mall body) ----
  var mallShell = document.querySelector('.mall-shell');
  if (mallShell && !productDiscovery) {
    mallShell.addEventListener('touchstart', function (e) {
      if (isOpen) return;
      touchStartY = e.touches[0].clientY;
      // Only trigger swipe-down if near the top of the page
      if (touchStartY > 80) return;
      isDragging = true;
    }, { passive: true });

    mallShell.addEventListener('touchmove', function (e) {
      if (!isDragging || isOpen) return;
      touchCurrentY = e.touches[0].clientY;
    }, { passive: true });

    mallShell.addEventListener('touchend', function () {
      if (!isDragging) return;
      isDragging = false;
      if (touchCurrentY - touchStartY > SWIPE_THRESHOLD) {
        openPlane();
      }
      touchStartY = 0;
      touchCurrentY = 0;
    }, { passive: true });
  }

  // ---- swipe-up to close (on plane) ----
  plane.addEventListener('touchstart', function (e) {
    if (productDiscovery) return;
    touchStartY = e.touches[0].clientY;
    isDragging = true;
  }, { passive: true });

  plane.addEventListener('touchmove', function (e) {
    if (productDiscovery) return;
    if (!isDragging) return;
    touchCurrentY = e.touches[0].clientY;
  }, { passive: true });

  plane.addEventListener('touchend', function () {
    if (productDiscovery) return;
    if (!isDragging) return;
    isDragging = false;
    if (touchStartY - touchCurrentY > SWIPE_THRESHOLD) {
      closePlane();
    }
    touchStartY = 0;
    touchCurrentY = 0;
  }, { passive: true });

  // ---- invites toggle ----
  if (invitesToggle && invitesDrawer) {
    invitesToggle.addEventListener('click', function () {
      if (productDiscovery && !discoveryAdmitted) return;
      var expanded = invitesDrawer.classList.toggle('open');
      invitesToggle.classList.toggle('expanded', expanded);
    });
  }

  // ---- sign out ----
  if (signOutBtn) {
    signOutBtn.addEventListener('click', async function () {
      if (productDiscovery && !discoveryAdmitted) return;
      try {
        if (window.Clerk) await window.Clerk.signOut();
      } finally {
        window.location.href = '/';
      }
    });
  }

  // ---- AI tools: projection, density, motion mode ----
  var aiToolsEl = null;

  // Local state (truthful — these represent the user's current choice)
  var currentCategory = 'all';
  var currentDensity = '3x5';
  var currentMotionMode = 'snap';

  var CATEGORIES = [
    { id: 'all',       label: 'All' },
    { id: 'startups',  label: 'Startups' },
    { id: 'travel',    label: 'Travel' },
    { id: 'music',     label: 'Music' },
    { id: 'food',      label: 'Food' },
    { id: 'tech',      label: 'Tech' }
  ];

  var DENSITY_PRESETS = [
    { id: '3x4', label: '3×4' },
    { id: '3x5', label: '3×5' },
    { id: '4x6', label: '4×6' },
    { id: '5x8', label: '5×8' },
    { id: '6x3', label: '6×3' },
    { id: '8x2', label: '8w' },
    { id: '10x6', label: '10' },
    { id: '12x3', label: '12' },
    { id: '15x4', label: '15' }
  ];

  function emitRedDogCommand(command, detail) {
    document.dispatchEvent(new CustomEvent('reddog:command', {
      detail: Object.assign({ command: command }, detail || {})
    }));
  }

  function setCategory(categoryId) {
    if (productDiscovery) return false;
    currentCategory = categoryId;
    // Call B's API if available
    if (categoryId === 'all') {
      if (window.mallTileField && typeof window.mallTileField.resetProjection === 'function') {
        window.mallTileField.resetProjection();
      }
    } else {
      if (window.mallTileField && typeof window.mallTileField.setProjection === 'function') {
        window.mallTileField.setProjection(categoryId);
      }
    }
    emitRedDogCommand('set_projection', { category: categoryId });
    refreshToolsUI();
    renderBriefing();
  }

  function setDensity(presetId) {
    if (productDiscovery && !discoveryAdmitted) return false;
    // Use requestDensity for device policy enforcement
    if (window.mallTileField && typeof window.mallTileField.requestDensity === 'function') {
      var result = window.mallTileField.requestDensity(presetId, { source: 'reddog' });
      if (!result.applied) {
        console.warn('[RedDog] Density rejected:', result.reason);
        emitRedDogCommand('density_rejected', { preset: presetId, reason: result.reason });
        return;
      }
      currentDensity = presetId;
    } else if (window.mallTileField && typeof window.mallTileField.setDensity === 'function') {
      // Fallback for older API
      currentDensity = presetId;
      window.mallTileField.setDensity(presetId);
    }
    emitRedDogCommand('set_density', { preset: presetId });
    refreshToolsUI();
  }

  function setMotionMode(mode) {
    if (productDiscovery && !discoveryAdmitted) return false;
    currentMotionMode = mode;
    if (window.mallTileField && typeof window.mallTileField.setMotionMode === 'function') {
      window.mallTileField.setMotionMode(mode);
    }
    emitRedDogCommand('set_motion_mode', { mode: mode });
    refreshToolsUI();
  }

  function refreshToolsUI() {
    if (!aiToolsEl) return;

    // Update category active states
    var catBtns = aiToolsEl.querySelectorAll('[data-reddog-category]');
    for (var i = 0; i < catBtns.length; i++) {
      catBtns[i].classList.toggle('active', catBtns[i].getAttribute('data-reddog-category') === currentCategory);
    }

    // Update density active states
    var denBtns = aiToolsEl.querySelectorAll('[data-reddog-density]');
    for (var j = 0; j < denBtns.length; j++) {
      denBtns[j].classList.toggle('active', denBtns[j].getAttribute('data-reddog-density') === currentDensity);
    }

    // Update motion mode toggle
    var motionBtns = aiToolsEl.querySelectorAll('[data-reddog-motion]');
    for (var k = 0; k < motionBtns.length; k++) {
      motionBtns[k].classList.toggle('active', motionBtns[k].getAttribute('data-reddog-motion') === currentMotionMode);
    }
  }

  function injectAITools() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (aiToolsEl) return;
    var conciergeHost = plane.querySelector('[data-reddog-concierge]');
    if (!conciergeHost) return;

    aiToolsEl = document.createElement('div');
    aiToolsEl.className = 'reddog-ai-tools';
    aiToolsEl.setAttribute('data-reddog-tools', '');

    var html = '';

    // Global video projections do not own the selected product's house field.
    if (!productDiscovery) {
      // Category projection
      html += '<div class="reddog-tools-group">';
      html += '<div class="reddog-tools-label">Category</div>';
      html += '<div class="reddog-tools-row">';
      for (var i = 0; i < CATEGORIES.length; i++) {
        var c = CATEGORIES[i];
        html += '<button class="reddog-tool-pill' + (c.id === currentCategory ? ' active' : '') + '"'
              + ' data-reddog-category="' + c.id + '" type="button">' + esc(c.label) + '</button>';
      }
      html += '</div></div>';

      // Creator/entity projection hook
      html += '<div class="reddog-tools-group">';
      html += '<div class="reddog-tools-label">Creator / Entity</div>';
      html += '<div class="reddog-tools-row">';
      html += '<button class="reddog-tool-pill" data-reddog-creator-search type="button">Search\u2026</button>';
      html += '</div></div>';
    }

    // Density presets
    html += '<div class="reddog-tools-group">';
    html += '<div class="reddog-tools-label">Layout</div>';
    if (!productDiscovery) {
      html += '<button class="reddog-tool-pill" data-reddog-browse-rows type="button">Adaptive category rows</button>';
    }
    html += '<div class="reddog-tools-row reddog-tools-row-wrap">';
    for (var j = 0; j < DENSITY_PRESETS.length; j++) {
      var d = DENSITY_PRESETS[j];
      html += '<button class="reddog-tool-pill reddog-density-pill' + (d.id === currentDensity ? ' active' : '') + '"'
            + ' data-reddog-density="' + d.id + '" type="button">' + (d.label || d.id) + '</button>';
    }
    html += '</div></div>';

    // Motion mode: Snap / Glide
    html += '<div class="reddog-tools-group">';
    html += '<div class="reddog-tools-label">Motion</div>';
    html += '<div class="reddog-tools-row">';
    html += '<button class="reddog-tool-pill reddog-motion-pill' + (currentMotionMode === 'snap' ? ' active' : '') + '"'
          + ' data-reddog-motion="snap" type="button">Snap</button>';
    html += '<button class="reddog-tool-pill reddog-motion-pill' + (currentMotionMode === 'glide' ? ' active' : '') + '"'
          + ' data-reddog-motion="glide" type="button">Glide</button>';
    html += '</div></div>';

    aiToolsEl.innerHTML = html;

    // Insert before options section
    var optionsSection = plane.querySelector('[data-reddog-options]');
    if (optionsSection) {
      optionsSection.parentNode.insertBefore(aiToolsEl, optionsSection);
    } else {
      conciergeHost.appendChild(aiToolsEl);
    }

    // Wire click handlers
    aiToolsEl.addEventListener('click', function (e) {
      if (productDiscovery && !discoveryAdmitted) return;
      var catBtn = e.target.closest('[data-reddog-category]');
      if (catBtn) {
        setCategory(catBtn.getAttribute('data-reddog-category'));
        return;
      }

      if (e.target.closest('[data-reddog-browse-rows]')) {
        if (!productDiscovery && window.mallTileField && typeof window.mallTileField.setLayoutMode === 'function') {
          window.mallTileField.setLayoutMode('rows');
        }
        return;
      }

      var denBtn = e.target.closest('[data-reddog-density]');
      if (denBtn) {
        setDensity(denBtn.getAttribute('data-reddog-density'));
        return;
      }

      var motBtn = e.target.closest('[data-reddog-motion]');
      if (motBtn) {
        setMotionMode(motBtn.getAttribute('data-reddog-motion'));
        return;
      }

      var creatorBtn = e.target.closest('[data-reddog-creator-search]');
      if (creatorBtn) {
        if (!productDiscovery) {
          emitRedDogCommand('search_creator', {});
          injectChannels();
          toggleSearchInput(true);
        }
        return;
      }
    });
  }

  // ---- channel attachment surface ----
  var channelsEl = null;
  var attachedChannels = {}; // id -> boolean
  var storedCatalog = []; // set by setFoundUps()

  var CHANNEL_PLATFORMS = [
    { type: 'youtube_channel',  icon: '\u25B6',  label: 'YouTube' },
    { type: 'linkedin_profile', icon: '\uD83D\uDD17', label: 'LinkedIn' },
    { type: 'x_account',       icon: '\uD835\uDD4F', label: 'X' },
    { type: 'autopost',        icon: '\u2699',  label: 'AutoPost' }
  ];

  function getPlatformMeta(sourceType) {
    for (var i = 0; i < CHANNEL_PLATFORMS.length; i++) {
      if (CHANNEL_PLATFORMS[i].type === sourceType) return CHANNEL_PLATFORMS[i];
    }
    return { type: sourceType, icon: '\u2022', label: sourceType };
  }

  function getChannelsFromCatalog() {
    // Read from catalog stored by setFoundUps()
    var catalog = storedCatalog;
    return catalog.map(function (item) {
      return {
        id: item.foundup_id,
        name: item.title || item.entity || item.foundup_id,
        sourceType: item.source_type,
        sourceHandle: item.source_handle || '',
        videoCount: item.video_count || 0,
        attached: attachedChannels[item.foundup_id] !== false
      };
    });
  }

  function toggleChannelAttach(channelId) {
    if (productDiscovery) return false;
    var current = attachedChannels[channelId] !== false;
    attachedChannels[channelId] = !current;
    var action = current ? 'detach_channel' : 'attach_channel';
    emitRedDogCommand(action, { channelId: channelId, attached: !current });
    refreshChannelsUI();
    renderBriefing();
  }

  function refreshChannelsUI() {
    if (productDiscovery) return;
    if (!channelsEl) return;
    var channels = getChannelsFromCatalog();
    var listEl = channelsEl.querySelector('[data-reddog-channel-list]');
    if (!listEl) return;

    if (!channels.length) {
      listEl.innerHTML = '<p class="reddog-channel-empty">No channels loaded yet.</p>';
      return;
    }

    listEl.innerHTML = channels.map(function (ch) {
      var meta = getPlatformMeta(ch.sourceType);
      var attached = ch.attached;
      return '<div class="reddog-channel-row" data-reddog-channel="' + esc(ch.id) + '">'
        + '<span class="reddog-channel-icon">' + meta.icon + '</span>'
        + '<div class="reddog-channel-info">'
        + '<span class="reddog-channel-name">' + esc(ch.name) + '</span>'
        + '<span class="reddog-channel-meta">' + esc(meta.label)
        + (ch.videoCount > 0 ? ' \u00b7 ' + ch.videoCount + ' videos' : '')
        + (ch.sourceHandle ? ' \u00b7 ' + esc(ch.sourceHandle) : '')
        + '</span>'
        + '</div>'
        + '<button class="reddog-channel-toggle' + (attached ? ' attached' : '') + '"'
        + ' data-reddog-channel-toggle="' + esc(ch.id) + '" type="button">'
        + (attached ? 'On' : 'Off')
        + '</button>'
        + '</div>';
    }).join('');
  }

  function injectChannels() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (channelsEl) return;
    var conciergeHost = plane.querySelector('[data-reddog-concierge]');
    if (!conciergeHost) return;

    channelsEl = document.createElement('div');
    channelsEl.className = 'reddog-channels-section';
    channelsEl.setAttribute('data-reddog-channels', '');

    if (productDiscovery) {
      channelsEl.innerHTML = '<div class="reddog-tools-label">Video Mall</div>'
        + '<a class="reddog-tool-pill" href="/member/">Browse videos in Play Foundups</a>';
      var productOptions = plane.querySelector('[data-reddog-options]');
      if (productOptions) productOptions.parentNode.insertBefore(channelsEl, productOptions);
      else plane.appendChild(channelsEl);
      return;
    }

    var html = '<div class="reddog-tools-label">Channels</div>';
    html += '<div data-reddog-channel-list></div>';

    // Mall projection quick-switch
    html += '<div class="reddog-channel-actions">';
    html += '<button class="reddog-tool-pill" data-reddog-populate-mall type="button">Populate My Mall</button>';
    html += '<button class="reddog-tool-pill" data-reddog-personal-mall type="button">Personal Mall</button>';
    html += '<button class="reddog-tool-pill" data-reddog-search-mall type="button">Search Mall</button>';
    html += '</div>';

    // Search input (hidden by default)
    html += '<div class="reddog-search-container" data-reddog-search-container style="display:none;">';
    html += '<div class="reddog-search-row">';
    html += '<input type="text" class="reddog-search-input" data-reddog-search-input placeholder="Show me videos on Fukui, houses, cars…" aria-label="Search the Mall catalog" maxlength="300" autocomplete="off">';
    html += '<button class="reddog-search-clear" data-reddog-search-clear type="button">&times;</button>';
    html += '</div>';

    // Category filter pills
    html += '<div class="reddog-filter-row" data-reddog-category-filters>';
    html += '<span class="reddog-filter-label">Category:</span>';
    var categories = Array.from(new Set(storedCatalog.map(function(item) { return item.category; }).filter(Boolean))).sort();
    for (var i = 0; i < categories.length; i++) {
      html += '<button class="reddog-filter-pill" data-reddog-category="' + esc(categories[i]).replace(/"/g, '&quot;') + '" type="button">' + esc(categories[i]) + '</button>';
    }
    html += '</div>';

    // Tag filter dropdown
    html += '<div class="reddog-filter-row">';
    html += '<span class="reddog-filter-label">Tag:</span>';
    html += '<select class="reddog-tag-select" data-reddog-tag-select>';
    html += '<option value="">All tags</option>';
    var tags = ['012-lane', 'ffcpln', 'consciousness', 'meditation', 'founders', 'ai', 'music', 'resistance', 'japan', 'expat'];
    for (var j = 0; j < tags.length; j++) {
      html += '<option value="' + tags[j] + '">' + tags[j] + '</option>';
    }
    html += '</select>';
    html += '</div>';

    html += '</div>';

    channelsEl.innerHTML = html;

    // Insert after AI tools, before options
    var aiTools = plane.querySelector('[data-reddog-tools]');
    var optionsSection = plane.querySelector('[data-reddog-options]');
    if (aiTools && aiTools.nextSibling) {
      aiTools.parentNode.insertBefore(channelsEl, aiTools.nextSibling);
    } else if (optionsSection) {
      optionsSection.parentNode.insertBefore(channelsEl, optionsSection);
    } else if (conciergeHost) {
      conciergeHost.appendChild(channelsEl);
    }

    // Wire handlers
    channelsEl.addEventListener('click', function (e) {
      var toggleBtn = e.target.closest('[data-reddog-channel-toggle]');
      if (toggleBtn) {
        toggleChannelAttach(toggleBtn.getAttribute('data-reddog-channel-toggle'));
        return;
      }

      if (e.target.closest('[data-reddog-populate-mall]')) {
        emitRedDogCommand('populate_my_mall', {});
        if (window.mallTileField && typeof window.mallTileField.projectPersonalMall === 'function') {
          window.mallTileField.projectPersonalMall();
        }
        return;
      }

      if (e.target.closest('[data-reddog-personal-mall]')) {
        emitRedDogCommand('open_personal_mall', {});
        if (window.mallTileField && typeof window.mallTileField.projectPersonalMall === 'function') {
          window.mallTileField.projectPersonalMall();
        }
        return;
      }

      if (e.target.closest('[data-reddog-search-mall]')) {
        emitRedDogCommand('open_search_mall', {});
        toggleSearchInput(true);
        return;
      }

      if (e.target.closest('[data-reddog-search-clear]')) {
        clearSearch();
        return;
      }
    });

    // Search input handler
    var searchInput = channelsEl.querySelector('[data-reddog-search-input]');
    if (searchInput) {
      searchInput.addEventListener('input', function (e) {
        var query = e.target.value.trim();
        if (window.mallTileField && typeof window.mallTileField.searchCatalog === 'function') {
          if (query.length > 0) {
            window.mallTileField.searchCatalog(query);
          } else {
            window.mallTileField.clearFieldScope();
          }
        }
      });

      searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          clearSearch();
        }
      });
    }

    // Category filter handlers
    var categoryFilters = channelsEl.querySelectorAll('[data-reddog-category]');
    categoryFilters.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var category = btn.getAttribute('data-reddog-category');
        emitRedDogCommand('filter_category', { category: category });

        // Clear other active states
        categoryFilters.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');

        // Clear tag select
        var tagSelect = channelsEl.querySelector('[data-reddog-tag-select]');
        if (tagSelect) tagSelect.value = '';

        // Clear search input
        if (searchInput) searchInput.value = '';

        if (window.mallTileField && typeof window.mallTileField.filterByCategory === 'function') {
          window.mallTileField.filterByCategory(category);
        }
      });
    });

    // Tag filter handler
    var tagSelect = channelsEl.querySelector('[data-reddog-tag-select]');
    if (tagSelect) {
      tagSelect.addEventListener('change', function () {
        var tag = tagSelect.value;
        emitRedDogCommand('filter_tag', { tag: tag });

        // Clear category active states
        categoryFilters.forEach(function (b) { b.classList.remove('active'); });

        // Clear search input
        if (searchInput) searchInput.value = '';

        if (window.mallTileField) {
          if (tag && typeof window.mallTileField.filterByTag === 'function') {
            window.mallTileField.filterByTag(tag);
          } else if (typeof window.mallTileField.clearFieldScope === 'function') {
            window.mallTileField.clearFieldScope();
          }
        }
      });
    }

    refreshChannelsUI();
  }

  /**
   * Toggle search input visibility
   * @param {boolean} show - true to show, false to hide
   */
  function toggleSearchInput(show) {
    if (productDiscovery) return show ? openPlane() : false;
    var container = document.querySelector('[data-reddog-search-container]');
    var input = document.querySelector('[data-reddog-search-input]');
    if (container) {
      container.style.display = show ? 'flex' : 'none';
      if (show && input) {
        input.focus();
      }
    }
  }

  /**
   * Clear search and hide input
   */
  function clearSearch() {
    if (productDiscovery) return false;
    var input = document.querySelector('[data-reddog-search-input]');
    if (input) {
      input.value = '';
    }

    // Clear category filter active states
    var categoryFilters = document.querySelectorAll('[data-reddog-category]');
    categoryFilters.forEach(function (b) { b.classList.remove('active'); });

    // Clear tag select
    var tagSelect = document.querySelector('[data-reddog-tag-select]');
    if (tagSelect) tagSelect.value = '';

    toggleSearchInput(false);
    if (window.mallTileField && typeof window.mallTileField.clearFieldScope === 'function') {
      window.mallTileField.clearFieldScope();
    }
  }

  // ---- context briefing ----
  var briefingEl = null;

  function gatherContext() {
    var ctx = {
      planeOpen: isOpen,
      modesVisible: modesVisible,
      currentMode: currentMode,
      tileCount: 0,
      activeCount: 0,
      inviteText: '',
      projection: null,
      inspecting: null,
      inspectorOpen: false,
      viewOpen: false,
      viewIndex: -1
    };

    // DOM-derived counts from loaded plane data
    var grid = plane.querySelector('[data-account-foundups-grid]');
    ctx.tileCount = grid ? grid.querySelectorAll('.account-foundup-tile').length : 0;
    ctx.activeCount = grid ? grid.querySelectorAll('.status-active, .status-ready').length : 0;
    var countEl = plane.querySelector('[data-invite-count]');
    ctx.inviteText = countEl ? countEl.textContent : '';

    // Mall tile field signals (B's public API, read-only)
    if (window.mallTileField) {
      if (typeof window.mallTileField.getProjection === 'function') {
        ctx.projection = window.mallTileField.getProjection();
      }
      if (typeof window.mallTileField.getInspectingIndex === 'function') {
        ctx.inspecting = window.mallTileField.getInspectingIndex();
      }
      if (typeof window.mallTileField.isInspectorOpen === 'function') {
        ctx.inspectorOpen = window.mallTileField.isInspectorOpen();
      }
    }

    // Mall planes signals (B's public API, read-only)
    if (window.mallPlanes) {
      if (typeof window.mallPlanes.isOpen === 'function') {
        ctx.viewOpen = window.mallPlanes.isOpen();
      }
      if (typeof window.mallPlanes.getActiveIndex === 'function') {
        ctx.viewIndex = window.mallPlanes.getActiveIndex();
      }
    }

    return ctx;
  }

  function renderBriefing() {
    if (!briefingEl) return;
    var ctx = gatherContext();
    var lines = [];

    // FoundUp summary
    if (ctx.tileCount > 0) {
      var line = ctx.tileCount + ' FoundUp' + (ctx.tileCount !== 1 ? 's' : '');
      if (ctx.activeCount > 0) line += ' \u00b7 ' + ctx.activeCount + ' active';
      lines.push(line);
    } else {
      lines.push('No FoundUps loaded');
    }

    // Invite count
    if (ctx.inviteText) {
      lines.push('Invites: ' + ctx.inviteText);
    }

    // Projection mode
    if (currentCategory !== 'all') {
      lines.push('Category: ' + currentCategory);
    } else if (ctx.projection && ctx.projection !== 'default') {
      lines.push('Sorted: ' + ctx.projection);
    }

    // Density and motion
    if (currentDensity !== '3x4') {
      lines.push('Density: ' + currentDensity);
    }
    if (currentMotionMode !== 'snap') {
      lines.push('Motion: ' + currentMotionMode);
    }

    // Active inspection
    if (ctx.inspectorOpen && ctx.inspecting !== null) {
      lines.push('Inspecting tile #' + (ctx.inspecting + 1));
    }

    // FoundUp view plane
    if (ctx.viewOpen && ctx.viewIndex >= 0) {
      lines.push('Viewing FoundUp #' + (ctx.viewIndex + 1));
    }

    briefingEl.innerHTML = lines.map(function (l) {
      return '<p class="reddog-briefing-line">' + esc(l) + '</p>';
    }).join('');
  }

  function injectBriefing() {
    if (briefingEl) return;
    var conciergeHost = plane.querySelector('[data-reddog-concierge]');
    if (!conciergeHost) return;

    briefingEl = document.createElement('div');
    briefingEl.className = 'reddog-context-briefing';
    briefingEl.setAttribute('data-reddog-briefing', '');
    briefingEl.setAttribute('role', 'status');
    briefingEl.setAttribute('aria-label', 'Red Dog context briefing');

    // Product members keep their live account briefing outside the hidden
    // video-only guide. The domain form remains in its own separate host.
    var productOptions = productDiscovery && plane.querySelector('[data-reddog-options]');
    if (productOptions) productOptions.parentNode.insertBefore(briefingEl, productOptions);
    else conciergeHost.insertBefore(briefingEl, conciergeHost.firstChild);
  }

  // ---- recommended actions ----
  var recsEl = null;

  var RECOMMENDATION_RULES = [
    {
      id: 'return_to_mall',
      label: 'Return to Mall',
      test: function (ctx) { return ctx.viewOpen; },
      run: function () {
        if (window.mallPlanes && typeof window.mallPlanes.closeView === 'function') {
          window.mallPlanes.closeView();
        }
      }
    },
    {
      id: 'enter_foundup',
      label: 'Enter FoundUp',
      test: function (ctx) { return ctx.inspectorOpen && ctx.inspecting !== null; },
      run: function () {
        var idx = window.mallTileField && typeof window.mallTileField.getInspectingIndex === 'function'
          ? window.mallTileField.getInspectingIndex() : null;
        if (idx !== null && window.mallTileField && typeof window.mallTileField.enterFoundUp === 'function') {
          window.mallTileField.enterFoundUp(idx);
        }
      }
    },
    {
      id: 'reset_projection',
      label: 'Reset to All',
      test: function (ctx) { return ctx.projection && ctx.projection !== 'default'; },
      run: function () {
        if (window.mallTileField && typeof window.mallTileField.resetProjection === 'function') {
          window.mallTileField.resetProjection();
        }
      }
    },
    {
      id: 'view_active',
      label: 'View active FoundUps',
      test: function (ctx) {
        return ctx.activeCount > 0 && (!ctx.projection || ctx.projection === 'default');
      },
      run: function () {
        if (window.mallTileField && typeof window.mallTileField.setProjection === 'function') {
          window.mallTileField.setProjection('readiness');
        }
      }
    },
    {
      id: 'open_invites',
      label: 'Check Invites',
      test: function (ctx) {
        return ctx.inviteText && invitesDrawer && !invitesDrawer.classList.contains('open');
      },
      run: function () { executeMode('invites'); }
    },
    {
      id: 'view_foundups',
      label: 'View My FoundUps',
      test: function (ctx) { return ctx.tileCount > 0 && !isOpen; },
      run: function () { executeMode('foundups'); }
    },
    {
      id: 'show_summary',
      label: 'Show Summary',
      test: function () { return true; },
      run: function () { showSummary(); }
    }
  ];

  var MAX_RECOMMENDATIONS = 3;

  function getRecommendations() {
    if (productDiscovery && !discoveryAdmitted) return [];
    var ctx = gatherContext();
    // Also check invites drawer expanded state
    ctx.invitesExpanded = invitesDrawer ? invitesDrawer.classList.contains('open') : false;
    var recs = [];
    for (var i = 0; i < RECOMMENDATION_RULES.length && recs.length < MAX_RECOMMENDATIONS; i++) {
      var rule = RECOMMENDATION_RULES[i];
      if (productDiscovery && ['enter_foundup', 'reset_projection', 'view_active'].indexOf(rule.id) !== -1) continue;
      if (rule.test(ctx)) {
        recs.push({ id: rule.id, label: rule.label });
      }
    }
    return recs;
  }

  function runRecommendation(id) {
    if (productDiscovery && (!discoveryAdmitted ||
        ['enter_foundup', 'reset_projection', 'view_active'].indexOf(id) !== -1)) return false;
    for (var i = 0; i < RECOMMENDATION_RULES.length; i++) {
      if (RECOMMENDATION_RULES[i].id === id) {
        RECOMMENDATION_RULES[i].run();
        // Refresh after action
        renderRecommendations();
        renderBriefing();
        return true;
      }
    }
    return false;
  }

  function renderRecommendations() {
    if (!recsEl) return;
    var recs = getRecommendations();
    if (!recs.length) {
      recsEl.innerHTML = '';
      return;
    }
    recsEl.innerHTML = recs.map(function (r) {
      return '<button class="reddog-rec-action" data-reddog-rec="' + esc(r.id) + '" type="button">'
        + esc(r.label) + '</button>';
    }).join('');
  }

  function injectRecommendations() {
    if (recsEl) return;
    var conciergeHost = plane.querySelector('[data-reddog-concierge]');
    if (!conciergeHost) return;

    recsEl = document.createElement('div');
    recsEl.className = 'reddog-recommendations';
    recsEl.setAttribute('data-reddog-recommendations', '');
    recsEl.setAttribute('aria-label', 'Recommended actions');

    // Product briefing is a sibling of the guide, so recommendations follow
    // that same visible account owner. Ordinary Mall placement is unchanged.
    var briefing = (productDiscovery ? plane : conciergeHost).querySelector('[data-reddog-briefing]');
    if (productDiscovery && briefing) {
      briefing.parentNode.insertBefore(recsEl, briefing.nextSibling);
    } else if (productDiscovery && plane.querySelector('[data-reddog-options]')) {
      var productOptions = plane.querySelector('[data-reddog-options]');
      productOptions.parentNode.insertBefore(recsEl, productOptions);
    } else if (briefing && briefing.nextSibling) {
      conciergeHost.insertBefore(recsEl, briefing.nextSibling);
    } else if (briefing) {
      conciergeHost.appendChild(recsEl);
    } else {
      conciergeHost.insertBefore(recsEl, conciergeHost.firstChild);
    }

    // Delegate clicks
    recsEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-reddog-rec]');
      if (!btn) return;
      runRecommendation(btn.getAttribute('data-reddog-rec'));
    });
  }

  // ---- saved videos section ----
  var savedEl = null;

  function injectSavedVideos() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (savedEl) {
      renderSavedVideos();
      return;
    }

    savedEl = document.createElement('section');
    savedEl.setAttribute('data-reddog-saved', '');
    savedEl.className = 'reddog-saved-section';

    var channelsSection = plane.querySelector('[data-reddog-channels]');
    var optionsSection = plane.querySelector('[data-reddog-options]');
    if (channelsSection && channelsSection.nextSibling) {
      channelsSection.parentNode.insertBefore(savedEl, channelsSection.nextSibling);
    } else if (optionsSection) {
      optionsSection.parentNode.insertBefore(savedEl, optionsSection);
    } else if (conciergeHost) {
      conciergeHost.appendChild(savedEl);
    }

    renderSavedVideos();
  }

  function renderSavedVideos() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (!savedEl) return;

    var player = window.mallVideoPlayer;
    var savedMap = (player && typeof player.getSavedVideos === 'function') ? player.getSavedVideos() : {};
    var keys = Object.keys(savedMap);
    var count = keys.length;

    var html = '<div class="reddog-saved-header">';
    html += '<span class="reddog-section-label">Saved Videos</span>';
    html += '<span class="reddog-saved-count">' + count + '</span>';
    html += '</div>';

    if (count === 0) {
      html += '<p class="reddog-saved-empty">No saved videos yet. Swipe left or use Save in the player to save a video.</p>';
      savedEl.innerHTML = html;
      return;
    }

    // Sort by savedAt descending (newest first)
    var entries = keys.map(function (k) { return savedMap[k]; });
    entries.sort(function (a, b) {
      return (b.savedAt || '').localeCompare(a.savedAt || '');
    });

    html += '<div class="reddog-saved-list">';
    entries.forEach(function (entry) {
      var thumb = esc(entry.thumbnail || '');
      var title = esc(entry.title || 'Untitled');
      var foundupId = esc(entry.foundupId || '');
      var videoId = esc(entry.videoId || '');
      var savedDate = entry.savedAt ? new Date(entry.savedAt).toLocaleDateString() : '';

      html += '<button class="reddog-saved-card" data-saved-foundup="' + foundupId + '" data-saved-video="' + videoId + '" type="button">';
      if (thumb) {
        html += '<img class="reddog-saved-thumb" src="' + thumb + '" alt="" loading="lazy">';
      } else {
        html += '<div class="reddog-saved-thumb reddog-saved-thumb-empty"></div>';
      }
      html += '<div class="reddog-saved-info">';
      html += '<span class="reddog-saved-title">' + title + '</span>';
      html += '<span class="reddog-saved-meta">' + foundupId + (savedDate ? ' · ' + savedDate : '') + '</span>';
      html += '</div>';
      html += '</button>';
    });
    html += '</div>';

    savedEl.innerHTML = html;

    // Wire click handlers for re-entry
    savedEl.querySelectorAll('[data-saved-foundup]').forEach(function (card) {
      card.addEventListener('click', function () {
        var fid = card.getAttribute('data-saved-foundup');
        var vid = card.getAttribute('data-saved-video');
        reenterSavedVideo(fid, vid);
      });
    });
  }

  function reenterSavedVideo(foundupId, videoId) {
    if (productDiscovery && !discoveryAdmitted) return;
    emitRedDogCommand('reenter_saved_video', { foundupId: foundupId, videoId: videoId });

    // Try to reconstruct queue from catalog and open fullscreen player
    var player = window.mallVideoPlayer;
    if (player && typeof player.open === 'function' && storedCatalog) {
      var foundup = null;
      for (var i = 0; i < storedCatalog.length; i++) {
        if (storedCatalog[i].foundup_id === foundupId) {
          foundup = storedCatalog[i];
          break;
        }
      }

      if (foundup && foundup.videos && foundup.videos.length > 0) {
        // Find video index in queue
        var startIdx = 0;
        for (var j = 0; j < foundup.videos.length; j++) {
          var v = foundup.videos[j];
          if ((v.video_id || v.videoId || v.id) === videoId) {
            startIdx = j;
            break;
          }
        }
        closePlane();
        player.open(foundupId, foundup.videos, startIdx);
        return;
      }
    }

    // Fallback: open FoundUp entry page
    closePlane();
    window.location.href = '/member/foundup.html?id=' + encodeURIComponent(foundupId);
  }

  // ---- watch history section ----
  var historyEl = null;

  function injectWatchHistory() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (historyEl) {
      renderWatchHistory();
      return;
    }

    historyEl = document.createElement('section');
    historyEl.setAttribute('data-reddog-history', '');
    historyEl.className = 'reddog-history-section';

    var savedSection = plane.querySelector('[data-reddog-saved]');
    var optionsSection = plane.querySelector('[data-reddog-options]');
    if (savedSection && savedSection.nextSibling) {
      savedSection.parentNode.insertBefore(historyEl, savedSection.nextSibling);
    } else if (savedSection) {
      savedSection.parentNode.appendChild(historyEl);
    } else if (optionsSection) {
      optionsSection.parentNode.insertBefore(historyEl, optionsSection);
    } else {
      var conciergeHost = plane.querySelector('[data-reddog-concierge]');
      if (conciergeHost) conciergeHost.appendChild(historyEl);
    }

    renderWatchHistory();
  }

  /** Match mall-video-player MIN_RESUME_SECONDS (5) — only then show “Continue at …”. */
  function formatContinueAt(seconds) {
    if (seconds == null || typeof seconds !== 'number' || isNaN(seconds) || seconds < 5) return '';
    var m = Math.floor(seconds / 60);
    var s = Math.floor(seconds % 60);
    return 'Continue at ' + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function renderWatchHistory() {
    if (productDiscovery && !discoveryAdmitted) return;
    if (!historyEl) return;

    var player = window.mallVideoPlayer;
    var entries = (player && typeof player.getHistory === 'function') ? player.getHistory() : [];
    var count = entries.length;

    var html = '<div class="reddog-history-header">';
    html += '<span class="reddog-section-label">Recently Watched</span>';
    html += '<span class="reddog-history-count">' + count + '</span>';
    if (count > 0) {
      html += '<button class="reddog-history-clear" data-reddog-history-clear type="button">Clear</button>';
    }
    html += '</div>';

    if (count === 0) {
      html += '<p class="reddog-history-empty">No watch history yet. Videos you play will appear here.</p>';
      historyEl.innerHTML = html;
      return;
    }

    html += '<div class="reddog-history-list">';
    entries.forEach(function (entry) {
      var thumb = esc(entry.thumbnail || '');
      var title = esc(entry.title || 'Untitled');
      var foundupId = esc(entry.foundupId || '');
      var videoId = esc(entry.videoId || '');
      var videoIndex = entry.videoIndex != null ? entry.videoIndex : 0;
      var watchDate = entry.timestamp ? new Date(entry.timestamp).toLocaleDateString() : '';

      html += '<button class="reddog-history-card" data-history-foundup="' + foundupId + '" data-history-video="' + videoId + '" data-history-index="' + videoIndex + '" type="button">';
      if (thumb) {
        html += '<img class="reddog-history-thumb" src="' + thumb + '" alt="" loading="lazy">';
      } else {
        html += '<div class="reddog-history-thumb reddog-history-thumb-empty"></div>';
      }
      html += '<div class="reddog-history-info">';
      html += '<span class="reddog-history-title">' + title + '</span>';
      html += '<span class="reddog-history-meta">' + foundupId + (watchDate ? ' \u00b7 ' + watchDate : '') + '</span>';
      var contLabel = formatContinueAt(entry.playbackPosition);
      if (contLabel) {
        html += '<span class="reddog-history-continue-badge">' + esc(contLabel) + '</span>';
      }
      html += '</div>';
      html += '</button>';
    });
    html += '</div>';

    historyEl.innerHTML = html;

    // Wire click handlers for re-entry
    historyEl.querySelectorAll('[data-history-foundup]').forEach(function (card) {
      card.addEventListener('click', function () {
        var fid = card.getAttribute('data-history-foundup');
        var vid = card.getAttribute('data-history-video');
        var idx = parseInt(card.getAttribute('data-history-index'), 10) || 0;
        reenterHistoryVideo(fid, vid, idx);
      });
    });

    // Wire clear button
    var clearBtn = historyEl.querySelector('[data-reddog-history-clear]');
    if (clearBtn) {
      clearBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        clearWatchHistory();
      });
    }
  }

  function reenterHistoryVideo(foundupId, videoId, videoIndex) {
    if (productDiscovery && !discoveryAdmitted) return;
    emitRedDogCommand('reenter_history_video', { foundupId: foundupId, videoId: videoId, videoIndex: videoIndex });

    // Try to reconstruct queue from catalog and open fullscreen player
    var player = window.mallVideoPlayer;
    var resumeOpt = null;
    if (player && typeof player.getHistory === 'function') {
      var hist = player.getHistory();
      for (var hi = 0; hi < hist.length; hi++) {
        if (hist[hi].foundupId === foundupId && hist[hi].videoId === videoId) {
          if (typeof hist[hi].playbackPosition === 'number' && !isNaN(hist[hi].playbackPosition)) {
            resumeOpt = { resumeSeconds: hist[hi].playbackPosition };
          }
          break;
        }
      }
    }
    if (player && typeof player.open === 'function' && storedCatalog) {
      var foundup = null;
      for (var i = 0; i < storedCatalog.length; i++) {
        if (storedCatalog[i].foundup_id === foundupId) {
          foundup = storedCatalog[i];
          break;
        }
      }

      if (foundup && foundup.videos && foundup.videos.length > 0) {
        // Find video index in queue by videoId, fall back to stored videoIndex
        var startIdx = videoIndex;
        for (var j = 0; j < foundup.videos.length; j++) {
          var v = foundup.videos[j];
          if ((v.video_id || v.videoId || v.id) === videoId) {
            startIdx = j;
            break;
          }
        }
        closePlane();
        player.open(foundupId, foundup.videos, startIdx, resumeOpt);
        return;
      }
    }

    // Fallback: open FoundUp entry page
    closePlane();
    window.location.href = '/member/foundup.html?id=' + encodeURIComponent(foundupId);
  }

  window.addEventListener('videoPlayerClose', function () {
    if (historyEl) renderWatchHistory();
  });

  function clearWatchHistory() {
    if (productDiscovery && !discoveryAdmitted) return;
    var player = window.mallVideoPlayer;
    if (player && typeof player.clearHistory === 'function') {
      player.clearHistory();
    }
    renderWatchHistory();
  }

  // Refresh briefing and recommendations every time plane opens
  var _origOpenPlane = openPlane;
  openPlane = function (event) {
    _origOpenPlane(event);
    if (productDiscovery && !discoveryAdmitted) return;
    injectBriefing();
    renderBriefing();
    injectRecommendations();
    renderRecommendations();
    injectAITools();
    injectChannels();
    injectSavedVideos();
    injectWatchHistory();
  };

  // ---- public API: window.redDog ----
  var api = {
    open: openPlane,
    close: closePlane,
    toggle: togglePlane,
    isOpen: function () { return isOpen; },
    showSummary: showSummary,
    dismissSummary: dismissSummary,
    startListening: startListening,
    stopListening: stopListening,
    anchorState: function () { return stateRing ? stateRing.getAttribute('data-reddog-anchor-state') : 'idle'; },
    openModes: openModes,
    closeModes: closeModes,
    toggleModes: toggleModes,
    setMode: executeMode,
    currentMode: function () { return currentMode; },
    isModeSheetOpen: function () { return modesVisible; },
    getContext: gatherContext,
    refreshBriefing: function () { injectBriefing(); renderBriefing(); },
    getRecommendations: getRecommendations,
    runRecommendation: runRecommendation,
    refreshRecommendations: function () { injectRecommendations(); renderRecommendations(); },

    // AI Tools: projection, density, motion mode
    openTools: function () { injectAITools(); executeMode('tools'); },
    setCategory: setCategory,
    getCategory: function () { return currentCategory; },
    setDensity: setDensity,
    getDensity: function () { return currentDensity; },
    setMotionMode: setMotionMode,
    getMotionMode: function () { return currentMotionMode; },

    // Channel attachment
    openChannels: function () { injectChannels(); executeMode('channels'); },
    getChannels: getChannelsFromCatalog,
    toggleChannel: toggleChannelAttach,
    populateMyMall: function () {
      emitRedDogCommand('populate_my_mall', {});
      if (window.mallTileField && typeof window.mallTileField.projectPersonalMall === 'function') {
        window.mallTileField.projectPersonalMall();
      }
    },
    openPersonalMall: function () {
      emitRedDogCommand('open_personal_mall', {});
      if (window.mallTileField && typeof window.mallTileField.projectPersonalMall === 'function') {
        window.mallTileField.projectPersonalMall();
      }
    },
    openSearchMall: function () {
      emitRedDogCommand('open_search_mall', {});
      injectChannels();
      toggleSearchInput(true);
    },
    // Saved Videos
    openSaved: function () { injectSavedVideos(); executeMode('saved'); },
    refreshSaved: function () { renderSavedVideos(); },

    // Watch History
    openHistory: function () { injectWatchHistory(); executeMode('history'); },
    refreshHistory: function () { renderWatchHistory(); },
    clearHistory: function () { clearWatchHistory(); },

    searchCatalog: function(query) {
      if (window.mallTileField && typeof window.mallTileField.searchCatalog === 'function') {
        window.mallTileField.searchCatalog(query);
      }
    },

    searchByCreator: function (query) {
      emitRedDogCommand('search_creator', { query: query });
      if (window.mallTileField && typeof window.mallTileField.searchByCreator === 'function') {
        window.mallTileField.searchByCreator(query);
      }
    },
    clearSearch: clearSearch,

    /** Populate identity block from Clerk user + Firestore data */
    setIdentity: function (clerkUser, userData) {
      var avatarImg = plane.querySelector('[data-account-avatar-img]');
      var avatarPlaceholder = plane.querySelector('[data-account-avatar-placeholder]');
      var nameEl = plane.querySelector('[data-account-name]');
      var handleEl = plane.querySelector('[data-account-handle]');

      // Avatar: use Clerk profile image if available
      var imageUrl = clerkUser && clerkUser.imageUrl;
      if (imageUrl && avatarImg && avatarPlaceholder) {
        avatarImg.src = imageUrl;
        avatarImg.style.display = 'block';
        avatarPlaceholder.style.display = 'none';
      }

      // Also update the header trigger avatar
      var triggerImg = avatarTrigger && avatarTrigger.querySelector('img');
      var triggerPlaceholder = avatarTrigger && avatarTrigger.querySelector('.account-avatar-placeholder');
      if (imageUrl && triggerImg && triggerPlaceholder) {
        triggerImg.src = imageUrl;
        triggerImg.style.display = 'block';
        triggerPlaceholder.style.display = 'none';
      }

      // Name / handle
      var displayName = (clerkUser && clerkUser.firstName) || '';
      var handle = userData && userData.username ? '@' + userData.username : '';

      if (nameEl) nameEl.textContent = displayName || handle || 'Member';
      if (handleEl) handleEl.textContent = handle;

      // Avatar tap goes to Clerk user profile
      var avatarLink = plane.querySelector('[data-account-avatar-link]');
      if (avatarLink && (!productDiscovery || !productProfileBound)) {
        if (productDiscovery) productProfileBound = true;
        avatarLink.addEventListener('click', function () {
          if (productDiscovery && !discoveryAdmitted) return;
          if (window.Clerk && window.Clerk.openUserProfile) {
            if (productDiscovery) closePlane();
            window.Clerk.openUserProfile({ appearance: window.FOUNDUPS_CLERK_APPEARANCE });
          }
        });
      }
    },

    /** Populate FoundUps grid from catalog data */
    setFoundUps: function (catalog) {
      if (productDiscovery) {
        // One card per unambiguous registered identity, never one per house.
        var counts = Object.create(null);
        (Array.isArray(catalog) ? catalog : []).forEach(function (item) {
          if (item && typeof item.foundup_id === 'string' && /^[a-z0-9_]+$/.test(item.foundup_id)) {
            counts[item.foundup_id] = (counts[item.foundup_id] || 0) + 1;
          }
        });
        catalog = (Array.isArray(catalog) ? catalog : []).filter(function (item) {
          return item && typeof item.foundup_id === 'string' &&
            /^[a-z0-9_]+$/.test(item.foundup_id) && counts[item.foundup_id] === 1;
        });
      }
      storedCatalog = catalog || [];
      var grid = plane.querySelector('[data-account-foundups-grid]');
      if (!grid || !catalog) return;

      grid.innerHTML = catalog.map(function (item) {
        var displayName = item.title || item.entity || item.name || item.foundup_id;
        var iconLabel = item.creator_display || item.creator || displayName.slice(0, 3);
        var category = item.category || 'default';
        var status = item.status || item.launch_readiness || 'placeholder';
        var videoHint = (item.video_count > 0) ? ' data-video-count="' + item.video_count + '"' : '';

        var entry = productDiscovery ? '/f/' + encodeURIComponent(item.foundup_id)
          : '/member/foundup.html?id=' + encodeURIComponent(item.foundup_id);
        return '<a class="account-foundup-tile" href="' + entry + '"' + videoHint + '>'
          + '<div class="account-foundup-icon cat-' + esc(category) + '">' + esc(iconLabel.slice(0, 4)) + '</div>'
          + '<span class="account-foundup-name">' + esc(displayName) + '</span>'
          + '<span class="account-foundup-status status-' + esc(status) + '"></span>'
          + '</a>';
      }).join('');
    },

    /** Populate invites drawer */
    setInvites: function (codesWithStatus) {
      var drawer = plane.querySelector('[data-account-invites-drawer]');
      var countEl = invitesToggle && invitesToggle.querySelector('[data-invite-count]');
      if (!drawer) return;

      var activeCount = codesWithStatus.filter(function (c) { return c.status === 'active'; }).length;
      if (countEl) countEl.textContent = activeCount + ' active';

      if (!codesWithStatus.length) {
        drawer.innerHTML = '<p style="font-size:0.82rem;color:rgba(243,241,248,0.4);">No invite codes yet.</p>';
        return;
      }

      drawer.innerHTML = codesWithStatus.map(function (item) {
        var isUsed = item.status !== 'active';
        return '<button class="invite-chip' + (isUsed ? ' used' : '') + '" data-code="' + esc(item.code) + '" type="button">'
          + '<span>' + esc(item.code) + '</span>'
          + '<span>' + esc(item.status) + '</span>'
          + '</button>';
      }).join('');

      // Tap-to-copy on active codes
      drawer.querySelectorAll('.invite-chip:not(.used)').forEach(function (chip) {
        chip.addEventListener('click', function () {
          var code = chip.dataset.code;
          if (!code) return;
          navigator.clipboard.writeText(code).then(function () {
            var original = chip.innerHTML;
            chip.innerHTML = '<span>Copied!</span><span>ready</span>';
            setTimeout(function () { chip.innerHTML = original; }, 1400);
          }).catch(function () {});
        });
      });
    },

    // ---- verification alert skeleton (PFM9) ----
    // WSP 97 truth boundary: RedDog may notify/summarize/open panels.
    // RedDog may NOT judge/deny/finalize protected decisions.

    /**
     * Display a verification alert in RedDog plane.
     * @param {Object} alert - RedDogVerificationAlert object
     * @param {string} alert.alert_id - Unique alert identifier
     * @param {string} alert.event_id - VerificationGapEvent.event_id
     * @param {string} alert.foundup_id - Which FoundUp this relates to
     * @param {string} alert.summary - Human-readable summary
     * @param {string} alert.action_required - "human_review" | "acknowledge" | "info_only"
     * @param {string} [alert.panel_to_open] - "verification_wall" | "task_detail" | "evidence"
     * @param {string} alert.created_at - ISO 8601 timestamp
     * @returns {boolean} true if alert stored, false if invalid
     */
    showVerificationAlert: function (alert) {
      if (!alert || typeof alert !== 'object') return false;
      if (!alert.alert_id || typeof alert.alert_id !== 'string') return false;

      // Store alert (in-memory only - no backend)
      verificationAlerts[alert.alert_id] = {
        alert_id: alert.alert_id,
        event_id: alert.event_id || '',
        foundup_id: alert.foundup_id || '',
        summary: alert.summary || '',
        action_required: alert.action_required || 'info_only',
        panel_to_open: alert.panel_to_open || null,
        created_at: alert.created_at || new Date().toISOString(),
        displayed_at: new Date().toISOString()
      };
      verificationAlertCount++;

      // Emit event for UI renderers (future phase)
      document.dispatchEvent(new CustomEvent('reddog:alert_stored', {
        detail: { alert_id: alert.alert_id, count: verificationAlertCount }
      }));

      return true;
    },

    /**
     * Dismiss a verification alert by ID.
     * @param {string} alertId - The alert_id to dismiss
     * @returns {boolean} true if dismissed, false if not found
     */
    dismissVerificationAlert: function (alertId) {
      if (!alertId || typeof alertId !== 'string') return false;
      if (!verificationAlerts[alertId]) return false;

      delete verificationAlerts[alertId];
      verificationAlertCount = Math.max(0, verificationAlertCount - 1);

      // Emit event for UI renderers (future phase)
      document.dispatchEvent(new CustomEvent('reddog:alert_dismissed', {
        detail: { alert_id: alertId, count: verificationAlertCount }
      }));

      return true;
    },

    /**
     * Get current verification alert count.
     * @returns {number} Number of active alerts
     */
    getVerificationAlertCount: function () {
      return verificationAlertCount;
    },

    /**
     * Get all active verification alerts.
     * @returns {Object} Map of alert_id -> alert object
     */
    getVerificationAlerts: function () {
      // Return shallow copy to prevent external mutation
      var copy = {};
      for (var k in verificationAlerts) {
        if (verificationAlerts.hasOwnProperty(k)) {
          copy[k] = verificationAlerts[k];
        }
      }
      return copy;
    }
  };

  if (productDiscovery) {
    composeProductDiscovery(api);
  }

  // Primary API: window.redDog
  window.redDog = api;

  // Backward compat alias (will be removed in future)
  window.accountConcierge = api;

  // ---- verification alert event listener (PFM9) ----
  // WSP 97: AI agents dispatch 'reddog:verification_alert' to surface anomalies.
  // RedDog stores and displays; RedDog does NOT judge or finalize.
  document.addEventListener('reddog:verification_alert', function (e) {
    if (e.detail && typeof e.detail === 'object') {
      api.showVerificationAlert(e.detail);
    }
  });

  /**
   * Presentation admission comes only from the existing member runtime after
   * its read-only account checks. This flag neither signs in nor grants any
   * backend privilege. Revocation clears account data while preserving the
   * domain-owned search form and results.
   */
  function composeProductDiscovery(memberApi) {
    var memberSelector = '[data-reddog-state], [data-reddog-identity], [data-reddog-foundups], '
      + '[data-reddog-invites], [data-reddog-options], [data-reddog-concierge], '
      + '[data-reddog-tools], [data-reddog-channels], [data-reddog-briefing], '
      + '[data-reddog-recommendations], [data-reddog-saved], [data-reddog-history]';
    var presentation = [];
    var host = plane.querySelector('[data-reddog-discovery]');
    var accountAction = plane.querySelector('[data-reddog-discovery-account]');

    function applyPresentation() {
      plane.setAttribute('data-reddog-admitted', discoveryAdmitted ? 'true' : 'false');
      plane.querySelectorAll(memberSelector).forEach(function (element) {
        var saved = presentation.filter(function (entry) { return entry.element === element; })[0];
        if (!saved) {
          saved = { element: element, hidden: element.hidden, inert: element.hasAttribute('inert') };
          presentation.push(saved);
        }
        // The old video gesture guide is not product help. Domain guidance is
        // supplied by the unchanged form inside the separate discovery host.
        var shown = discoveryAdmitted && !element.hasAttribute('data-reddog-concierge');
        element.hidden = shown ? saved.hidden : true;
        if (!shown || saved.inert) element.setAttribute('inert', '');
        else element.removeAttribute('inert');
      });
      if (host) {
        host.hidden = false;
        host.removeAttribute('inert');
      }
      if (accountAction) accountAction.hidden = discoveryAdmitted;
    }

    function clearMemberPresentation() {
      storedCatalog = [];
      attachedChannels = {};
      verificationAlerts = {};
      verificationAlertCount = 0;
      currentMode = 'idle';
      clearTimeout(tapTimer);
      clearTimeout(holdTimer);
      tapTimer = holdTimer = null;
      lastTapTime = 0;
      isDragging = anchorSwiping = false;
      closeModes();
      dismissSummary();
      stopListening();
      if (summaryContent) summaryContent.innerHTML = '';
      if (invitesDrawer) invitesDrawer.classList.remove('open');
      if (invitesToggle) invitesToggle.classList.remove('expanded');
      ['[data-account-name]', '[data-account-handle]', '[data-invite-count]'].forEach(function (selector) {
        var element = plane.querySelector(selector);
        if (element) element.textContent = '';
      });
      ['[data-account-foundups-grid]', '[data-account-invites-drawer]', '[data-reddog-briefing]',
        '[data-reddog-recommendations]', '[data-reddog-saved]', '[data-reddog-history]'].forEach(function (selector) {
        var element = plane.querySelector(selector);
        if (element) element.innerHTML = '';
      });
      var avatarImg = plane.querySelector('[data-account-avatar-img]');
      var avatarPlaceholder = plane.querySelector('[data-account-avatar-placeholder]');
      var triggerImg = avatarTrigger && avatarTrigger.querySelector('img');
      var triggerPlaceholder = avatarTrigger && avatarTrigger.querySelector('.account-avatar-placeholder');
      [avatarImg, triggerImg].forEach(function (element) {
        if (element) {
          element.removeAttribute('src');
          element.style.display = 'none';
        }
      });
      [avatarPlaceholder, triggerPlaceholder].forEach(function (element) {
        if (element) element.style.display = '';
      });
    }

    // Guard the existing API dynamically, including references captured before
    // revocation. Guest rendering never establishes an admitted account.
    var discoveryMethods = ['open', 'close', 'toggle', 'isOpen', 'anchorState'];
    var globalFieldMethods = ['setCategory', 'populateMyMall', 'openPersonalMall', 'searchCatalog', 'searchByCreator', 'clearSearch', 'toggleChannel'];
    Object.keys(memberApi).forEach(function (name) {
      if (discoveryMethods.indexOf(name) !== -1) return;
      var method = memberApi[name];
      if (typeof method !== 'function') return;
      memberApi[name] = function () {
        if (!discoveryAdmitted || globalFieldMethods.indexOf(name) !== -1) return false;
        return method.apply(memberApi, arguments);
      };
    });

    productDiscoveryController = initializePublicDiscovery({
      publish: false,
      skipPrimaryBindings: true,
      open: function (event) { openPlane(event); },
      onStateChange: function (opened) { isOpen = opened; },
      onAnchorSwipe: function () {
        if (discoveryAdmitted) openModes();
        else openPlane();
      }
    });
    memberApi.registerDiscoveryAdapter = productDiscoveryController.registerDiscoveryAdapter;
    memberApi.openSearchMall = openPlane;
    memberApi.isDiscoveryAdmitted = function () { return discoveryAdmitted; };
    memberApi.setDiscoveryAdmission = function (admitted) {
      discoveryAdmitted = admitted === true;
      if (!discoveryAdmitted) clearMemberPresentation();
      applyPresentation();
      if (discoveryAdmitted && isOpen) {
        openPlane();
        applyPresentation();
      }
      productDiscoveryController.refreshFocus();
      return discoveryAdmitted;
    };
    memberApi.setDiscoveryAdmission(false);
  }

  /**
   * Optional public discovery controller. The normal member path above is
   * unchanged. Domain code owns the form, validation and search results;
   * this owner supplies the existing Red Dog plane, anchors and modal behavior.
   */
  function initializePublicDiscovery(options) {
    options = options || {};
    var host = plane.querySelector('[data-reddog-discovery]');
    if (host) host.hidden = false;
    var closeButton = plane.querySelector('[data-reddog-close]');
    var background = document.querySelector('.mall-shell');
    var trigger = document.getElementById('redDogBtn');
    var triggers = Array.prototype.slice.call(document.querySelectorAll('[data-reddog-open-discovery]'));
    if (trigger && triggers.indexOf(trigger) === -1) triggers.push(trigger);
    var accountTrigger = document.getElementById('mallAvatarTrigger');
    if (accountTrigger && triggers.indexOf(accountTrigger) === -1) triggers.push(accountTrigger);
    var ring = trigger && trigger.querySelector('[data-reddog-anchor-state]');
    var adapter = null;
    var opened = false;
    var returnFocus = null;
    var backgroundWasInert = false;
    var bodyWasOpen = false;
    // The shell and plane are siblings. Never make the dialog's own ancestor inert.
    if (background && background.contains(plane)) background = null;

    function hiddenByDisclosure(element) {
      for (var ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
        if (ancestor.tagName !== 'DETAILS' || ancestor.hasAttribute('open')) continue;
        var summary = Array.prototype.filter.call(ancestor.children, function (child) {
          return child.tagName === 'SUMMARY';
        })[0];
        if (!summary || !summary.contains(element)) return true;
      }
      return false;
    }

    function available(element) {
      return !!element && element.isConnected && !element.disabled &&
        !element.closest('[hidden], [inert], [aria-hidden="true"]') &&
        !hiddenByDisclosure(element) &&
        element.getClientRects().length > 0;
    }

    function controls() {
      return Array.prototype.slice.call(plane.querySelectorAll(
        'a[href], button, input, select, textarea, summary, [tabindex]'
      )).filter(function (element) {
        return element.tabIndex >= 0 && !element.matches(':disabled') && available(element);
      });
    }

    function focusSearch() {
      var candidates = controls();
      var preferred = adapter && adapter.focusElement;
      if (candidates.indexOf(preferred) === -1) {
        preferred = candidates.filter(function (element) { return host && host.contains(element); })[0];
      }
      (preferred || candidates[0] || plane).focus({ preventScroll: true });
    }

    function setState() {
      triggers.forEach(function (element) {
        element.setAttribute('aria-expanded', opened ? 'true' : 'false');
      });
      if (ring) ring.setAttribute('data-reddog-anchor-state', opened ? 'active' : 'idle');
      if (options.onStateChange) options.onStateChange(opened);
    }

    function openDiscovery(event) {
      if (opened) return;
      // Touch activation does not focus buttons in every browser.
      returnFocus = event && triggers.indexOf(event.currentTarget) !== -1
        ? event.currentTarget : document.activeElement;
      // Use the existing detail owner to leave its modal before opening search.
      if (window.mallPlanes && typeof window.mallPlanes.isOpen === 'function' &&
          window.mallPlanes.isOpen() && typeof window.mallPlanes.closeView === 'function') {
        window.mallPlanes.closeView();
      }
      backgroundWasInert = !!background && background.hasAttribute('inert');
      bodyWasOpen = document.body.classList.contains('surface-open');
      opened = true;
      plane.removeAttribute('inert');
      plane.setAttribute('aria-hidden', 'false');
      plane.classList.add('open');
      scrim.classList.add('open');
      document.body.classList.add('surface-open');
      if (background) background.setAttribute('inert', '');
      setState();
      focusSearch();
    }

    function closeDiscovery() {
      if (!opened) return;
      opened = false;
      plane.classList.remove('open');
      scrim.classList.remove('open');
      plane.setAttribute('inert', '');
      if (background && !backgroundWasInert) background.removeAttribute('inert');
      if (!bodyWasOpen) document.body.classList.remove('surface-open');
      setState();
      var target = returnFocus !== document.body && available(returnFocus)
        ? returnFocus : triggers.filter(available)[0];
      if (target) target.focus({ preventScroll: true });
      returnFocus = null;
      plane.setAttribute('aria-hidden', 'true');
    }

    function registerDiscoveryAdapter(options) {
      var element = options && options.element;
      var focusElement = options && options.focusElement;
      if (!host || !element || element.nodeType !== 1 || element.ownerDocument !== document ||
          element === host || element.contains(host) ||
          (focusElement && (focusElement.nodeType !== 1 || !element.contains(focusElement))) ||
          (adapter && adapter.element !== element)) return false;
      // Move, never clone or rebuild: form values and domain listeners survive.
      if (!host.contains(element)) host.appendChild(element);
      adapter = { element: element, focusElement: focusElement || null };
      // Late catalog registration must not steal focus from an active form control.
      if (opened && !plane.contains(document.activeElement)) focusSearch();
      return true;
    }

    plane.setAttribute('role', 'dialog');
    plane.setAttribute('aria-modal', 'true');
    plane.setAttribute('aria-hidden', 'true');
    plane.setAttribute('tabindex', '-1');
    plane.setAttribute('inert', '');
    scrim.setAttribute('aria-hidden', 'true');
    triggers.forEach(function (element) {
      element.setAttribute('aria-haspopup', 'dialog');
      element.setAttribute('aria-controls', plane.id);
      // Native click supports keyboard activation. It also stays idempotent
      // after a shared gesture recognizer observes a swipe on the same anchor.
      if (!options.skipPrimaryBindings || (element !== trigger && element !== accountTrigger)) {
        element.addEventListener('click', options.open || openDiscovery);
      }
    });
    setState();
    if (closeButton) closeButton.addEventListener('click', closeDiscovery);
    scrim.addEventListener('click', closeDiscovery);

    document.addEventListener('keydown', function (event) {
      if (!opened) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        closeDiscovery();
      } else if (event.key === 'Tab') {
        var candidates = controls();
        var index = candidates.indexOf(document.activeElement);
        if (!candidates.length) {
          event.preventDefault();
          plane.focus({ preventScroll: true });
        } else if (index === -1 || (event.shiftKey && index === 0) ||
            (!event.shiftKey && index === candidates.length - 1)) {
          event.preventDefault();
          candidates[event.shiftKey ? candidates.length - 1 : 0].focus({ preventScroll: true });
        }
      }
    }, true);
    document.addEventListener('focusin', function (event) {
      if (opened && !plane.contains(event.target)) focusSearch();
    });

    // Reuse the shared recognizer only at the protected anchors/handle.
    // Swiping within the domain form remains native vertical scrolling.
    if (window.gestureZone) {
      var top = document.querySelector('[data-anchor="top"]');
      var bottom = document.getElementById('redDogAnchor');
      var handle = plane.querySelector('.account-plane-handle');
      if (top) window.gestureZone(top, { onSwipe: function (direction) {
        if (direction === 'down') (options.open || openDiscovery)();
      } });
      if (bottom) window.gestureZone(bottom, { onSwipe: function (direction) {
        if (direction === 'up') (options.onAnchorSwipe || options.open || openDiscovery)();
      } });
      if (handle) window.gestureZone(handle, { onSwipe: function (direction) {
        if (direction === 'up') closeDiscovery();
      } });
    }

    var discoveryApi = {
      open: openDiscovery,
      openSearchMall: openDiscovery,
      close: closeDiscovery,
      toggle: function () { if (opened) closeDiscovery(); else openDiscovery(); },
      isOpen: function () { return opened; },
      anchorState: function () { return opened ? 'active' : 'idle'; },
      registerDiscoveryAdapter: registerDiscoveryAdapter,
      refreshFocus: function () {
        if (opened && (!plane.contains(document.activeElement) || !available(document.activeElement))) focusSearch();
      }
    };
    if (options.publish !== false) {
      window.redDog = discoveryApi;
      window.accountConcierge = discoveryApi;
    }
    return discoveryApi;
  }

  // ---- escape helper ----
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }
})();
