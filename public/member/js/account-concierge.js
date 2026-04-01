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

  var avatarTrigger = document.getElementById('mallAvatarTrigger');
  var redDogTrigger = document.getElementById('redDogBtn');
  var invitesToggle = plane.querySelector('[data-account-invites-toggle]');
  var invitesDrawer = plane.querySelector('[data-account-invites-drawer]');
  var signOutBtn = plane.querySelector('[data-account-signout]');

  var isOpen = false;

  // ---- swipe tracking ----
  var touchStartY = 0;
  var touchCurrentY = 0;
  var isDragging = false;
  var SWIPE_THRESHOLD = 60;

  // ---- open / close ----
  function openPlane() {
    if (isOpen) return;
    isOpen = true;
    plane.classList.add('open');
    scrim.classList.add('open');
    document.body.classList.add('surface-open');
    setAnchorState('active');
  }

  function closePlane() {
    if (!isOpen) return;
    isOpen = false;
    plane.classList.remove('open');
    scrim.classList.remove('open');
    document.body.classList.remove('surface-open');
    if (!listeningVisible) setAnchorState('idle');
  }

  function togglePlane() {
    if (isOpen) closePlane();
    else openPlane();
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
    if (!summaryEl || !summaryContent) return;
    // Build shell-owned summary from loaded data
    var lines = [];
    var grid = plane.querySelector('[data-account-foundups-grid]');
    var tileCount = grid ? grid.querySelectorAll('.account-foundup-tile').length : 0;
    var readyCount = grid ? grid.querySelectorAll('.status-ready').length : 0;
    var countEl = plane.querySelector('[data-invite-count]');
    var inviteText = countEl ? countEl.textContent : '';

    if (tileCount > 0) {
      lines.push(tileCount + ' FoundUp' + (tileCount !== 1 ? 's' : '') + (readyCount > 0 ? ' \u00b7 ' + readyCount + ' ready' : ''));
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
      e.stopPropagation();
      // Start hold timer
      holdTimer = setTimeout(function () {
        startListening();
      }, HOLD_THRESHOLD);
    });

    redDogTrigger.addEventListener('pointerup', function (e) {
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
          togglePlane();
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
  }

  // ---- mode sheet (JS-injected into anchor) ----
  var modeSheetEl = null;
  var modesVisible = false;
  var currentMode = 'idle';

  var MODE_ACTIONS = [
    { id: 'summary',   label: 'Summary',     icon: '\u2139' },
    { id: 'listen',    label: 'Listen',       icon: '\uD83C\uDFA4' },
    { id: 'tools',     label: 'AI Tools',     icon: '\uD83D\uDD27' },
    { id: 'foundups',  label: 'My FoundUps',  icon: '\uD83D\uDCE6' },
    { id: 'invites',   label: 'Invites',      icon: '\uD83D\uDCE8' },
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

  if (anchor) {
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
      togglePlane();
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
  if (mallShell) {
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
    touchStartY = e.touches[0].clientY;
    isDragging = true;
  }, { passive: true });

  plane.addEventListener('touchmove', function (e) {
    if (!isDragging) return;
    touchCurrentY = e.touches[0].clientY;
  }, { passive: true });

  plane.addEventListener('touchend', function () {
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
      var expanded = invitesDrawer.classList.toggle('open');
      invitesToggle.classList.toggle('expanded', expanded);
    });
  }

  // ---- sign out ----
  if (signOutBtn) {
    signOutBtn.addEventListener('click', async function () {
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
  var currentDensity = '3x4';
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
    { id: '2x3', cols: 2, rows: 3 },
    { id: '3x4', cols: 3, rows: 4 },
    { id: '3x5', cols: 3, rows: 5 },
    { id: '5x8', cols: 5, rows: 8 }
  ];

  function emitRedDogCommand(command, detail) {
    document.dispatchEvent(new CustomEvent('reddog:command', {
      detail: Object.assign({ command: command }, detail || {})
    }));
  }

  function setCategory(categoryId) {
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
    currentDensity = presetId;
    var preset = null;
    for (var i = 0; i < DENSITY_PRESETS.length; i++) {
      if (DENSITY_PRESETS[i].id === presetId) { preset = DENSITY_PRESETS[i]; break; }
    }
    if (window.mallTileField && typeof window.mallTileField.setDensity === 'function') {
      window.mallTileField.setDensity(preset ? preset.cols : 3, preset ? preset.rows : 4);
    }
    emitRedDogCommand('set_density', { preset: presetId, cols: preset ? preset.cols : 3, rows: preset ? preset.rows : 4 });
    refreshToolsUI();
  }

  function setMotionMode(mode) {
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
    if (aiToolsEl) return;
    var conciergeHost = plane.querySelector('[data-reddog-concierge]');
    if (!conciergeHost) return;

    aiToolsEl = document.createElement('div');
    aiToolsEl.className = 'reddog-ai-tools';
    aiToolsEl.setAttribute('data-reddog-tools', '');

    var html = '';

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

    // Density presets
    html += '<div class="reddog-tools-group">';
    html += '<div class="reddog-tools-label">Density</div>';
    html += '<div class="reddog-tools-row">';
    for (var j = 0; j < DENSITY_PRESETS.length; j++) {
      var d = DENSITY_PRESETS[j];
      html += '<button class="reddog-tool-pill reddog-density-pill' + (d.id === currentDensity ? ' active' : '') + '"'
            + ' data-reddog-density="' + d.id + '" type="button">' + d.id + '</button>';
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
      var catBtn = e.target.closest('[data-reddog-category]');
      if (catBtn) {
        setCategory(catBtn.getAttribute('data-reddog-category'));
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
        emitRedDogCommand('search_creator', {});
        return;
      }
    });
  }

  // ---- context briefing ----
  var briefingEl = null;

  function gatherContext() {
    var ctx = {
      planeOpen: isOpen,
      modesVisible: modesVisible,
      currentMode: currentMode,
      tileCount: 0,
      readyCount: 0,
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
    ctx.readyCount = grid ? grid.querySelectorAll('.status-ready').length : 0;
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
      if (ctx.readyCount > 0) line += ' \u00b7 ' + ctx.readyCount + ' ready';
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

    // Insert at the top of the concierge section
    conciergeHost.insertBefore(briefingEl, conciergeHost.firstChild);
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
      id: 'view_ready',
      label: 'View ready FoundUps',
      test: function (ctx) {
        return ctx.readyCount > 0 && (!ctx.projection || ctx.projection === 'default');
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
    var ctx = gatherContext();
    // Also check invites drawer expanded state
    ctx.invitesExpanded = invitesDrawer ? invitesDrawer.classList.contains('open') : false;
    var recs = [];
    for (var i = 0; i < RECOMMENDATION_RULES.length && recs.length < MAX_RECOMMENDATIONS; i++) {
      var rule = RECOMMENDATION_RULES[i];
      if (rule.test(ctx)) {
        recs.push({ id: rule.id, label: rule.label });
      }
    }
    return recs;
  }

  function runRecommendation(id) {
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

    // Insert after briefing (if present) or at top
    var briefing = conciergeHost.querySelector('[data-reddog-briefing]');
    if (briefing && briefing.nextSibling) {
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

  // Refresh briefing and recommendations every time plane opens
  var _origOpenPlane = openPlane;
  openPlane = function () {
    _origOpenPlane();
    injectBriefing();
    renderBriefing();
    injectRecommendations();
    renderRecommendations();
    injectAITools();
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
      if (avatarLink) {
        avatarLink.addEventListener('click', function () {
          if (window.Clerk && window.Clerk.openUserProfile) {
            window.Clerk.openUserProfile({ appearance: window.FOUNDUPS_CLERK_APPEARANCE });
          }
        });
      }
    },

    /** Populate FoundUps grid from catalog data */
    setFoundUps: function (catalog) {
      var grid = plane.querySelector('[data-account-foundups-grid]');
      if (!grid || !catalog) return;

      grid.innerHTML = catalog.map(function (item) {
        return '<a class="account-foundup-tile" href="/member/foundup.html?id=' + encodeURIComponent(item.foundup_id) + '">'
          + '<div class="account-foundup-icon theme-' + esc(item.theme) + '">' + esc(item.token_symbol) + '</div>'
          + '<span class="account-foundup-name">' + esc(item.name) + '</span>'
          + '<span class="account-foundup-status status-' + esc(item.launch_readiness) + '"></span>'
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
    }
  };

  // Primary API: window.redDog
  window.redDog = api;

  // Backward compat alias (will be removed in future)
  window.accountConcierge = api;

  // ---- escape helper ----
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }
})();
