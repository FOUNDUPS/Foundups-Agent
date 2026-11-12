(function () {
  'use strict';

  const reference = document.getElementById('hpc-probe-embed');
  if (!reference && window.mallVideoProjection?.resolve(location) !== 'hpc') return;

  const firstShort = 'iJuguXpbRR4';
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const platform = navigator.userAgent.match(/iPhone OS [0-9_]+/)?.[0] || 'iPhone OS not reported';
  const trace = [];
  let started = performance.now();
  let activeId = null;
  let firstTime = null;
  let advanced = 0;
  let lastFrame = null;
  let observedCaches = [];
  let referencePlayer;
  let referenceState = null;

  window.caches?.keys().then((keys) => {
    observedCaches = keys.filter((key) => /^pfmall-member-v[0-9]+$/.test(key));
  }).catch(() => {});

  function record(snapshot) {
    if (!snapshot || !/^[A-Za-z0-9_-]{11}$/.test(snapshot.videoId)) return;
    if (snapshot.videoId !== activeId || snapshot.state === 'loading' && trace.at(-1)?.state !== 'loading') {
      activeId = snapshot.videoId;
      started = performance.now();
      trace.length = 0;
      firstTime = null;
      advanced = 0;
      lastFrame = null;
    }
    const frame = document.querySelector(reference ? '#hpc-probe-embed iframe' : '.video-player-stage iframe');
    const rect = frame?.getBoundingClientRect();
    if (rect?.width && rect.height) lastFrame = [Math.round(rect.width), Math.round(rect.height)];
    const { state, code, providerState, positionSeconds } = snapshot;
    if (state === 'playing' && Number.isFinite(positionSeconds)) {
      firstTime ??= positionSeconds;
      advanced = Math.max(advanced, positionSeconds - firstTime);
    }
    const previous = trace.at(-1);
    if (previous?.state === state && previous?.code === code && previous?.providerState === providerState) return;
    trace.push({ state, code, providerState, elapsedMs: Math.round(performance.now() - started),
      activation: (state === 'ready' || state === 'starting') ? navigator.userActivation?.isActive : undefined });
    if (trace.length > 24) trace.shift();
  }

  function receipt() {
    const events = trace.map((entry) => {
      const details = [entry.code === undefined ? '' : 'code ' + entry.code,
        entry.providerState === undefined ? '' : 'YT state ' + entry.providerState,
        entry.activation === undefined ? '' : 'activation ' + entry.activation].filter(Boolean);
      return entry.elapsedMs + ' ms ' + entry.state + (details.length ? ' (' + details.join(', ') + ')' : '');
    });
    return [
      'HPC iPhone playback test',
      'Path: ' + (reference ? 'Official YouTube embed' : 'Mall player'),
      'Mode: ' + (standalone ? 'Home Screen web app' : 'Browser') + ' · ' + platform,
      'Host: ' + location.host,
      'Mall caches seen: ' + (observedCaches.join(', ') || 'none'),
      'Video: ' + (activeId || 'tap a video first'),
      'Iframe: ' + (lastFrame ? lastFrame.join(' × ') + ' CSS px' : 'not observed'),
      'Advancing media time: ' + advanced.toFixed(2) + ' s',
      'Events: ' + (events.join(' → ') || 'none')
    ].join('\n');
  }

  function addReceiptControls(parent) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Copy playback result';
    const result = document.createElement('textarea');
    result.readOnly = true;
    result.hidden = true;
    result.rows = 5;
    result.style.cssText = 'width:100%;box-sizing:border-box;font:inherit';
    result.setAttribute('aria-label', 'Playback test result');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    button.addEventListener('click', async () => {
      result.value = receipt();
      result.hidden = false;
      try {
        await navigator.clipboard.writeText(result.value);
        status.textContent = 'Copied. Paste the result into the conversation.';
      } catch {
        result.focus();
        result.select();
        status.textContent = 'Copy the selected result and paste it into the conversation.';
      }
    });
    parent.append(button, status, result);
  }

  function mountMallTools() {
    const menu = document.getElementById('videoScopeOptions');
    if (!menu) return false;
    const tools = document.createElement('section');
    addReceiptControls(tools);
    const link = document.createElement('a');
    link.href = '/member/playback-probe/reference.html';
    link.textContent = 'Compare with the official YouTube embed';
    link.style.cssText = 'display:block;padding:0.75rem 0;color:inherit';
    link.addEventListener('click', () => window.mallStateRestore?.save());
    tools.append(link);
    menu.querySelector('form[method="dialog"]').before(tools);
    return true;
  }

  function mountReference() {
    const iframe = document.createElement('iframe');
    const url = new URL('https://www.youtube.com/embed/' + firstShort);
    url.search = new URLSearchParams({ enablejsapi: '1', playsinline: '1', controls: '1', origin: location.origin });
    iframe.src = url.href;
    iframe.title = 'First Move2Japan Short';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    reference.append(iframe);
    addReceiptControls(document.getElementById('hpc-probe-controls'));

    const update = (state, fields) => {
      referenceState = { videoId: firstShort, state, ...fields };
      record(referenceState);
    };
    update('loading');
    const timer = setTimeout(() => update('api-timeout'), 12000);
    const states = { '-1': 'unstarted', 0: 'ended', 1: 'playing', 2: 'paused', 3: 'buffering', 5: 'cued' };
    window.onYouTubeIframeAPIReady = () => {
      referencePlayer = new window.YT.Player(iframe, {
        events: {
          onReady() { clearTimeout(timer); update('ready'); },
          onStateChange(event) { update(states[event.data] || 'provider-state', { providerState: event.data }); },
          onError(event) { clearTimeout(timer); update('provider-error', { code: event.data }); },
          onAutoplayBlocked() { update('autoplay-blocked'); }
        }
      });
    };
    const script = document.createElement('script');
    script.src = 'https://www.youtube.com/iframe_api';
    script.onerror = () => { clearTimeout(timer); update('api-load-error'); };
    document.head.append(script);
  }

  if (reference) {
    mountReference();
  } else {
    window.addEventListener('mallVideoPlayback', (event) => record(event.detail));
    if (!mountMallTools()) {
      const observer = new MutationObserver(() => { if (mountMallTools()) observer.disconnect(); });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }
  setInterval(() => {
    if (document.hidden) return;
    if (reference) {
      if (referenceState) record({ ...referenceState, positionSeconds: referencePlayer?.getCurrentTime?.() });
    } else {
      record(window.mallVideoPlayer?.getPlaybackSnapshot());
    }
  }, 300);
})();
