(function () {
  'use strict';

  // Public presentation routes. Membership and tenant capabilities are checked elsewhere.
  const dedicatedHosts = new Map([['hpc.foundups.com', 'hpc']]);
  const publicScopes = new Set(dedicatedHosts.values());
  const memberPaths = new Set(['/member', '/member/', '/member/index.html']);

  function hostScope(location) {
    return dedicatedHosts.get(location.hostname) || null;
  }

  function resolve(location) {
    if (!memberPaths.has(location.pathname)) return null;
    const requested = new URLSearchParams(location.search).getAll('foundup');
    return hostScope(location) ||
      (requested.length === 1 && publicScopes.has(requested[0]) ? requested[0] : null);
  }

  function discoveryPath(foundupId, pocUrl) {
    if (!publicScopes.has(foundupId)) return null;
    const path = '/member/?foundup=' + foundupId;
    return pocUrl === 'https://foundups.com' + path ? path : null;
  }

  // Select install metadata in the head, before the public catalog loads.
  const hpcTitle = 'Hasan Piker Coalition';
  const hpcPortrait = '/member/hpc-icon-192.png';
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
    function cancel() {
      attempt += 1;
      active?.abort();
      active = null;
      status.textContent = '';
    }
    window.addEventListener('pagehide', cancel);
    document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
    input.addEventListener('input', cancel);
    input.addEventListener('blur', cancel);
    button.addEventListener('click', async () => {
      cancel();
      input.focus(); // Keep iOS keyboard dictation reachable on the original tap.
      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!Recognition?.available || !('processLocally' in Recognition.prototype)) {
        status.textContent = hint;
        return;
      }
      const request = attempt;
      const lang = navigator.language || 'en-US';
      try {
        const availability = await Recognition.available({ langs: [lang], processLocally: true });
        if (request !== attempt || document.hidden) return;
        if (availability !== 'available') {
          status.textContent = hint;
          return;
        }
        const recognition = new Recognition();
        recognition.lang = lang;
        recognition.processLocally = true;
        recognition.onresult = (event) => {
          if (request !== attempt) return;
          input.value = event.results[0][0].transcript.trim().slice(0, input.maxLength);
          status.textContent = 'Dictation added. Press Search.';
        };
        recognition.onerror = () => { if (request === attempt) status.textContent = hint; };
        recognition.onend = () => {
          if (active === recognition) active = null;
          if (request === attempt && status.textContent === 'Listening…') status.textContent = hint;
        };
        active = recognition;
        status.textContent = 'Listening…';
        recognition.start();
      } catch {
        if (request === attempt) {
          active = null;
          status.textContent = hint;
        }
      }
    });
    return cancel;
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
      '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6"/></svg></button>',
      '</form>',
      '<a aria-label="Red Dog"><img src="/logo-dog.png" alt="" width="32" height="32"></a>',
      '<p class="video-scope-dictation-status" role="status"></p>',
      '<dialog id="videoScopeOptions" aria-labelledby="videoScopeOptionsTitle">',
      '<h2 id="videoScopeOptionsTitle">More options</h2>',
      '<button type="button" data-action="home">Home</button>',
      '<button type="button" data-action="about">About this FoundUp</button>',
      '<h3>Device models</h3><p>No on-device models are connected.</p>',
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
    dog.href = '/f/' + scope + '#red-dog';
    dog.addEventListener('click', () => window.mallStateRestore.save());
    const cancelDictation = bindDictation(form.querySelector('button'), input, dock.querySelector('[role="status"]'));

    function search(query) {
      field.setScopedPhoneQuery(query);
      input.value = field.getScopedPhoneQuery();
      window.mallStateRestore.save();
    }
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      cancelDictation();
      search(input.value);
    });
    input.addEventListener('input', () => { if (!input.value && field.getScopedPhoneQuery()) search(''); });
    dock.querySelector('[aria-haspopup="dialog"]').addEventListener('click', () => menu.showModal());
    menu.querySelector('[data-action="home"]').addEventListener('click', () => { menu.close(); search(''); });
    menu.querySelector('[data-action="about"]').addEventListener('click', () => { menu.close(); disclosure.showModal(); });
    return {
      show(visible) {
        if (!visible) { menu.close(); cancelDictation(); }
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

  window.mallVideoProjection = { hostScope, resolve, discoveryPath, mount };
})();
