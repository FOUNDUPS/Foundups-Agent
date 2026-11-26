(function () {
  'use strict';

  const reference = document.getElementById('hpc-probe-embed');
  const projectionScope = window.mallVideoProjection?.resolve?.(location) ||
    window.mallVideoProjection?.resolveMember?.(location) || null;
  if (!reference && projectionScope !== 'hpc') return;

  const firstShort = 'iJuguXpbRR4';
  const ADMITTED_HPC_SHORTS = Object.freeze([
    'iJuguXpbRR4',
    'sSzWdw7MNjs',
    'BXCzUOh9Y8M',
    'OTTz58wPi24',
    'fp2BkIS2FNI',
    'DDAfdpJeUP0',
    'Pdz1Q5tHmJQ',
    'urXOSlVgPdk'
  ]);
  // Retained strictly for isolated probe diagnostics; never admitted into public/member catalogs here.
  const DIAGNOSTIC_ONLY_SHORTS = Object.freeze([
    'R7xm4MZ9N4w',
    'TppBUj_7lC0',
    'qNFSBWXhZSY',
    'B0P1Zci5Pxo'
  ]);
  const ADMITTED_SET = new Set(ADMITTED_HPC_SHORTS);
  const DIAGNOSTIC_SET = new Set(DIAGNOSTIC_ONLY_SHORTS);
  const OFFICIAL_HOSTS = Object.freeze({
    youtube: 'https://www.youtube.com',
    nocookie: 'https://www.youtube-nocookie.com'
  });
  const OBSERVED_PROMPTS = Object.freeze([
    ['not-recorded', 'Not recorded'],
    ['normal-player-ui', 'Normal YouTube player'],
    ['login-required-bot-check', 'Sign in / not-a-bot challenge'],
    ['embed-unavailable-or-disabled', 'Unavailable / embed disabled'],
    ['opened-external-youtube', 'Left frame for external YouTube']
  ]);
  const PROMPT_KEYS = new Set(OBSERVED_PROMPTS.map((entry) => entry[0]));
  const PROBE_STORAGE_KEY = 'hpc_playback_probe_selection_v1';
  const DEPLOYMENT_META_URL = '/member/playback-probe/deployment.json';

  function validVideoId(value) {
    return typeof value === 'string' && /^[A-Za-z0-9_-]{11}$/.test(value) &&
      (ADMITTED_SET.has(value) || DIAGNOSTIC_SET.has(value)) ? value : null;
  }

  function validHostKey(value) {
    return value === 'youtube' || value === 'nocookie' ? value : null;
  }

  function validPromptKey(value) {
    return typeof value === 'string' && PROMPT_KEYS.has(value) ? value : 'not-recorded';
  }

  function readStoredSelection() {
    try {
      const raw = window.sessionStorage?.getItem(PROBE_STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return {
        v: validVideoId(parsed?.v),
        host: validHostKey(parsed?.host)
      };
    } catch {
      return {};
    }
  }

  function writeStoredSelection(videoId, hostKey) {
    const cleanVideo = validVideoId(videoId) || firstShort;
    const cleanHost = validHostKey(hostKey) || 'youtube';
    try {
      window.sessionStorage?.setItem(PROBE_STORAGE_KEY, JSON.stringify({
        v: cleanVideo,
        host: cleanHost
      }));
    } catch {
      // Private/storage-restricted modes keep URL-parameter selection without failing.
    }
  }

  const searchParams = new URLSearchParams(location.search);
  const storedSelection = readStoredSelection();
  let selectedVideoId = validVideoId(searchParams.get(reference ? 'v' : 'probe_v')) ||
    validVideoId(searchParams.get('v')) ||
    storedSelection.v ||
    firstShort;
  let selectedHostKey = validHostKey(searchParams.get(reference ? 'host' : 'probe_host')) ||
    validHostKey(searchParams.get('host')) ||
    storedSelection.host ||
    'youtube';
  writeStoredSelection(selectedVideoId, selectedHostKey);

  const standalone = Boolean(
    window.matchMedia?.('(display-mode: standalone)')?.matches ||
    navigator.standalone === true
  );
  const platform = String(navigator['userAgent'] || '').match(/iPhone OS [0-9_]+/)?.[0] || 'iPhone OS not reported';
  const trace = [];
  let started = performance.now();
  let activeId = reference ? selectedVideoId : null;
  let firstTime = null;
  let peakTime = null;
  let advanced = 0;
  let lastFrame = null;
  let lastErrorCode = null;
  let lastLoaderFailure = null;
  let autoplayStatus = 'not-blocked';
  let observedPrompt = 'not-recorded';
  let observedCaches = [];
  let swRegistrationSummary = 'none';
  let deploymentMeta = {
    sourceSha: 'repo-fixture',
    channelId: 'unstaged',
    hostingVersion: 'unverified',
    mallBuild: null
  };
  let referencePlayer;
  let referenceState = null;
  let mallCompareLink = null;
  let mallTargetSummary = null;

  function sanitizeSwScript(scriptUrl) {
    if (!scriptUrl) return null;
    try {
      const parsed = new URL(scriptUrl, location.origin);
      if (parsed.origin !== location.origin) return 'cross-origin-worker';
      return parsed.pathname + parsed.search;
    } catch {
      return 'unparsed-worker';
    }
  }

  function readControllerSummary() {
    const ctrl = navigator.serviceWorker?.controller;
    if (!ctrl) return 'none';
    const path = sanitizeSwScript(ctrl.scriptURL) || 'unknown';
    return path + ' (' + (ctrl.state || 'unknown') + ')';
  }

  function refreshSwRegistration() {
    if (!navigator.serviceWorker?.getRegistration) return;
    navigator.serviceWorker.getRegistration('/member/').then((reg) => {
      if (!reg) {
        swRegistrationSummary = 'none';
        return;
      }
      const parts = [];
      if (reg.active) parts.push('active:' + (sanitizeSwScript(reg.active.scriptURL) || '?'));
      if (reg.waiting) parts.push('waiting:' + (sanitizeSwScript(reg.waiting.scriptURL) || '?'));
      if (reg.installing) parts.push('installing:' + (sanitizeSwScript(reg.installing.scriptURL) || '?'));
      swRegistrationSummary = parts.join(',') || 'registered-idle';
    }).catch(() => {
      swRegistrationSummary = 'unavailable';
    });
  }

  function refreshObservedCaches() {
    window.caches?.keys().then((keys) => {
      observedCaches = keys.filter((key) => /^pfmall-member-v[0-9]+$/.test(key));
    }).catch(() => {});
  }

  function fetchDeploymentMeta() {
    if (typeof window.fetch !== 'function') return;
    window.fetch(DEPLOYMENT_META_URL, { cache: 'no-store', credentials: 'omit' })
      .then((resp) => (resp && resp.ok && !resp.redirected ? resp.json() : null))
      .then((data) => {
        if (!data || typeof data !== 'object') return;
        if (typeof data.source_sha === 'string' && /^[0-9a-f]{7,40}$/i.test(data.source_sha)) {
          deploymentMeta.sourceSha = data.source_sha;
        }
        if (typeof data.channel_id === 'string' && /^[A-Za-z0-9._-]{1,64}$/.test(data.channel_id)) {
          deploymentMeta.channelId = data.channel_id;
        }
        if (typeof data.hosting_version === 'string' && /^[A-Za-z0-9._-]{1,40}$/.test(data.hosting_version)) {
          deploymentMeta.hostingVersion = data.hosting_version;
        }
        if (typeof data.mall_build === 'string' && /^v[0-9]{1,4}$/.test(data.mall_build)) {
          deploymentMeta.mallBuild = data.mall_build;
        }
      })
      .catch(() => {});
  }

  refreshObservedCaches();
  refreshSwRegistration();
  fetchDeploymentMeta();

  function buildReferenceHref(videoId, hostKey) {
    const params = new URLSearchParams({
      v: validVideoId(videoId) || firstShort,
      host: validHostKey(hostKey) || 'youtube'
    });
    return '/member/playback-probe/reference.html?' + params.toString();
  }

  function buildReturnHref(videoId, hostKey) {
    const params = new URLSearchParams({
      foundup: 'hpc',
      probe_v: validVideoId(videoId) || firstShort,
      probe_host: validHostKey(hostKey) || 'youtube'
    });
    return '/member/?' + params.toString();
  }

  function syncMallSelectionUi() {
    writeStoredSelection(selectedVideoId, selectedHostKey);
    if (mallCompareLink) {
      mallCompareLink.href = buildReferenceHref(selectedVideoId, selectedHostKey);
    }
    if (mallTargetSummary) {
      mallTargetSummary.textContent = 'Selected probe target: ' + selectedVideoId + ' · ' + OFFICIAL_HOSTS[selectedHostKey];
    }
  }

  function syncReferenceReturnLink() {
    const back = document.getElementById('hpc-probe-return');
    if (back) {
      back.href = buildReturnHref(selectedVideoId, selectedHostKey);
    }
  }

  function classifyCatalogTier(videoId) {
    if (!videoId) return 'none';
    if (ADMITTED_SET.has(videoId)) return 'admitted-hpc';
    if (DIAGNOSTIC_SET.has(videoId)) return 'diagnostic-only';
    return 'other-mall';
  }

  function formatErrorStatus() {
    if (lastLoaderFailure) {
      return lastLoaderFailure + ' (iframe/API loader failure; not IFrame error 101/150)';
    }
    if (lastErrorCode === null || lastErrorCode === undefined) {
      if (observedPrompt === 'login-required-bot-check') {
        return 'none reported by IFrame API (screen prompt recorded as LOGIN_REQUIRED challenge)';
      }
      return 'none';
    }
    if (Number(lastErrorCode) === 101 || Number(lastErrorCode) === 150) {
      if (observedPrompt === 'login-required-bot-check') {
        return 'IFrame error ' + lastErrorCode + ' + screen prompt LOGIN_REQUIRED challenge';
      }
      if (observedPrompt === 'embed-unavailable-or-disabled') {
        return 'IFrame error ' + lastErrorCode + ' + screen prompt unavailable/embed-disabled';
      }
      return 'IFrame error ' + lastErrorCode + ' (official 101/150 embed refusal; distinct from confirmed LOGIN_REQUIRED unless prompt observed)';
    }
    return 'IFrame error ' + lastErrorCode;
  }

  function record(snapshot) {
    if (!snapshot || typeof snapshot.videoId !== 'string' || !/^[A-Za-z0-9_-]{11}$/.test(snapshot.videoId)) return;
    if (!reference && validVideoId(snapshot.videoId) && snapshot.videoId !== selectedVideoId) {
      selectedVideoId = snapshot.videoId;
      syncMallSelectionUi();
    }
    if (snapshot.videoId !== activeId || (snapshot.state === 'loading' && trace.at(-1)?.state !== 'loading')) {
      activeId = snapshot.videoId;
      started = performance.now();
      trace.length = 0;
      firstTime = null;
      peakTime = null;
      advanced = 0;
      lastFrame = null;
      lastErrorCode = null;
      lastLoaderFailure = null;
      autoplayStatus = 'not-blocked';
    }
    const frame = document.querySelector(reference ? '#hpc-probe-embed iframe' : '.video-player-stage iframe');
    const rect = frame?.getBoundingClientRect();
    if (rect?.width && rect.height) lastFrame = [Math.round(rect.width), Math.round(rect.height)];
    const { state, code, providerState, positionSeconds } = snapshot;
    if (state === 'autoplay-blocked' || state === 'manual-play') {
      autoplayStatus = state;
    }
    if (state === 'api-timeout' || state === 'api-load-error') {
      lastLoaderFailure = state;
    }
    if (code !== undefined && code !== null) {
      lastErrorCode = code;
    }
    if (state === 'playing' && Number.isFinite(positionSeconds)) {
      firstTime ??= positionSeconds;
      peakTime = peakTime === null ? positionSeconds : Math.max(peakTime, positionSeconds);
      advanced = Math.max(advanced, positionSeconds - firstTime);
    }
    const previous = trace.at(-1);
    if (previous?.state === state && previous?.code === code && previous?.providerState === providerState) return;
    const isActiveGesture = (state === 'ready' || state === 'starting')
      ? navigator['userActivation']?.isActive
      : undefined;
    trace.push({
      state,
      code,
      providerState,
      elapsedMs: Math.round(performance.now() - started),
      activation: isActiveGesture
    });
    if (trace.length > 24) trace.shift();
  }

  function currentMallBuildLabel() {
    const domLabel = document.querySelector('.mall-build-label')?.textContent?.trim();
    if (domLabel) return domLabel;
    if (deploymentMeta.mallBuild) return 'Build ' + deploymentMeta.mallBuild;
    return reference ? 'reference-only' : 'not-mounted';
  }

  function receipt() {
    refreshObservedCaches();
    const events = trace.map((entry) => {
      const details = [
        entry.code === undefined || entry.code === null ? '' : 'code ' + entry.code,
        entry.providerState === undefined ? '' : 'YT state ' + entry.providerState,
        entry.activation === undefined ? '' : 'activation ' + entry.activation
      ].filter(Boolean);
      return entry.elapsedMs + ' ms ' + entry.state + (details.length ? ' (' + details.join(', ') + ')' : '');
    });
    const reportedVideo = activeId || (reference ? selectedVideoId : null);
    const embedHostUsed = reference ? OFFICIAL_HOSTS[selectedHostKey] : 'https://www.youtube.com (Mall player)';
    const timeRange = firstTime !== null && peakTime !== null
      ? ' (' + firstTime.toFixed(2) + ' s -> ' + peakTime.toFixed(2) + ' s)'
      : '';
    return [
      'HPC iPhone playback test',
      'Path: ' + (reference ? 'Official YouTube embed' : 'Mall player'),
      'Mode: ' + (standalone ? 'Home Screen web app' : 'Browser') + ' · ' + platform,
      'Host: ' + location.host,
      'Embed host: ' + embedHostUsed,
      'Source revision: ' + deploymentMeta.sourceSha + ' · channel ' + deploymentMeta.channelId +
        ' · version ' + deploymentMeta.hostingVersion + ' · ' + currentMallBuildLabel(),
      'SW controller: ' + readControllerSummary() + ' · registration ' + swRegistrationSummary,
      'Mall caches seen: ' + (observedCaches.join(', ') || 'none'),
      'Video: ' + (reportedVideo ? reportedVideo + ' (' + classifyCatalogTier(reportedVideo) + ')' : 'tap a video first'),
      'Selected target: ' + selectedVideoId + ' · ' + selectedHostKey,
      'Iframe: ' + (lastFrame ? lastFrame.join(' × ') + ' CSS px' : 'not observed'),
      'Autoplay status: ' + autoplayStatus,
      'Error status: ' + formatErrorStatus(),
      'Screen prompt: ' + observedPrompt,
      'Advancing media time: ' + advanced.toFixed(2) + ' s' + timeRange,
      'Events: ' + (events.join(' → ') || 'none')
    ].join('\n');
  }

  function buildPromptSelect() {
    const label = document.createElement('label');
    label.className = 'hpc-probe-field';
    label.textContent = 'Observed screen state (optional): ';
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Observed screen prompt');
    for (const [value, text] of OBSERVED_PROMPTS) {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = text;
      select.append(opt);
    }
    select.value = observedPrompt;
    select.addEventListener('change', () => {
      observedPrompt = validPromptKey(select.value);
    });
    label.append(select);
    return label;
  }

  function buildHostSelect(onSelectChange) {
    const label = document.createElement('label');
    label.className = 'hpc-probe-field';
    label.textContent = 'Official YouTube host: ';
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Official YouTube host');
    for (const [key, origin] of Object.entries(OFFICIAL_HOSTS)) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = origin.replace('https://', '');
      select.append(opt);
    }
    select.value = selectedHostKey;
    select.addEventListener('change', () => {
      selectedHostKey = validHostKey(select.value) || 'youtube';
      onSelectChange(selectedHostKey);
    });
    label.append(select);
    return label;
  }

  function buildVideoSelect(onVideoChange) {
    const label = document.createElement('label');
    label.className = 'hpc-probe-field';
    label.textContent = 'Test Short: ';
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Test Short');
    const admittedGroup = document.createElement('optgroup');
    admittedGroup.label = 'Admitted HPC Shorts (8)';
    for (const id of ADMITTED_HPC_SHORTS) {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = id + (id === firstShort ? ' (default)' : '');
      admittedGroup.append(opt);
    }
    const diagGroup = document.createElement('optgroup');
    diagGroup.label = 'Diagnostic-only Shorts (4 · unadmitted)';
    for (const id of DIAGNOSTIC_ONLY_SHORTS) {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = id + ' (diagnostic-only)';
      diagGroup.append(opt);
    }
    select.append(admittedGroup, diagGroup);
    select.value = selectedVideoId;
    select.addEventListener('change', () => {
      selectedVideoId = validVideoId(select.value) || firstShort;
      onVideoChange(selectedVideoId);
    });
    label.append(select);
    return label;
  }

  function addReceiptControls(parent) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Copy playback result';
    const result = document.createElement('textarea');
    result.readOnly = true;
    result.hidden = true;
    result.rows = 8;
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
    if (!menu || menu.querySelector('[data-hpc-probe-tools]')) return Boolean(menu);
    const tools = document.createElement('section');
    tools.setAttribute('data-hpc-probe-tools', '1');

    mallTargetSummary = document.createElement('p');
    mallTargetSummary.style.cssText = 'margin:0.4rem 0;font-size:0.85rem;opacity:0.9';
    const hostSelector = buildHostSelect(() => syncMallSelectionUi());
    const promptSelector = buildPromptSelect();
    tools.append(mallTargetSummary, hostSelector, promptSelector);
    addReceiptControls(tools);

    mallCompareLink = document.createElement('a');
    mallCompareLink.textContent = 'Compare with the official YouTube embed';
    mallCompareLink.style.cssText = 'display:block;padding:0.75rem 0;color:inherit';
    mallCompareLink.addEventListener('click', () => {
      const liveVideoId = validVideoId(window.mallVideoPlayer?.getCurrentVideoId?.()) ||
        validVideoId(activeId) ||
        selectedVideoId;
      selectedVideoId = liveVideoId;
      syncMallSelectionUi();
      window.mallStateRestore?.save?.();
    });
    tools.append(mallCompareLink);
    syncMallSelectionUi();

    const diagnostics = menu.querySelector('[data-mall-daemon-diagnostics]');
    if (diagnostics) {
      diagnostics.append(tools);
      const group = menu.querySelector('[data-preview-diagnostics]');
      if (group) group.hidden = false;
    }
    else {
      // Compatibility with older preview shells: technical selectors are still
      // explicitly collapsed rather than crowding the ordinary control menu.
      const group = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'Playback diagnostics';
      group.append(summary, tools);
      menu.append(group);
    }
    return true;
  }

  function mountReference() {
    syncReferenceReturnLink();
    const embedOrigin = OFFICIAL_HOSTS[selectedHostKey];
    const iframe = document.createElement('iframe');
    const url = new URL('/embed/' + selectedVideoId, embedOrigin);
    url.search = new URLSearchParams({
      enablejsapi: '1',
      playsinline: '1',
      controls: '1',
      origin: location.origin
    }).toString();
    iframe.src = url.href;
    iframe.title = 'Official YouTube Short ' + selectedVideoId;
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    reference.append(iframe);

    const controlsRoot = document.getElementById('hpc-probe-controls');
    if (controlsRoot) {
      const selectors = document.createElement('div');
      selectors.className = 'hpc-probe-row';
      const navigateSelection = () => {
        writeStoredSelection(selectedVideoId, selectedHostKey);
        syncReferenceReturnLink();
        location.assign(buildReferenceHref(selectedVideoId, selectedHostKey));
      };
      selectors.append(
        buildVideoSelect(navigateSelection),
        buildHostSelect(navigateSelection),
        buildPromptSelect()
      );
      controlsRoot.append(selectors);
      addReceiptControls(controlsRoot);
    }

    const update = (state, fields) => {
      referenceState = { videoId: selectedVideoId, state, ...fields };
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
      record(window.mallVideoPlayer?.getPlaybackSnapshot?.());
    }
  }, 300);
})();
