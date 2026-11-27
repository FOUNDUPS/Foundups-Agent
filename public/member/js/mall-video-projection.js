(function () {
  'use strict';

  // Dedicated public hosts start guest discovery without member account reads.
  // hpc.foundups.com mounts the single-FoundUp HPC Shorts projection;
  // play.foundups.com mounts the open p.fMALL discovery landing for all FoundUps,
  // Public cards/video stay readable. Account and contribution intents use the
  // existing same-host sign-in/invite flow; this is not a graph ACL or writer.
  const OPEN_MALL_ORIGIN = 'https://play.foundups.com';
  const dedicatedHosts = new Map([
    ['hpc.foundups.com', 'hpc'],
    ['play.foundups.com', 'mall']
  ]);
  if (/^foundupscom--(?:play-open-v2[34]|play-v24-(?:iphone|phone|mobile)|play-v2[56]-iphone|play-v26-(?:controls|gestures|home|home2))-[a-z0-9]+\.(?:web\.app|firebaseapp\.com)$/.test(window.location.hostname)) {
    dedicatedHosts.set(window.location.hostname, 'mall');
  }
  const publicScopes = new Set(['hpc', 'voteballots']);
  let scopedPhoneDock = null;
  const memberPaths = new Set(['/member', '/member/', '/member/index.html']);
  // Keep this display label aligned with the shell cache generation.
  const mallBuild = 'v26';
  const buildLabel = `<small class="mall-build-label">Build ${mallBuild} · Home &amp; Dock</small>`;

  function hostScope(location) {
    return dedicatedHosts.get(location?.hostname) || null;
  }

  function isOpenMallHost(location) {
    return hostScope(location) === 'mall';
  }

  // Presentation only: a guest HPC projection retains its existing gated Add
  // entry even on a Mall/preview host. This never establishes editor eligibility.
  function isPublicBrowseOnly(location) {
    return isOpenMallHost(location) && !isAdmissionRequest(location) && resolve(location) !== 'hpc';
  }

  function isAdmissionRequest(location) {
    if (!location) return false;
    if (/^\/sso-callback\/?$/.test(location.pathname || '')) return true;
    const query = new URLSearchParams(location.search || '');
    return [...query.keys()].some(key =>
      ['signin', 'auth', 'admission', 'invite', 'invitation', 'code', 'state', 'error'].includes(key) ||
      key.startsWith('__clerk'));
  }

  function publicEntryPath(location) {
    if (!isOpenMallHost(location) || !memberPaths.has(location?.pathname) || isAdmissionRequest(location)) return null;
    const entries = new URLSearchParams(location.search || '').getAll('enter');
    return entries.length === 1 ? memberEntryPath(entries[0]) : null;
  }

  function shouldLoadMemberAuth(location) {
    return !hostScope(location) || isAdmissionRequest(location) ||
      (new URLSearchParams(location?.search || '').has('enter') && !publicEntryPath(location));
  }

  function dedicatedLandingPath(location) {
    if (!hostScope(location) || !['/', '/index.html'].includes(location?.pathname) || isAdmissionRequest(location)) return null;
    const query = new URLSearchParams(location.search || '');
    // An old entry link must resolve its intended read-only card, not disappear.
    if (query.has('enter')) {
      const entries = query.getAll('enter');
      return entries.length === 1 ? memberEntryPath(entries[0]) : null;
    }
    return '/member/' + (location.search || '') + (location.hash || '');
  }

  // Planning/test seam only. The apex does not invoke this redirect in v26.
  function plannedApexLandingUrl(location) {
    if (location?.hostname !== 'foundups.com' || !['/', '/index.html'].includes(location.pathname) ||
        isAdmissionRequest(location)) return null;
    const query = new URLSearchParams(location.search || '');
    if (['enter', 'foundup', 'return_to', 'next'].some(key => query.has(key))) return null;
    return OPEN_MALL_ORIGIN + '/' + (location.search || '') + (location.hash || '');
  }

  function portalOrigin(location = window.location) {
    // A preview remains isolated, including its auth callback. The production
    // HPC site uses Play's existing gate; no provider configuration is changed.
    return isOpenMallHost(location) && location.origin ? location.origin : OPEN_MALL_ORIGIN;
  }

  function signInUrl(location = window.location) {
    return portalOrigin(location) + '/?signin=required';
  }

  function authCompletionPath(location = window.location) {
    return hostScope(location) ? '/member/?admission=resume' : '/member/';
  }

  function validFoundUpId(value) {
    return typeof value === 'string' &&
      /^[a-z0-9][a-z0-9_-]{0,63}$/i.test(value) &&
      value !== '__proto__' &&
      value !== 'constructor' &&
      value !== 'prototype'
      ? value
      : null;
  }

  function resolve(location) {
    if (!location || !memberPaths.has(location.pathname)) return null;
    if (isAdmissionRequest(location) || new URLSearchParams(location.search || '').has('enter')) return null;
    const scope = hostScope(location);
    if (scope === 'mall') {
      const requested = new URLSearchParams(location.search).getAll('foundup');
      if (requested.length === 1 && requested[0] === 'move2japan') return null;
      if (requested.length === 1 && publicScopes.has(requested[0])) return requested[0];
      return 'mall';
    }
    return scope;
  }

  // Member boot uses this presentation selection after checking admission.
  function resolveMember(location) {
    if (!location || !memberPaths.has(location.pathname) || (hostScope(location) && !isAdmissionRequest(location))) return null;
    const requested = new URLSearchParams(location.search).getAll('foundup');
    return requested.length === 1 && publicScopes.has(requested[0]) ? requested[0] : null;
  }

  function resolveMemberEntry(location) {
    if (!location || !memberPaths.has(location.pathname) || (hostScope(location) && !isAdmissionRequest(location))) return null;
    const requested = new URLSearchParams(location.search).getAll('enter');
    return requested.length === 1 ? validFoundUpId(requested[0]) : null;
  }

  function memberPath(foundupId) {
    return publicScopes.has(foundupId) ? '/member/?foundup=' + foundupId : null;
  }

  function memberEntryPath(foundupId) {
    const clean = validFoundUpId(foundupId);
    return clean ? '/member/foundup.html?id=' + encodeURIComponent(clean) : null;
  }

  function memberPortalUrl(foundupId) {
    const clean = validFoundUpId(foundupId);
    return clean
      ? portalOrigin() + memberEntryPath(clean)
      : signInUrl();
  }

  function isPhoneDockLayout() {
    return ['phone', 'grid'].includes(document.documentElement.dataset.mallVideoLayout) ||
      !window.matchMedia?.('(min-width: 900px) and (hover: hover) and (pointer: fine)').matches;
  }

  function showContributionReview(intent, admitted = false, returnFocusTo = document.activeElement) {
    if (!intent || !['add-foundup', 'add-video'].includes(intent.action)) return false;
    const old = document.getElementById('mallContributionReview');
    if (old?.open) return false;
    old?.remove();
    const dialog = document.createElement('dialog');
    dialog.id = 'mallContributionReview';
    dialog.className = 'mall-member-search-options mall-contribution-review';
    dialog.setAttribute('aria-labelledby', 'mallContributionTitle');
    const title = document.createElement('h2');
    title.id = 'mallContributionTitle';
    title.textContent = intent.action === 'add-video' ? 'Add Video' : 'Add FoundUp';
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = admitted
      ? 'Sign-in and the existing invite check completed. Submission is unavailable until the owning service verifies current membership and editor permission. No contribution has been submitted.'
      : 'Sign-in and membership are required for contributions at every level. Video curation starts with 012 as the HPC editor. The browser cannot grant editor permission.';
    const detail = document.createElement('p');
    detail.textContent = intent.action === 'add-video'
      ? 'Video is the current HPC type. This pilot restores a review step; it does not publish to the curated catalog.'
      : 'The trailing + adds a FoundUp. Registration/publication requires the existing owning service; this pilot does not create a parallel registry.';
    const signIn = document.createElement('button');
    signIn.type = 'button';
    signIn.className = 'mall-search-option';
    signIn.textContent = admitted ? 'Contribution service not enabled' : 'Sign in and check membership';
    const sameHostReturn = new URL(signInUrl(), window.location.href).origin === window.location.origin;
    signIn.disabled = admitted || !sameHostReturn;
    if (!admitted && !sameHostReturn) {
      signIn.textContent = 'Contribution return not connected';
      status.textContent = 'HPC contribution sign-in return is not connected. Keep browsing; no contribution has been submitted.';
    }
    signIn.addEventListener('click', () => {
      if (admitted || !sameHostReturn) return;
      if (!window.mallStateRestore?.rememberAdmissionIntent?.(intent)) {
        status.textContent = 'The safe return could not be saved. No sign-in or submission was started.';
        return;
      }
      window.mallStateRestore.save();
      window.location.assign(signInUrl());
    });
    const close = document.createElement('button');
    close.type = 'button'; close.textContent = 'Back to browsing';
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('keydown', event => { if (event.key === 'Escape') event.stopPropagation(); });
    dialog.addEventListener('close', () => {
      if (returnFocusTo?.isConnected && !returnFocusTo.closest('[inert]')) returnFocusTo.focus({ preventScroll: true });
      dialog.remove();
    }, { once: true });
    dialog.append(title, status, detail, signIn, close);
    document.body.append(dialog);
    dialog.showModal();
    (signIn.disabled ? close : signIn).focus({ preventScroll: true });
    return true;
  }

  function canonicalEntryId(item) {
    if (!item || typeof item !== 'object') return null;
    // Explicit null marks a source/project card without a FoundUp doorway.
    // Older projections retain their existing identity; format is not admission.
    const id = Object.prototype.hasOwnProperty.call(item, 'canonical_foundup_id')
      ? item.canonical_foundup_id : item.foundup_id || item.id;
    return validFoundUpId(id);
  }

  function scopedRedDogPath(scope) {
    return publicScopes.has(scope) ? '/f/' + encodeURIComponent(scope) + '#red-dog' : null;
  }

  function openScopedRedDog(scope) {
    if (!publicScopes.has(scope)) return;
    window.mallStateRestore?.save();
    return window.redDog?.openConversation?.();
  }

  function cameraDestination() {
    const target = new URL('https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/');
    const caller = new URL(window.location.href);
    const hosts = new Set(['hpc.foundups.com', 'play.foundups.com', 'foundups.com']);
    const paths = new Set(['/', '/member', '/member/', '/member/index.html']);
    const snapshot = caller.hostname === 'hpc.foundups.com' && /^\/member\/hpc-v(?:25|26)\/$/.test(caller.pathname);
    const queries = [...caller.searchParams];
    if (caller.protocol === 'https:' && !caller.port && !caller.username && !caller.password &&
        hosts.has(caller.hostname) && (paths.has(caller.pathname) || snapshot) && !caller.hash &&
        (queries.length === 0 || (queries.length === 1 && queries[0][0] === 'foundup' && queries[0][1] === 'hpc')) &&
        caller.href.length <= 1024) target.searchParams.set('return_to', caller.href);
    return target.href;
  }

  function discoveryPath(foundupId, pocUrl) {
    for (const [host, scope] of dedicatedHosts) {
      if (!publicScopes.has(scope) || foundupId !== scope) continue;
      const url = 'https://' + host + '/';
      // Recognize a cached discovery card from before the host split.
      if (pocUrl === url || pocUrl === 'https://foundups.com' + memberPath(scope)) return url;
    }
    return null;
  }

  // Select install metadata in the head, before the public catalog loads.
  const hpcTitle = 'HPC';
  const hpcPortrait = '/member/hpc-icon-192.png';
  // Root navigation is owned by the gateway's dedicatedLandingPath guard.
  if (typeof document !== 'undefined' && window.location && resolve(window.location) === 'hpc') {
    document.title = hpcTitle;
    document.querySelector('link[rel="manifest"]').href = '/member/hpc.webmanifest';
    document.querySelector('link[rel="apple-touch-icon"]').href = '/member/hpc-icon-180.png';
    const icon = document.querySelector('link[rel="icon"]');
    icon.href = hpcPortrait;
    icon.setAttribute('sizes', '192x192');
    const appleTitle = document.createElement('meta');
    appleTitle.name = 'apple-mobile-web-app-title';
    appleTitle.content = hpcTitle;
    document.head.append(appleTitle);
  }

  function bindDictation(form, input, mic, stopButton, status) {
    const hint = 'Use the microphone on your keyboard to dictate.';
    let attempt = 0;
    let active = null;
    let starting = false;
    let finishing = false;
    let timer;
    function idle() {
      clearTimeout(timer);
      active = null;
      starting = false;
      finishing = false;
      form.removeAttribute('data-dictating');
      form.removeAttribute('data-dictation-hold');
      mic.setAttribute('aria-pressed', 'false');
      stopButton.hidden = true;
    }
    function cancel() {
      attempt += 1;
      const recognition = active;
      idle();
      recognition?.abort();
      status.textContent = '';
    }
    function stop() {
      if (finishing) return;
      if (!active) {
        if (starting) cancel();
        return;
      }
      finishing = true;
      status.textContent = 'Finishing dictation…';
      try { active.stop(); } catch { cancel(); }
    }
    window.addEventListener('pagehide', cancel);
    document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
    input.addEventListener('input', cancel);
    form.addEventListener('focusout', (event) => {
      if (!form.contains(event.relatedTarget)) cancel();
    });
    for (const button of [mic, stopButton]) {
      for (const eventType of ['pointerdown', 'mousedown']) {
        button.addEventListener(eventType, (event) => {
          if (active || starting) event.preventDefault();
        });
      }
    }
    async function start(fromHold = false) {
      cancel();
      if (document.hidden || !input.getClientRects().length) return;
      input.focus(); // Keep iOS keyboard dictation reachable on the original tap.
      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!Recognition?.available || !('processLocally' in Recognition.prototype)) {
        status.textContent = hint;
        return;
      }
      const request = attempt;
      const lang = navigator.language || 'en-US';
      starting = true;
      form.setAttribute('data-dictating', '');
      form.toggleAttribute('data-dictation-hold', fromHold);
      mic.setAttribute('aria-pressed', 'true');
      stopButton.hidden = false;
      status.textContent = 'Starting dictation…';
      timer = setTimeout(cancel, 15000);
      try {
        const availability = await Recognition.available({ langs: [lang], processLocally: true });
        if (request !== attempt || document.hidden) return;
        if (availability !== 'available') {
          idle();
          status.textContent = hint;
          return;
        }
        const recognition = new Recognition();
        let receivedTranscript = false;
        recognition.lang = lang;
        recognition.processLocally = true;
        recognition.onstart = () => {
          if (request === attempt && !finishing) status.textContent = 'Listening for search…';
        };
        recognition.onresult = (event) => {
          if (request !== attempt) return;
          const transcript = event.results[0]?.[0]?.transcript?.trim();
          if (!transcript) return;
          receivedTranscript = true;
          input.value = transcript.slice(0, input.maxLength);
          status.textContent = 'Dictation added. Press Search.';
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };
        recognition.onerror = () => { if (request === attempt) status.textContent = hint; };
        recognition.onend = () => {
          if (request !== attempt) return;
          idle();
          if (!receivedTranscript) status.textContent = hint;
        };
        active = recognition;
        recognition.start();
      } catch {
        if (request === attempt) {
          idle();
          status.textContent = hint;
        }
      }
    }
    mic.addEventListener('click', () => { if (active || starting) stop(); else start(); });
    stopButton.addEventListener('click', () => {
      if (document.activeElement === stopButton) input.focus({ preventScroll: true });
      stop();
    });
    return { start, stop, cancel };
  }

  function bindOptions(trigger, open) {
    let start = null, echoUntil = 0;
    trigger.addEventListener('click', event => {
      if ((event.pointerType === 'touch' || event.sourceCapabilities?.firesTouchEvents === true) &&
          performance.now() < echoUntil) { event.preventDefault(); return; }
      open();
    });
    trigger.addEventListener('touchstart', event => {
      start = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY, at: performance.now() } : null;
      event.stopPropagation();
    }, { passive: true });
    trigger.addEventListener('touchmove', event => {
      if (event.touches.length !== 1 || (start && Math.hypot(event.touches[0].clientX - start.x, event.touches[0].clientY - start.y) >= 15)) start = null;
    }, { passive: true });
    trigger.addEventListener('touchcancel', () => { start = null; }, { passive: true });
    trigger.addEventListener('touchend', event => {
      const tap = start; start = null;
      event.stopPropagation();
      if (!tap || event.touches.length || event.changedTouches.length !== 1 || performance.now() - tap.at > 600 ||
          Math.hypot(event.changedTouches[0].clientX - tap.x, event.changedTouches[0].clientY - tap.y) >= 15) return;
      // A trusted touch may have no compatibility click. Consume only this tap,
      // with a trigger-local echo fence; keyboard and other controls stay live.
      event.preventDefault();
      echoUntil = performance.now() + 400;
      open();
    }, { passive: false });
    window.gestureZone?.(trigger, {
      onSwipe(direction) {
        // Preserve ordinary Mall/other projections. HPC's dock capture owns
        // its distinct Tile types swipe and never opens both dialogs.
        if (direction === 'up' && document.documentElement.dataset.mallVideoScope !== 'hpc') open();
      }
    });
  }

  function bindDictationHold(trigger, dictation) {
    let timer;
    let held = false;
    let pressed = false;
    function cancel() {
      clearTimeout(timer);
      if (pressed && held) dictation.cancel();
      pressed = false;
      held = false;
    }
    trigger.title = 'Open Red Dog conversation';
    trigger.addEventListener('pointerdown', (event) => {
      if (!event.isPrimary || event.button !== 0) return;
      held = false;
      pressed = true;
      timer = setTimeout(() => {
        held = true;
        window.redDog?.openConversation?.();
      }, 500);
    });
    trigger.addEventListener('pointerup', () => {
      if (!pressed) return;
      pressed = false;
      clearTimeout(timer);
      // Speech transport is independently admitted by the conversation owner.
    });
    trigger.addEventListener('pointerleave', cancel);
    trigger.addEventListener('pointercancel', cancel);
    window.addEventListener('pagehide', cancel);
    trigger.addEventListener('contextmenu', (event) => event.preventDefault());
    trigger.addEventListener('click', (event) => {
      if (event.detail && held) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
      held = false;
    });
    return cancel;
  }

  function createMemberDock(label, submit, openRedDog, redDogHref) {
    let contextual = false;
    const element = document.createElement('div');
    element.className = 'mall-member-search-dock';
    const optionsLabel = redDogHref ? 'More options' : 'Search options';
    const dogLogo = '<img src="/logo-dog.png" alt="" width="30" height="30">';
    const dogAction = redDogHref || openRedDog
      ? `<button class="mall-search-dog" type="button" aria-label="Open Red Dog conversation">${dogLogo}</button>` : '';
    element.innerHTML = `
      <form class="mall-member-search-bar" role="search">
        <p role="status"></p>
        <button class="mall-search-plus" type="button" aria-haspopup="dialog">+</button>
        <textarea rows="1" maxlength="300" inputmode="search" enterkeyhint="search"></textarea>
        <button class="mall-search-submit" type="submit" aria-label="Search" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4"/></svg>
        </button>
        <button class="mall-search-add" type="button" aria-label="Add FoundUp" title="Add FoundUp">+</button>
        <button class="mall-search-camera" type="button" aria-label="Open AutoPost camera">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 7h4l2-3h6l2 3h4v13H3z"/><circle cx="12" cy="13" r="3.5"/>
          </svg>
        </button>
        ${dogAction}
        <button class="mall-search-stop" type="button" aria-label="Stop dictation" hidden>
          <span class="mall-dictation-stop" aria-hidden="true"></span>
        </button>
      </form>
      <dialog class="mall-member-search-options">
        <button class="mall-search-option" type="button" data-action="home" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10h-6v-6H9v6H3z"/></svg>Home
        </button>
        <button class="mall-search-option" type="button" data-action="about" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-9v1"/></svg>About this FoundUp
        </button>
        <button class="mall-search-option" type="button" data-action="browse-ai">AI / Browse AI</button>
        <div data-browse-ai-pilot hidden></div>
        <a class="mall-search-option" data-action="camera" href="https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h4l2-3h6l2 3h4v13H3z"/><circle cx="12" cy="13" r="3.5"/></svg>AutoPost camera and photos
        </a>
        <fieldset class="mall-video-options">
          <legend>Video</legend>
          <details data-video-settings><summary>Interface, Gestures and Playback</summary>
          <fieldset><legend>Interface</legend>
          <label>Tap a video tile <select data-video-option="tileTapDestination"><option value="floating">Floating</option><option value="wikitube">WikiTube</option><option value="full-video">Fullscreen in app</option></select></label>
          <label>Add Video tile <select data-video-option="addVideoPosition"><option value="last">Last</option><option value="first">First</option></select></label>
          <button type="button" class="mall-search-option" data-tile-types>Tile types</button>
          <label>Collapse Full Video to <select data-video-option="collapseDestination"><option value="mall">Mall</option><option value="wikitube">WikiTube</option></select></label>
          <label><input type="checkbox" data-video-option="revealSelectedPlayer"> Show parked player when I select a clip</label>
          </fieldset>
          <fieldset><legend>Gestures</legend>
          <label>Pinch out <select data-video-option="pinchOutDestination"><option value="wikitube">WikiTube</option><option value="full-video">Fullscreen in app</option></select></label>
          <label>Pinch in return <select data-video-option="pinchInDestination"><option value="" disabled>Keep current return</option><option value="wikitube">WikiTube</option><option value="mall">Mall tiles</option></select></label>
          <label>Swipe up return <select data-video-option="swipeUpDestination"><option value="" disabled>Keep current gesture</option><option value="wikitube">WikiTube</option><option value="mall">Mall tiles</option></select></label>
          <label>Full Video swipe left <select data-video-option="fullVideoSwipeRight"><option value="next">Next video</option><option value="previous">Previous video</option><option value="none">No action</option></select></label>
          <label>Tucked tab swipe right <select data-video-option="tuckedSwipeRight"><option value="next-hidden">Next video, stay hidden</option><option value="next-reveal">Next video and reveal</option><option value="restore">Restore current video</option><option value="none">No action</option></select></label>
          <small>Use the frame edges for app gestures. Gestures inside YouTube belong to YouTube.</small>
          </fieldset>
          <fieldset><legend>Playback</legend>
          <label><input type="checkbox" data-video-option="autoplayNext"> Autoplay</label>
          <small>Automatically continue the visible video queue in any presentation. Deliberate Play and Next still work when off.</small>
          <small>A fully hidden player stays paused. Browser/provider playback rules still apply.</small>
          </fieldset>
          </details>
          <a data-player-source target="_blank" rel="noopener noreferrer" hidden></a>
          <details data-video-commands><summary>Playback actions</summary>
          <div class="mall-video-actions">
            <button type="button" data-player-action="previous">Previous video</button>
            <button type="button" data-player-action="next">Next video</button>
            <button type="button" data-player-action="play">Play / resume video</button>
            <button type="button" data-player-action="expand">Expand video</button>
            <button type="button" data-player-action="collapse">Collapse video</button>
            <button type="button" data-player-action="hide">Hide video</button>
            <button type="button" data-player-action="save">Save video</button>
            <button type="button" data-player-action="share">Share video</button>
            <button type="button" data-player-action="enter" hidden>Enter FoundUp</button>
            <button type="button" data-player-action="return">Return to tiles</button>
            <button type="button" data-player-action="close">Close video</button>
          </div>
          </details>
        </fieldset>
        <label class="mall-daemon-toggle"><input type="checkbox" data-daemon-toggle> Open DAEmon</label>
        <section data-daemon-panel aria-label="DAEmon activity" hidden>
          <div data-daemon-feed></div>
          <details data-preview-diagnostics hidden><summary>Playback diagnostics</summary><div data-mall-daemon-diagnostics></div></details>
        </section>
        ${buildLabel}
        <form method="dialog"><button type="submit">Close</button></form>
      </dialog>`;
    const form = element.querySelector('.mall-member-search-bar');
    const input = form.querySelector('textarea');
    const submitButton = form.querySelector('.mall-search-submit');
    const dialog = element.querySelector('dialog');
    const daemonToggle = dialog.querySelector('[data-daemon-toggle]');
    const daemonPanel = dialog.querySelector('[data-daemon-panel]');
    let activityMonitor = null, activityView = null;
    daemonToggle.addEventListener('change', async () => {
      daemonPanel.hidden = !daemonToggle.checked;
      if (!daemonToggle.checked) { activityMonitor?.setEnabled(false); placeOptions(); return; }
      try {
        const local = await import('/member/js/mall-local-activity.js?v=26');
        if (!daemonToggle.checked) return;
        activityMonitor ||= local.createLocalActivityMonitor(window);
        activityView ||= local.mountLocalActivityView(dialog.querySelector('[data-daemon-feed]'), activityMonitor);
        activityMonitor.setEnabled(true);
        activityView.refresh();
        placeOptions();
      } catch {
        daemonToggle.checked = false;
        dialog.querySelector('[data-daemon-feed]').textContent = 'Activity view is unavailable on this build.';
        placeOptions();
      }
    });
    const options = form.querySelector('.mall-search-plus');
    dialog.prepend(dialog.querySelector('[data-action="browse-ai"]'),
      dialog.querySelector('[data-browse-ai-pilot]'), dialog.querySelector('.mall-video-options'));
    const add = form.querySelector('.mall-search-add');
    const publicBrowseOnly = isPublicBrowseOnly(window.location);
    add.hidden = publicBrowseOnly;
    add.disabled = publicBrowseOnly;
    add.addEventListener('click', () => {
      if (isPublicBrowseOnly(window.location)) return;
      const scope = document.documentElement.dataset.mallVideoScope;
      const intent = { action: scope === 'hpc' ? 'add-video' : 'add-foundup' };
      if (scope === 'hpc') {
        intent.foundupId = 'hpc';
        const videoId = window.mallVideoPlayer?.getCurrentVideoId?.();
        if (/^[A-Za-z0-9_-]{11}$/.test(videoId || '')) intent.videoId = videoId;
      }
      showContributionReview(intent, false, add);
    });
    options.setAttribute('aria-label', optionsLabel);
    dialog.setAttribute('aria-label', optionsLabel);
    form.setAttribute('aria-label', label);
    input.setAttribute('aria-label', label);
    input.placeholder = label;
    const dictation = bindDictation(form, input, document.createElement('button'),
      form.querySelector('.mall-search-stop'), form.querySelector('[role="status"]'));
    const camera = form.querySelector('.mall-search-camera');
    const cameraLink = dialog.querySelector('[data-action="camera"]');
    const openCamera = (event) => {
      event.preventDefault();
      dictation.cancel(); dialog.close();
      window.mallStateRestore?.save();
      window.location.assign(cameraDestination());
    };
    camera.addEventListener('click', openCamera);
    cameraLink.addEventListener('click', openCamera);

    function fitInput() {
      if (element.hidden) return;
      submitButton.hidden = !input.value.trim();
      form.removeAttribute('data-expanded');
      input.style.height = '';
      if (input.value && input.scrollHeight > input.clientHeight + 1) {
        form.setAttribute('data-expanded', '');
        input.style.height = input.scrollHeight + 'px';
      }
    }
    input.addEventListener('input', fitInput);
    input.addEventListener('change', fitInput);
    input.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' || event.isComposing || event.shiftKey) return;
      event.preventDefault();
      form.requestSubmit();
    });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      dictation.cancel();
      submit(input.value.trim());
    });
    function placeOptions() {
      if (!dialog.open) return;
      const rect = options.getBoundingClientRect();
      const viewport = window.visualViewport;
      const top = viewport?.offsetTop || 0;
      const height = viewport?.height || window.innerHeight;
      const barTop = form.getBoundingClientRect().top;
      const above = barTop - top - 16;
      const fitsAbove = above >= 144;
      const left = viewport?.offsetLeft || 0;
      const right = left + (viewport?.width || window.innerWidth);
      dialog.style.left = `clamp(max(${left + 12}px, var(--safe-left)), ${rect.left}px, ` +
        `calc(${right - dialog.offsetWidth}px - max(12px, var(--safe-right))))`;
      dialog.style.bottom = (window.innerHeight - (fitsAbove ? barTop : top + height) + 8) + 'px';
      dialog.style.maxHeight = Math.max(0, Math.min(height * .65, fitsAbove ? above : height - 16)) + 'px';
    }
    let detachedOptionsParent = null;
    let optionsReturnFocus = null;
    function showOptions(fromPlayer = false) {
      if (dialog.open || (element.hidden && fromPlayer !== true)) return;
      optionsReturnFocus = fromPlayer === true ? document.activeElement : options;
      if (element.hidden) {
        // Reuse this dialog for a floating card on a desktop whose search dock
        // is hidden. Never clone the dock or move/reload the provider frame.
        detachedOptionsParent = dialog.parentElement;
        document.body.append(dialog);
      }
      dictation.cancel();
      const prefs = window.mallStateRestore?.getVideoOptions?.();
      for (const input of dialog.querySelectorAll('[data-video-option]')) {
        if (!prefs) continue;
        const value = prefs[input.dataset.videoOption];
        if (input.type === 'checkbox') input.checked = value;
        else input.value = value === undefined ? '' : value;
      }
      for (const button of dialog.querySelectorAll('[data-player-action]')) {
        button.disabled = window.mallVideoPlayer?.isOpen?.() !== true || window.mallVideoPlayer?.isMallHidden?.() === true;
        if (button.dataset.playerAction === 'enter') button.hidden = window.mallVideoPlayer?.canEnterFoundUp?.() !== true;
      }
      const source = dialog.querySelector('[data-player-source]');
      const attribution = window.mallVideoPlayer?.getAttribution?.();
      source.hidden = true;
      source.removeAttribute('href');
      if (attribution) {
        try {
          const url = new URL(attribution.url);
          if (url.protocol === 'https:' && !url.username && !url.password) {
            source.href = url.href;
            source.textContent = [attribution.title, attribution.label].filter(Boolean).join(' · ');
            source.hidden = false;
          }
        } catch { /* Untrusted catalog links never become menu navigation. */ }
      }
      if (!element.hidden) options.focus({ preventScroll: true });
      if (activityMonitor) {
        daemonToggle.checked = activityMonitor.getSnapshot().enabled;
        daemonPanel.hidden = !daemonToggle.checked;
      }
      dialog.showModal();
      activityView?.refresh();
      placeOptions();
    }
    dialog.querySelector('.mall-video-actions').addEventListener('click', event => {
      const action = event.target.closest('[data-player-action]')?.dataset.playerAction;
      if (!action) return;
      // These commands transfer focus through the player/field owner. The
      // asynchronously delivered dialog close must not steal it back to +.
      if (['expand', 'collapse', 'hide', 'enter', 'return', 'close'].includes(action)) optionsReturnFocus = null;
      dialog.close();
      const player = window.mallVideoPlayer;
      if (action === 'play') { player?.untuck?.({ immediate: true }); player?.requestPlay?.(); }
      else if (action === 'next' || action === 'previous') {
        player?.untuck?.({ immediate: true });
        if (action === 'next') player?.next?.();
        else player?.prev?.();
      }
      else if (action === 'expand') player?.openPinchDestination?.();
      else if (action === 'collapse') player?.collapseAppVideo?.();
      else if (action === 'hide') player?.tuck?.();
      else if (action === 'save') player?.save?.();
      else if (action === 'share') player?.share?.();
      else if (action === 'enter') player?.enterFoundUp?.();
      else if (action === 'return') player?.returnToMall?.();
      else if (action === 'close') player?.close?.();
    });
    window.addEventListener('resize', () => { fitInput(); placeOptions(); });
    window.visualViewport?.addEventListener('resize', placeOptions);
    window.visualViewport?.addEventListener('scroll', placeOptions);
    bindOptions(options, showOptions);
    const typePicker = document.createElement('dialog');
    typePicker.className = 'mall-member-search-options mall-tile-type-picker';
    typePicker.setAttribute('aria-label', 'Tile types');
    typePicker.innerHTML = '<h2>Tile types</h2><button type="button" data-type-video>Video</button>' +
      '<button type="button" disabled>Image</button><button type="button" disabled>Podcast</button>' +
      '<p>Image and podcast browsing is not connected to this video collection yet.</p>' +
      '<form method="dialog"><button>Close</button></form>';
    element.append(typePicker);
    let typeReturnFocus = null, dockSwipe = null, dockSwipeEchoUntil = 0;
    function showTileTypes() {
      if (typePicker.open) return;
      typeReturnFocus = document.activeElement;
      optionsReturnFocus = null;
      dialog.close();
      typePicker.showModal();
    }
    dialog.querySelector('[data-tile-types]').addEventListener('click', showTileTypes);
    typePicker.querySelector('[data-type-video]').addEventListener('click', () => typePicker.close());
    typePicker.addEventListener('close', () => {
      const target = typeReturnFocus?.isConnected && !typeReturnFocus.closest('dialog:not([open]),[inert]') ? typeReturnFocus : input;
      typeReturnFocus = null;
      target.focus({ preventScroll: true });
    });
    typePicker.addEventListener('keydown', event => { if (event.key === 'Escape') event.stopPropagation(); });
    // Only a deliberate gesture STARTING on the resting dock is consumed.
    // Focused typing, camera/dog/actions, provider input and page swipes retain
    // their existing owners. No touch layer is placed over a media frame.
    form.addEventListener('touchstart', event => {
      dockSwipe = document.documentElement.dataset.mallVideoScope === 'hpc' && event.touches.length === 1 && document.activeElement !== input &&
        !event.target.closest('button:not(.mall-search-plus),a') ?
        { x: event.touches[0].clientX, y: event.touches[0].clientY, at: performance.now(), consumed: false } : null;
    }, { capture: true, passive: true });
    form.addEventListener('touchmove', event => {
      if (!dockSwipe || event.touches.length !== 1) { dockSwipe = null; return; }
      const dx = event.touches[0].clientX - dockSwipe.x, dy = event.touches[0].clientY - dockSwipe.y;
      if (performance.now() - dockSwipe.at > 650 || Math.abs(dx) > 24 || dy > 15) { dockSwipe = null; return; }
      if (dy < -60 && -dy > Math.abs(dx) * 1.6) { dockSwipe.consumed = true; event.preventDefault(); }
    }, { capture: true, passive: false });
    form.addEventListener('touchend', event => {
      const swipe = dockSwipe; dockSwipe = null;
      if (!swipe?.consumed || event.touches.length) return;
      event.preventDefault(); event.stopImmediatePropagation();
      dockSwipeEchoUntil = performance.now() + 400;
      showTileTypes();
    }, { capture: true, passive: false });
    form.addEventListener('touchcancel', () => { dockSwipe = null; }, { passive: true });
    form.addEventListener('click', event => {
      if (event.detail && performance.now() < dockSwipeEchoUntil) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);
    for (const input of dialog.querySelectorAll('[data-video-option]')) {
      input.addEventListener('change', () => {
        const value = input.type === 'checkbox' ? input.checked : input.value;
        window.mallStateRestore?.setVideoOptions?.({ [input.dataset.videoOption]: value });
      });
    }
    let browsePilot = null;
    const browseHost = dialog.querySelector('[data-browse-ai-pilot]');
    dialog.querySelector('[data-action="browse-ai"]').addEventListener('click', async event => {
      const button = event.currentTarget;
      browseHost.hidden = false;
      button.disabled = true;
      try {
        const { mountBrowseAiPilot } = await import('/member/js/mall-browser-ai-pilot.js?v=26');
        if (!dialog.open) return;
        browsePilot?.destroy();
        browsePilot = mountBrowseAiPilot(browseHost, { returnFocusTo: button });
        placeOptions();
      } catch (_) {
        browseHost.textContent = 'Browse AI pilot is unavailable in this runtime. No model was loaded.';
      } finally {
        dialog.querySelector('[data-action="browse-ai"]').disabled = false;
      }
    });
    dialog.addEventListener('close', () => {
      browsePilot?.destroy(); browsePilot = null; browseHost.hidden = true;
      if (detachedOptionsParent?.isConnected) detachedOptionsParent.append(dialog);
      detachedOptionsParent = null;
      const returnFocus = optionsReturnFocus;
      optionsReturnFocus = null;
      if (returnFocus?.isConnected && !returnFocus.closest('[inert]') && returnFocus.getClientRects().length) {
        returnFocus.focus({ preventScroll: true });
      }
    });
    dialog.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') event.stopPropagation();
    });
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      event.stopPropagation();
      dialog.close();
    });
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    const autoPost = cameraLink;
    autoPost.addEventListener('click', () => dialog.close());
    const dog = form.querySelector('.mall-search-dog');
    const cancelHold = dog && bindDictationHold(dog, dictation);
    if (redDogHref) {
      dog.addEventListener('click', () => { dog.focus({ preventScroll: true }); window.mallStateRestore?.save(); window.redDog?.openConversation?.(); });
    } else if (openRedDog) {
      dog.addEventListener('click', () => {
        dog.focus({ preventScroll: true });
        window.mallStateRestore?.save();
        window.redDog?.openConversation?.();
      });
    }
    return {
      element, input, dialog, dictation, fitInput,
      showVideoOptions() { showOptions(true); dialog.querySelector('[data-video-commands]').open = true; dialog.querySelector('.mall-video-options')?.scrollIntoView({ block: 'nearest' }); },
      setScoped(scoped) {
        // AutoPost is a working existing action, not a model placeholder.
        autoPost.hidden = false;
        const hpc = document.documentElement.dataset.mallVideoScope === 'hpc';
        dialog.querySelector('[data-video-option="addVideoPosition"]').closest('label').hidden = !hpc;
        dialog.querySelector('[data-tile-types]').hidden = !hpc;
        const scopedActions = scoped && (hpc || document.documentElement.dataset.mallVideoScope === 'voteballots');
        add.hidden = publicBrowseOnly || scopedActions;
        if (scopedActions) {
          options.setAttribute('aria-label', 'Available actions');
          options.title = 'Available actions';
          dialog.setAttribute('aria-label', 'Available actions');
        }
        add.setAttribute('aria-label', hpc ? 'Add Video' : 'Add FoundUp');
        add.title = hpc ? 'Add Video' : 'Add FoundUp';
      },
      setValue(value) { input.value = value; fitInput(); },
      isDefaultContext() { return !contextual; },
      useSearchContext(nextSubmit, nextLabel, value) {
        const previous = { submit, label: input.getAttribute('aria-label'), value: input.value,
          start: input.selectionStart, end: input.selectionEnd };
        const scopeOptions = [...dialog.querySelectorAll('[data-action="home"], [data-action="about"]')]
          .map((option) => ({ option, hidden: option.hidden }));
        cancelHold?.(); dialog.close(); dictation.cancel();
        contextual = true;
        submit = nextSubmit;
        form.setAttribute('aria-label', nextLabel);
        input.setAttribute('aria-label', nextLabel);
        input.placeholder = nextLabel;
        input.value = value;
        // Scoped Home/information remain available from the sole Dock + entry
        // while its existing dock is loaned to the player.
        fitInput();
        return () => {
          cancelHold?.(); dialog.close(); dictation.cancel();
          submit = previous.submit;
          contextual = false;
          form.setAttribute('aria-label', previous.label);
          input.setAttribute('aria-label', previous.label);
          input.placeholder = previous.label;
          input.value = previous.value;
          input.setSelectionRange(previous.start, previous.end);
          scopeOptions.forEach(({ option, hidden }) => { option.hidden = hidden; });
          fitInput();
        };
      },
      hide() { cancelHold?.(); dialog.close(); typePicker.close(); dictation.cancel(); element.hidden = true; }
    };
  }

  function mountMemberDock() {
    const anchor = document.getElementById('redDogAnchor');
    if (!anchor || !window.redDog?.open || anchor.querySelector('.mall-member-search-dock')) return;
    const field = window.mallTileField;
    const dock = createMemberDock('Search the Mall', (query) => {
      field.searchCatalog(query);
      window.mallStateRestore?.save();
    });
    dock.input.addEventListener('input', () => {
      if (dock.isDefaultContext() && !dock.input.value && field.getFieldScope()?.type === 'query') {
        field.searchCatalog('');
        window.mallStateRestore?.save();
      }
    });
    anchor.prepend(dock.element);
    scopedPhoneDock = { scope: null, dock };
    dock.setScoped(false);
    const filters = document.getElementById('mallProjection');
    if (document.documentElement.dataset.mallOpenLanding === 'play' && filters) {
      filters.classList.add('mall-open-filter-options');
      dock.dialog.insertBefore(filters, dock.dialog.querySelector('.mall-build-label'));
    }
    dock.setValue(field.getFieldScope()?.query || '');
    window.redDog.bindSearchDictation?.(dock.dictation);
    window.visualViewport?.addEventListener('resize', () => {
      const viewport = window.visualViewport;
      const keyboard = dock.element.contains(document.activeElement) && viewport.scale === 1
        ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
      anchor.style.setProperty('--member-dock-keyboard', keyboard + 'px');
    });
    dock.input.addEventListener('blur', () => anchor.style.removeProperty('--member-dock-keyboard'));
  }

  function createPhoneDock(actions, scope, disclosure, onHome, searchLabel = 'Search HPC Mall') {
    const field = window.mallTileField;
    const dock = createMemberDock(searchLabel, search, () => {
      window.mallStateRestore?.save();
      window.redDog.openConversation();
    });
    scopedPhoneDock = { scope, dock };
    const { element, dialog, input } = dock;
    element.id = 'videoScopePhoneDock';
    element.hidden = true;
    dialog.id = 'videoScopeOptions';
    element.querySelector('[aria-haspopup="dialog"]').setAttribute('aria-controls', dialog.id);
    dock.setScoped(true);
    actions.append(element);
    const viewport = window.visualViewport;
    if (viewport) {
      const alignWithKeyboard = () => {
        const keyboard = document.activeElement === input && viewport.scale === 1
          ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
        actions.parentElement.style.setProperty('--video-dock-keyboard', keyboard + 'px');
      };
      viewport.addEventListener('resize', alignWithKeyboard);
      viewport.addEventListener('scroll', alignWithKeyboard);
      input.addEventListener('blur', alignWithKeyboard);
    }
    function search(query) {
      field.setScopedPhoneQuery(query);
      dock.setValue(field.getScopedPhoneQuery());
      window.mallStateRestore.save();
    }
    input.addEventListener('input', () => {
      if (dock.isDefaultContext() && !input.value && field.getScopedPhoneQuery()) search('');
    });
    const home = dialog.querySelector('[data-action="home"]');
    const about = dialog.querySelector('[data-action="about"]');
    home.hidden = about.hidden = false;
    about.lastChild.textContent = 'Site information';
    home.addEventListener('click', () => { dialog.close(); search(''); onHome?.(); });
    about.addEventListener('click', () => { dialog.close(); disclosure.showModal(); });
    return {
      show(visible) {
        if (!dock.isDefaultContext()) return;
        if (!visible) return dock.hide();
        element.hidden = false;
        dock.setValue(field.getScopedPhoneQuery());
      }
    };
  }

  async function mountOpenMall() {
    const element = (id) => document.getElementById(id);
    const field = element('mallTileField');
    document.documentElement.dataset.mallOpenLanding = 'play';
    document.title = 'Play FoundUps Mall | FoundUPS';
    element('gestureHints')?.remove();
    element('loadingState').style.display = 'none';
    element('memberArea').style.display = 'block';

    const home = document.querySelector('.mall-header .mall-brand-minimal');
    if (home) {
      home.href = '/member/';
      home.setAttribute('aria-label', 'Return to Play FoundUps Mall');
      home.addEventListener('click', () => window.mallStateRestore?.save?.());
    }

    const handle = element('mallUserHandle');
    const avatarTrigger = element('mallAvatarTrigger');
    const selfAnchor = document.querySelector('.mall-self-anchor');
    if (handle) handle.textContent = 'Member Portal';
    if (avatarTrigger) {
      avatarTrigger.setAttribute('aria-label', 'Open Play account');
      avatarTrigger.title = 'Open Play account';
    }
    function openPlayAccount(event) {
      event.preventDefault();
      event.stopPropagation();
      if (!window.mallStateRestore?.rememberAdmissionIntent?.({ action: 'account' })) {
        let status = element('mallAccountReturnStatus');
        if (!status) {
          status = document.createElement('p');
          status.id = 'mallAccountReturnStatus';
          status.setAttribute('role', 'alert');
          document.querySelector('.mall-header')?.after(status);
        }
        status.textContent = 'The safe account return could not be saved. Keep browsing; sign-in has not started.';
        return;
      }
      window.location.assign(memberPortalUrl());
    }
    if (selfAnchor) {
      selfAnchor.classList.add('open-mall-portal-cta');
      // The existing avatar owns a bubbling panel handler. This public account
      // action uses capture so it reaches the same-host sign-in gate once.
      selfAnchor.addEventListener('click', openPlayAccount, true);
    }

    const plane = element('accountPlane');
    if (plane) {
      for (const selector of ['[data-reddog-identity]', '[data-reddog-foundups]', '[data-reddog-invites]', '[data-reddog-options]']) {
        const section = plane.querySelector(selector);
        if (section) section.hidden = true;
      }
      const greeting = plane.querySelector('[data-reddog-greeting]');
      if (greeting) greeting.textContent = 'Play Mall guide · Sign in for account actions';
      const concierge = plane.querySelector('[data-reddog-concierge]');
      if (concierge && !concierge.querySelector('.open-mall-portal-link')) {
        const portalLink = document.createElement('a');
        portalLink.className = 'm2j-account open-mall-portal-link';
        portalLink.href = memberPortalUrl();
        portalLink.textContent = 'Open Play account \u2197';
        portalLink.addEventListener('click', openPlayAccount);
        concierge.prepend(portalLink);
      }
    }

    try {
      const catalogPager = await window.mallDiscoveryPager.openCatalog();
      const catalog = catalogPager.items;
      window.mallTileField?.initialize(catalog, { entityPortraitField: true, catalogPager });
      window.mallStateRestore?.restore?.();

      const creator = new URLSearchParams(window.location.search).getAll('creator');
      if (creator.length === 1 && creator[0] === 'move2japan') {
        await window.mallTileField?.openEntityById?.('move2japan');
      }

      window.mallPlanesSync = function () {};
      window.mallPlanes?.setCatalog(window.mallTileField?.getLoadedCatalog?.() || catalog);
      window.mallStateRestore?.bindAutoSave?.();

      element('overlayScrim')?.addEventListener('click', () => {
        window.redDog?.close?.();
        window.mallPlanes?.closeView?.();
      });
      document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        if (window.mallTileField?.isExpanded?.()) {
          window.mallTileField.collapseFoundUp();
          return;
        }
        window.redDog?.close?.();
        window.mallPlanes?.closeView?.();
      });
    } catch (error) {
      console.warn('[Mall] Open Mall catalog unavailable:', error);
      field.textContent = 'Play FoundUps Mall is unavailable right now. Reload the page to try again.';
    }
  }

  async function mount(scope) {
    const memberCards = scope === 'voteballots';
    if (scope === 'mall') {
      await mountOpenMall();
      return;
    }
    const element = (id) => document.getElementById(id);
    const field = element('mallTileField');
    document.documentElement.dataset.mallVideoScope = scope;
    element('gestureHints').remove();
    element('loadingState').style.display = 'none';
    element('memberArea').style.display = 'block';
    field.setAttribute('aria-label', memberCards ? 'Congressional member cards' : 'Shorts');
    const home = document.querySelector('.mall-header .mall-brand-minimal');
    home.href = isOpenMallHost(window.location) ? '/member/' : OPEN_MALL_ORIGIN + '/';
    home.setAttribute('aria-label', 'Return to Play FoundUps Mall');
    home.addEventListener('click', function () { window.mallStateRestore.save(); });
    if (memberCards) {
      const image = home.querySelector('img');
      image.src = '/logo-dog.png';
      image.width = image.height = 32;
      image.alt = '';
    }

    try {
      const response = await fetch(memberCards ? '/member/vote/congressional-cards.json' : '/member/mall-public-video-catalog.json', { cache: 'no-store', credentials: 'omit' });
      if (!response.ok) throw new Error('Public video catalog unavailable');
      const projection = (await response.json())[scope];
      if (projection?.lane?.foundup_id !== scope || !projection.lane.videos?.length) {
        throw new Error('Public video projection missing');
      }
      if (memberCards && !projection.lane.videos.every(video => window.mallVideoPlayer.isMemberCardVideo(video))) {
        throw new Error('Public member-card media is invalid');
      }
      const voiceResource = new URL(projection.voice_resource_url);
      if (voiceResource.protocol !== 'https:' || voiceResource.username || voiceResource.password) {
        throw new Error('Invalid civic resource destination');
      }

      document.title = scope === 'hpc' ? hpcTitle : projection.lane.title;
      const title = element('videoScopeTitle');
      title.textContent = scope === 'hpc' ? hpcTitle : projection.lane.title;
      const identity = element('videoScopeIdentity');
      const topic = element('videoScopeTopic');
      identity.textContent = projection.identity;
      topic.textContent = projection.topic;
      identity.hidden = topic.hidden = memberCards;
      const topicLine = document.createElement('div');
      topicLine.className = 'mall-video-scope-topic-line';
      if (scope !== 'hpc') topicLine.innerHTML = buildLabel;
      topicLine.prepend(topic);
      identity.after(topicLine);
      if (scope === 'hpc') {
        // Reuse the existing left identity and navigation target. The build stays
        // in normal flow above the full banner, inside the measured header.
        const banner = identity.parentElement;
        banner.classList.add('mall-hpc-banner');
        for (const metadata of [title, identity, topicLine]) {
          metadata.classList.add('mall-hpc-banner-metadata');
        }
        banner.insertAdjacentHTML('afterbegin', buildLabel);
        const image = home.querySelector('img');
        image.src = '/member/hpc-banner.webp';
        image.width = 1280;
        image.height = 353;
        image.classList.replace('mall-brand-logo-sm', 'mall-hpc-banner-image');
        home.classList.add('mall-hpc-banner-link');
        home.href = 'https://hasan4speaker.com/';
        home.target = '_blank';
        home.rel = 'noopener noreferrer';
        home.setAttribute('aria-label', 'Hasan for Speaker campaign');
        home.title = 'Hasan for Speaker campaign';
        const mallReturn = document.createElement('a');
        mallReturn.className = 'mall-hpc-mall-return';
        mallReturn.href = isOpenMallHost(window.location) ? '/member/' : OPEN_MALL_ORIGIN + '/';
        mallReturn.setAttribute('aria-label', 'Return to Play FoundUps Mall');
        mallReturn.innerHTML = '<img src="/logo-dog.png" alt="" width="30" height="30">';
        mallReturn.addEventListener('click', () => window.mallStateRestore?.save());
        const bannerArt = document.createElement('div');
        bannerArt.className = 'mall-hpc-banner-art';
        const brandCluster = home.closest('.mall-brand-cluster');
        bannerArt.append(home, mallReturn);
        banner.append(bannerArt);
        // The ordinary Mall keeps its logo and LinkedIn cluster. HPC uses the
        // moved banner link, so retire the now-hidden sibling badge and wrapper.
        brandCluster?.remove();
      }
      element('videoScopeCredit').textContent = projection.credit + ' Shorts · Commentary and satire';
      field.setAttribute('aria-describedby', 'videoScopeCredit');
      element('videoScopeDisclosureText').textContent = projection.disclosure;
      const disclosure = element('videoScopeDisclosure');
      if (memberCards) {
        const credit = document.createElement('p');
        credit.textContent = projection.credit;
        const guide = document.createElement('a');
        guide.href = 'https://vote.foundups.com/guide';
        guide.textContent = 'Vote guide';
        disclosure.append(credit, guide);
      }
      if (scope === 'hpc') {
        const campaign = document.createElement('a');
        campaign.href = 'https://hasan4speaker.com/';
        campaign.target = '_blank';
        campaign.rel = 'noopener noreferrer';
        campaign.textContent = 'Hasan for Speaker campaign';
        disclosure.append(campaign);
      }
      const info = element('videoScopeInfo');
      info.addEventListener('click', () => disclosure.showModal());

      const voice = element('videoScopeVoice');
      voice.href = voiceResource.href;
      if (memberCards) voice.textContent = 'Voice your opinion';
      voice.addEventListener('click', () => window.mallStateRestore.save());
      const actions = document.createElement('nav');
      actions.id = 'videoScopeActions';
      actions.setAttribute('aria-label', 'Video collection actions');
      actions.append(voice);
      element('redDogAnchor').prepend(actions);

      const header = element('videoScopeHeader');
      header.hidden = false;
      if (memberCards) {
        const resources = document.createElement('nav');
        resources.className = 'mall-member-card-resources';
        resources.setAttribute('aria-label', 'Vote resources');
        const dispatch = document.createElement('a');
        dispatch.href = 'https://vote.foundups.com/dispatch';
        dispatch.tabIndex = 0;
        dispatch.textContent = 'Dispatch';
        dispatch.addEventListener('click', () => window.mallStateRestore.save());
        resources.append(dispatch);
        const hpcLink = document.createElement('a');
        hpcLink.className = 'mall-vote-hpc-link';
        hpcLink.href = 'https://hpc.foundups.com/';
        hpcLink.setAttribute('aria-label', 'HPC — open Hasan Piker Coalition');
        hpcLink.addEventListener('click', () => window.mallStateRestore.save());
        const hpcBanner = document.createElement('img');
        hpcBanner.src = '/member/hpc-banner.webp';
        hpcBanner.width = 1280;
        hpcBanner.height = 353;
        hpcBanner.alt = 'HPC';
        hpcLink.append(hpcBanner);
        header.append(resources, hpcLink);
      }
      window.mallStateRestore.selectVideoScope(scope);
      window.mallTileField.initialize([projection.lane], { fixedVideoField: true });
      window.mallStateRestore.restore();
      window.mallStateRestore.bindAutoSave();

      const dock = createPhoneDock(actions, scope, disclosure, showScopedGrid, memberCards ? 'Search VOTE cards' : 'Search HPC Mall');
      const desktop = window.matchMedia('(min-width: 900px) and (hover: hover) and (pointer: fine)');
      function applyPresentation() {
        const theater = desktop.matches && !memberCards && window.mallStateRestore.getScopedPresentation() !== 'grid';
        document.documentElement.dataset.mallVideoLayout = theater ? 'theater' : desktop.matches ? 'grid' : 'phone';
        info.hidden = !theater;
        (theater ? actions : header).append(voice);
        window.mallTileField.setScopedTheater(theater);
        dock.show(!theater);
      }
      function showScopedGrid() {
        window.mallStateRestore.save();
        window.mallVideoPlayer.returnToMall?.();
        window.mallStateRestore.setScopedPresentation('grid');
        applyPresentation();
        window.mallStateRestore.save();
      }
      desktop.addEventListener('change', applyPresentation);
      // The shared state owner restores the tab's browse position before startup.
      requestAnimationFrame(applyPresentation);
    } catch (error) {
      console.warn('[Mall] Public video projection unavailable:', error);
      field.textContent = 'This video collection is unavailable. Reload the page to try again.';
    }
  }

  window.mallVideoProjection = {
    mallBuild,
    hostScope,
    isOpenMallHost,
    isPublicBrowseOnly,
    isAdmissionRequest,
    shouldLoadMemberAuth,
    publicEntryPath,
    dedicatedLandingPath,
    plannedApexLandingUrl,
    authCompletionPath,
    signInUrl,
    showContributionReview,
    resolve,
    resolveMember,
    resolveMemberEntry,
    memberPath,
    memberEntryPath,
    memberPortalUrl,
    canonicalEntryId,
    discoveryPath,
    mount,
    createMemberDock,
    cameraDestination,
    getScopedPhoneDock(scope, options) {
      const sharedDesktopDock = options?.includeDesktop === true;
      return (isPhoneDockLayout() || sharedDesktopDock) && scopedPhoneDock && (scopedPhoneDock.scope === null || scopedPhoneDock.scope === scope)
        ? scopedPhoneDock.dock : null;
    },
    isPhoneDockLayout,
    mountMemberDock,
    openScopedRedDog
  };
})();
