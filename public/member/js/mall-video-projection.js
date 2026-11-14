(function () {
  'use strict';

  // Only a dedicated host can start a guest projection.
  const dedicatedHosts = new Map([['hpc.foundups.com', 'hpc']]);
  const publicScopes = new Set(dedicatedHosts.values());
  const memberPaths = new Set(['/member', '/member/', '/member/index.html']);

  function hostScope(location) {
    return dedicatedHosts.get(location.hostname) || null;
  }

  function resolve(location) {
    return memberPaths.has(location.pathname) ? hostScope(location) : null;
  }

  // Member boot uses this presentation selection after checking admission.
  function resolveMember(location) {
    if (!memberPaths.has(location.pathname) || hostScope(location)) return null;
    const requested = new URLSearchParams(location.search).getAll('foundup');
    return requested.length === 1 && publicScopes.has(requested[0]) ? requested[0] : null;
  }

  function memberPath(foundupId) {
    return publicScopes.has(foundupId) ? '/member/?foundup=' + foundupId : null;
  }

  function scopedRedDogPath(scope) {
    return publicScopes.has(scope) ? '/f/' + encodeURIComponent(scope) + '#red-dog' : null;
  }

  function openScopedRedDog(scope) {
    const path = scopedRedDogPath(scope);
    if (!path) return;
    window.mallStateRestore?.save();
    window.location.assign(path);
  }

  function discoveryPath(foundupId, pocUrl) {
    for (const [host, scope] of dedicatedHosts) {
      if (foundupId !== scope) continue;
      const url = 'https://' + host + '/';
      // Recognize a cached discovery card from before the host split.
      if (pocUrl === url || pocUrl === 'https://foundups.com' + memberPath(scope)) return url;
    }
    return null;
  }

  // Select install metadata in the head, before the public catalog loads.
  const hpcTitle = 'Hasan Piker Coalition';
  const hpcPortrait = '/member/hpc-icon-192.png';
  const playLocation = window.location;
  if (playLocation?.hostname === 'play.foundups.com' && playLocation.pathname === '/' &&
      !new URLSearchParams(playLocation.search).has('signin')) {
    playLocation.replace('/member/' + playLocation.search + playLocation.hash);
  }
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
    trigger.addEventListener('click', open);
    if (!window.gestureZone) return;
    window.gestureZone(trigger, {
      onSwipe(direction) {
        if (direction !== 'up') return;
        open();
      }
    });
    // Keep the parent Red Dog mode sheet out of the same swipe.
    trigger.addEventListener('touchstart', (event) => event.stopPropagation(), { passive: true });
    trigger.addEventListener('touchend', (event) => event.stopPropagation(), { passive: true });
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
    trigger.title = 'Hold to dictate a search';
    trigger.addEventListener('pointerdown', (event) => {
      if (!event.isPrimary || event.button !== 0) return;
      held = false;
      pressed = true;
      timer = setTimeout(() => {
        held = true;
        dictation.start(true);
      }, 500);
    });
    trigger.addEventListener('pointerup', () => {
      if (!pressed) return;
      pressed = false;
      clearTimeout(timer);
      if (held) dictation.stop();
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
    const element = document.createElement('div');
    element.className = 'mall-member-search-dock';
    const optionsLabel = redDogHref ? 'More options' : 'Search options';
    const dogLogo = '<img src="/logo-dog.png" alt="" width="30" height="30">';
    const dogAction = redDogHref
      ? `<a class="mall-search-dog" aria-label="Red Dog">${dogLogo}</a>`
      : openRedDog ? `<button class="mall-search-dog" type="button" aria-label="Open Red Dog">${dogLogo}</button>` : '';
    element.innerHTML = `
      <form class="mall-member-search-bar" role="search">
        <p role="status"></p>
        <button class="mall-search-plus" type="button" aria-haspopup="dialog">+</button>
        <textarea rows="1" maxlength="300" inputmode="search" enterkeyhint="search"></textarea>
        <button class="mall-search-submit" type="submit" aria-label="Search" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4"/></svg>
        </button>
        <button class="mall-search-mic" type="button" aria-label="Dictate search" aria-pressed="false">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6"/>
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
        <a class="mall-search-option" href="https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/" target="_blank" rel="noopener noreferrer">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h4l2-3h6l2 3h4v13H3z"/><circle cx="12" cy="13" r="3.5"/></svg>AutoPost camera and photos
        </a>
        <label class="mall-search-option">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3"/></svg>
          <span>Browser AI <select aria-label="Browser AI" disabled><option>No device model connected</option></select></span>
        </label>
        <form method="dialog"><button type="submit">Close</button></form>
      </dialog>`;
    const form = element.querySelector('.mall-member-search-bar');
    const input = form.querySelector('textarea');
    const submitButton = form.querySelector('.mall-search-submit');
    const dialog = element.querySelector('dialog');
    const options = form.querySelector('.mall-search-plus');
    options.setAttribute('aria-label', optionsLabel);
    dialog.setAttribute('aria-label', optionsLabel);
    form.setAttribute('aria-label', label);
    input.setAttribute('aria-label', label);
    input.placeholder = label;
    const dictation = bindDictation(form, input, form.querySelector('.mall-search-mic'),
      form.querySelector('.mall-search-stop'), form.querySelector('[role="status"]'));

    function fitInput() {
      if (element.hidden) return;
      submitButton.hidden = !input.value.trim();
      form.removeAttribute('data-expanded');
      input.style.height = '';
      if (input.scrollHeight > input.clientHeight) {
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
    function showOptions() {
      if (dialog.open || element.hidden) return;
      dictation.cancel();
      options.focus({ preventScroll: true });
      dialog.showModal();
      placeOptions();
    }
    window.addEventListener('resize', () => { fitInput(); placeOptions(); });
    window.visualViewport?.addEventListener('resize', placeOptions);
    window.visualViewport?.addEventListener('scroll', placeOptions);
    bindOptions(options, showOptions);
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
    const autoPost = dialog.querySelector('a');
    autoPost.addEventListener('click', () => dialog.close());
    const dog = form.querySelector('.mall-search-dog');
    const cancelHold = dog && bindDictationHold(dog, dictation);
    if (redDogHref) {
      dog.href = redDogHref;
      dog.addEventListener('click', () => window.mallStateRestore.save());
    } else if (openRedDog) {
      dog.addEventListener('click', openRedDog);
    }
    return {
      element, input, dialog, dictation, fitInput,
      setScoped(scoped) { autoPost.hidden = scoped; },
      setValue(value) { input.value = value; fitInput(); },
      hide() { cancelHold?.(); dialog.close(); dictation.cancel(); element.hidden = true; }
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
      if (!dock.input.value && field.getFieldScope()?.type === 'query') {
        field.searchCatalog('');
        window.mallStateRestore?.save();
      }
    });
    anchor.prepend(dock.element);
    dock.setValue(field.getFieldScope()?.query || '');
    window.redDog.bindSearchDictation?.({ ...dock.dictation, start: () => dock.dictation.start(true) });
    window.visualViewport?.addEventListener('resize', () => {
      const viewport = window.visualViewport;
      const keyboard = dock.element.contains(document.activeElement) && viewport.scale === 1
        ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
      anchor.style.setProperty('--member-dock-keyboard', keyboard + 'px');
    });
    dock.input.addEventListener('blur', () => anchor.style.removeProperty('--member-dock-keyboard'));
  }

  function createPhoneDock(actions, scope, disclosure) {
    const field = window.mallTileField;
    const dock = createMemberDock('Search videos', search, null, scopedRedDogPath(scope));
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
    input.addEventListener('input', () => { if (!input.value && field.getScopedPhoneQuery()) search(''); });
    const home = dialog.querySelector('[data-action="home"]');
    const about = dialog.querySelector('[data-action="about"]');
    home.hidden = about.hidden = false;
    home.addEventListener('click', () => { dialog.close(); search(''); });
    about.addEventListener('click', () => { dialog.close(); disclosure.showModal(); });
    return {
      show(visible) {
        if (!visible) return dock.hide();
        element.hidden = false;
        dock.setValue(field.getScopedPhoneQuery());
      }
    };
  }

  async function mount(scope) {
    const element = (id) => document.getElementById(id);
    const field = element('mallTileField');
    document.documentElement.dataset.mallVideoScope = scope;
    element('gestureHints').remove();
    element('loadingState').style.display = 'none';
    element('memberArea').style.display = 'block';
    field.setAttribute('aria-label', 'Shorts');
    const home = document.querySelector('.mall-header .mall-brand-minimal');
    home.href = 'https://foundups.com/member/';
    if (scope === 'hpc') home.querySelector('img').src = hpcPortrait;
    home.setAttribute('aria-label', 'Return to Play FoundUps Mall');
    home.addEventListener('click', function () { window.mallStateRestore.save(); });

    try {
      const response = await fetch('/member/mall-public-video-catalog.json', { cache: 'no-store', credentials: 'omit' });
      if (!response.ok) throw new Error('Public video catalog unavailable');
      const projection = (await response.json())[scope];
      if (projection?.lane?.foundup_id !== scope || !projection.lane.videos?.length) {
        throw new Error('Public video projection missing');
      }
      const voiceResource = new URL(projection.voice_resource_url);
      if (voiceResource.protocol !== 'https:' || voiceResource.username || voiceResource.password) {
        throw new Error('Invalid civic resource destination');
      }

      document.title = projection.lane.title;
      element('videoScopeTitle').textContent = projection.lane.title;
      const identity = element('videoScopeIdentity');
      const topic = element('videoScopeTopic');
      identity.textContent = projection.identity;
      topic.textContent = projection.topic;
      identity.after(topic);
      element('videoScopeCredit').textContent = projection.credit + ' Shorts · Commentary and satire';
      field.setAttribute('aria-describedby', 'videoScopeCredit');
      element('videoScopeDisclosureText').textContent = projection.disclosure;
      const disclosure = element('videoScopeDisclosure');
      const info = element('videoScopeInfo');
      info.addEventListener('click', () => disclosure.showModal());

      const voice = element('videoScopeVoice');
      voice.href = voiceResource.href;
      voice.addEventListener('click', () => window.mallStateRestore.save());
      const actions = document.createElement('nav');
      actions.id = 'videoScopeActions';
      actions.setAttribute('aria-label', 'Video collection actions');
      actions.append(voice);
      element('redDogAnchor').prepend(actions);

      const header = element('videoScopeHeader');
      header.hidden = false;
      window.mallStateRestore.selectVideoScope(scope);
      window.mallTileField.initialize([projection.lane], { fixedVideoField: true });
      window.mallStateRestore.restore();
      window.mallStateRestore.bindAutoSave();

      const dock = createPhoneDock(actions, scope, disclosure);
      const desktop = window.matchMedia('(min-width: 900px) and (hover: hover) and (pointer: fine)');
      const applyPresentation = () => {
        const theater = desktop.matches;
        document.documentElement.dataset.mallVideoLayout = theater ? 'theater' : 'phone';
        info.hidden = !theater;
        (theater ? actions : header).append(voice);
        window.mallTileField.setScopedTheater(theater);
        dock.show(!theater);
      };
      desktop.addEventListener('change', applyPresentation);
      // The shared state owner restores the tab's browse position before startup.
      requestAnimationFrame(applyPresentation);
    } catch (error) {
      console.warn('[Mall] Public video projection unavailable:', error);
      field.textContent = 'This video collection is unavailable. Reload the page to try again.';
    }
  }

  window.mallVideoProjection = { hostScope, resolve, resolveMember, memberPath, discoveryPath, mount, createMemberDock, mountMemberDock, openScopedRedDog };
})();
