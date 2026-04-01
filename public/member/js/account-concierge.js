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
