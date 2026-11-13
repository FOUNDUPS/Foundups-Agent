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

  function bindDictation(button, input, status) {
    const hint = 'Use the microphone on your keyboard to dictate.';
    let attempt = 0;
    let active = null;
    let starting = false;
    let timer;
    function idle() {
      clearTimeout(timer);
      active = null;
      starting = false;
      button.removeAttribute('data-dictating');
      button.setAttribute('aria-label', 'Dictate search');
    }
    function cancel() {
      attempt += 1;
      const recognition = active;
      idle();
      recognition?.abort();
      status.textContent = '';
    }
    function stop() {
      if (!active) {
        if (starting) cancel();
        return;
      }
      try { active.stop(); } catch { cancel(); }
    }
    window.addEventListener('pagehide', cancel);
    document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
    input.addEventListener('input', cancel);
    input.addEventListener('blur', (event) => { if (event.relatedTarget !== button) cancel(); });
    function retainInputFocus(event) { if (active || starting) event.preventDefault(); }
    button.addEventListener('pointerdown', retainInputFocus);
    button.addEventListener('mousedown', retainInputFocus);
    async function start() {
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
      button.setAttribute('data-dictating', '');
      button.setAttribute('aria-label', 'Stop dictation');
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
        recognition.lang = lang;
        recognition.processLocally = true;
        recognition.onstart = () => {
          if (request === attempt) status.textContent = 'Listening for search…';
        };
        recognition.onresult = (event) => {
          if (request !== attempt) return;
          input.value = event.results[0][0].transcript.trim().slice(0, input.maxLength);
          status.textContent = 'Dictation added. Press Search.';
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };
        recognition.onerror = () => { if (request === attempt) status.textContent = hint; };
        recognition.onend = () => {
          if (request !== attempt) return;
          idle();
          if (status.textContent !== 'Dictation added. Press Search.') status.textContent = hint;
        };
        active = recognition;
        status.textContent = 'Starting dictation…';
        recognition.start();
      } catch {
        if (request === attempt) {
          idle();
          status.textContent = hint;
        }
      }
    }
    button.addEventListener('click', () => { if (active || starting) stop(); else start(); });
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
        dictation.start();
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

  function createMemberDock(label, submit, openRedDog) {
    const element = document.createElement('div');
    element.className = 'mall-member-search-dock';
    element.innerHTML = [
      '<div class="mall-member-search-bar">',
      '<button type="button" aria-label="Search options" aria-haspopup="dialog">+</button>',
      '<form role="search"><input type="search" maxlength="300" enterkeyhint="search">',
      '<button type="submit" aria-label="Search" hidden></button>',
      '<button type="button" aria-label="Dictate search"><svg viewBox="0 0 24 24" aria-hidden="true">',
      '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6"/></svg>',
      '<svg class="mall-dictation-stop" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></button></form>',
      openRedDog ? '<button type="button" aria-label="Open Red Dog"><img src="/logo-dog.png" alt="" width="30" height="30"></button>' : '',
      '</div><p role="status"></p>',
      '<dialog class="mall-member-search-options" aria-label="Search options">',
      '<a href="https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/" target="_blank" rel="noopener noreferrer">AutoPost camera and photos</a>',
      '<label>Browser AI <select disabled><option>No device model connected</option></select></label>',
      '<form method="dialog"><button type="submit">Close</button></form></dialog>'
    ].join('');
    const bar = element.querySelector('.mall-member-search-bar');
    const form = bar.querySelector('form');
    const input = form.querySelector('input');
    const status = element.querySelector('[role="status"]');
    const dialog = element.querySelector('dialog');
    const options = bar.firstElementChild;
    form.setAttribute('aria-label', label);
    input.setAttribute('aria-label', label);
    input.placeholder = label;
    const dictation = bindDictation(form.querySelector('[aria-label="Dictate search"]'), input, status);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      dictation.cancel();
      submit(input.value.trim());
    });
    function showOptions() {
      if (dialog.open || element.hidden) return;
      dictation.cancel();
      const rect = options.getBoundingClientRect();
      dialog.style.insetInlineStart = Math.max(16, Math.min(rect.left, window.innerWidth - 288)) + 'px';
      dialog.style.insetBlockEnd = window.innerHeight - rect.top + 8 + 'px';
      dialog.showModal();
    }
    bindOptions(options, showOptions);
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      event.stopPropagation();
      dialog.close();
    });
    const autoPost = dialog.querySelector('a');
    autoPost.addEventListener('click', () => dialog.close());
    let cancelHold;
    if (openRedDog) {
      cancelHold = bindDictationHold(bar.lastElementChild, dictation);
      bar.lastElementChild.addEventListener('click', openRedDog);
    }
    return {
      element, input, dialog, dictation,
      setScoped(scoped) { autoPost.hidden = scoped; },
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
    dock.input.value = field.getFieldScope()?.query || '';
    dock.input.addEventListener('input', () => {
      if (!dock.input.value && field.getFieldScope()?.type === 'query') {
        field.searchCatalog('');
        window.mallStateRestore?.save();
      }
    });
    anchor.prepend(dock.element);
    window.redDog.bindSearchDictation?.(dock.dictation);
    dock.dialog.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') event.stopPropagation();
    });
    window.visualViewport?.addEventListener('resize', () => {
      const viewport = window.visualViewport;
      const keyboard = dock.element.contains(document.activeElement) && viewport.scale === 1
        ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
      anchor.style.setProperty('--member-dock-keyboard', keyboard + 'px');
    });
    dock.input.addEventListener('blur', () => anchor.style.removeProperty('--member-dock-keyboard'));
  }

  function createPhoneDock(actions, scope, disclosure) {
    const dock = document.createElement('div');
    dock.id = 'videoScopePhoneDock';
    dock.hidden = true;
    dock.innerHTML = [
      '<button type="button" aria-label="More options" aria-haspopup="dialog" aria-controls="videoScopeOptions">+</button>',
      '<form role="search" aria-label="Search this collection">',
      '<input type="search" aria-label="Search videos" placeholder="Search videos" maxlength="300" enterkeyhint="search">',
      '<button type="button" aria-label="Dictate search"><svg viewBox="0 0 24 24" aria-hidden="true">',
      '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6"/></svg>',
      '<svg class="mall-dictation-stop" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></button>',
      '</form>',
      '<a aria-label="Red Dog"><img src="/logo-dog.png" alt="" width="32" height="32"></a>',
      '<p class="video-scope-dictation-status" role="status"></p>',
      '<dialog id="videoScopeOptions" aria-labelledby="videoScopeOptionsTitle">',
      '<h2 id="videoScopeOptionsTitle">More options</h2>',
      '<button type="button" data-action="home">Home</button>',
      '<button type="button" data-action="about">About this FoundUp</button>',
      '<label>Browser AI <select disabled><option>No device model connected</option></select></label>',
      '<form method="dialog"><button type="submit">Close</button></form></dialog>'
    ].join('');
    actions.append(dock);
    const field = window.mallTileField;
    const menu = dock.querySelector('dialog');
    const form = dock.querySelector('[role="search"]');
    const input = form.querySelector('input');
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
    const dog = dock.querySelector('a');
    dog.href = scopedRedDogPath(scope);
    dog.addEventListener('click', () => window.mallStateRestore.save());
    const dictation = bindDictation(form.querySelector('button'), input, dock.querySelector('[role="status"]'));
    const cancelHold = bindDictationHold(dog, dictation);

    function search(query) {
      field.setScopedPhoneQuery(query);
      input.value = field.getScopedPhoneQuery();
      window.mallStateRestore.save();
    }
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      dictation.cancel();
      search(input.value);
    });
    input.addEventListener('input', () => { if (!input.value && field.getScopedPhoneQuery()) search(''); });
    const options = dock.querySelector('[aria-haspopup="dialog"]');
    function showOptions() {
      if (menu.open || dock.hidden) return;
      dictation.cancel();
      menu.showModal();
    }
    bindOptions(options, showOptions);
    menu.querySelector('[data-action="home"]').addEventListener('click', () => { menu.close(); search(''); });
    menu.querySelector('[data-action="about"]').addEventListener('click', () => { menu.close(); disclosure.showModal(); });
    return {
      show(visible) {
        if (!visible) { cancelHold(); menu.close(); dictation.cancel(); }
        dock.hidden = !visible;
        if (visible) input.value = field.getScopedPhoneQuery();
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
