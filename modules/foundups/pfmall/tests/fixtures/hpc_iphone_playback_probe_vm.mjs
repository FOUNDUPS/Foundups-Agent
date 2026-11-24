import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../../../..');
const probeSource = fs.readFileSync(path.join(__dirname, 'hpc_iphone_playback_probe.js'), 'utf8');
const refHtml = fs.readFileSync(path.join(__dirname, 'hpc_iphone_playback_reference.html'), 'utf8');
const publicHpcCatalog = JSON.parse(
  fs.readFileSync(path.join(repoRoot, 'public/member/mall-public-video-catalog.json'), 'utf8')
);

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName || 'DIV').toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.parentNode = null;
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {};
    this.dataset = {};
    this.hidden = false;
    this.readOnly = false;
    this.textContent = '';
    this.value = '';
    this.href = '';
    this.src = '';
    this.title = '';
    this.allow = '';
    this.allowFullscreen = false;
    this.referrerPolicy = '';
    this.className = '';
    this.label = '';
    this.id = '';
    this._rect = { width: 358, height: 260 };
  }

  setAttribute(name, val) {
    const str = String(val);
    this.attributes.set(name, str);
    if (name === 'id') this.id = str;
    if (name === 'href') this.href = str;
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  append(...nodes) {
    for (const n of nodes) {
      if (typeof n === 'string') {
        const span = new FakeElement('#text', this.ownerDocument);
        span.textContent = n;
        span.parentNode = this;
        this.children.push(span);
      } else if (n) {
        n.parentNode = this;
        this.children.push(n);
        if (this.tagName === 'SELECT' && !this.value) {
          const firstOpt = this._firstOptionValue();
          if (firstOpt) this.value = firstOpt;
        }
      }
    }
  }

  before(node) {
    if (!this.parentNode) return;
    const idx = this.parentNode.children.indexOf(this);
    node.parentNode = this.parentNode;
    if (idx >= 0) this.parentNode.children.splice(idx, 0, node);
    else this.parentNode.children.push(node);
  }

  _firstOptionValue() {
    for (const c of this.children) {
      if (c.tagName === 'OPTION' && c.value) return c.value;
      if (c.tagName === 'OPTGROUP') {
        const sub = c.children.find((o) => o.tagName === 'OPTION' && o.value);
        if (sub) return sub.value;
      }
    }
    return '';
  }

  addEventListener(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(fn);
  }

  async trigger(type, eventObj = {}) {
    for (const fn of this.listeners.get(type) || []) {
      await fn({ target: this, ...eventObj });
    }
  }

  focus() {}
  select() {}

  getBoundingClientRect() {
    return this._rect;
  }

  matches(selector) {
    if (selector === 'iframe') return this.tagName === 'IFRAME';
    if (selector === 'form[method="dialog"]') {
      return this.tagName === 'FORM' && this.getAttribute('method') === 'dialog';
    }
    if (selector === '[data-hpc-probe-tools]') {
      return this.attributes.has('data-hpc-probe-tools');
    }
    if (selector === '.mall-build-label') {
      return this.className.split(/\s+/).includes('mall-build-label');
    }
    return false;
  }

  querySelector(selector) {
    if (selector === '#hpc-probe-embed iframe') {
      const embed = this.ownerDocument.getElementById('hpc-probe-embed');
      return embed ? embed.querySelector('iframe') : null;
    }
    if (selector === '.video-player-stage iframe') {
      const stage = this.ownerDocument.getElementById('stage-root');
      return stage ? stage.querySelector('iframe') : null;
    }
    for (const child of this.children) {
      if (child.matches?.(selector)) return child;
      const nested = child.querySelector?.(selector);
      if (nested) return nested;
    }
    return null;
  }

  findAll(predicate, acc = []) {
    if (predicate(this)) acc.push(this);
    for (const child of this.children) {
      if (child.findAll) child.findAll(predicate, acc);
    }
    return acc;
  }
}

function createHarness(opts = {}) {
  const mode = opts.mode || 'reference';
  const url = new URL(opts.url || 'https://foundupscom--probe.web.app/member/playback-probe/reference.html');
  const sessionStore = opts.sessionStore || new Map();
  const navigations = [];
  const intervals = [];
  const timeouts = [];
  const winListeners = new Map();

  const doc = {
    hidden: false,
    head: null,
    body: null,
    _byId: new Map(),
    createElement(tag) {
      return new FakeElement(tag, doc);
    },
    getElementById(id) {
      if (doc._byId.has(id)) return doc._byId.get(id);
      const found = doc.body.findAll((el) => el.id === id)[0] || null;
      return found;
    },
    querySelector(sel) {
      return doc.body.querySelector(sel);
    }
  };
  doc.head = new FakeElement('head', doc);
  doc.body = new FakeElement('body', doc);

  if (mode === 'reference') {
    const embed = new FakeElement('div', doc);
    embed.setAttribute('id', 'hpc-probe-embed');
    const controls = new FakeElement('div', doc);
    controls.setAttribute('id', 'hpc-probe-controls');
    const ret = new FakeElement('a', doc);
    ret.setAttribute('id', 'hpc-probe-return');
    ret.setAttribute('href', '/member/?foundup=hpc');
    doc.body.append(embed, controls, ret);
  } else {
    const buildSmall = new FakeElement('small', doc);
    buildSmall.className = 'mall-build-label';
    buildSmall.textContent = opts.mallBuildLabel || 'Build v19';
    const menu = new FakeElement('dialog', doc);
    menu.setAttribute('id', 'videoScopeOptions');
    const dialogForm = new FakeElement('form', doc);
    dialogForm.setAttribute('method', 'dialog');
    menu.append(dialogForm);
    const stageRoot = new FakeElement('div', doc);
    stageRoot.setAttribute('id', 'stage-root');
    const mallIframe = new FakeElement('iframe', doc);
    mallIframe._rect = { width: 369, height: 226 };
    stageRoot.append(mallIframe);
    doc.body.append(buildSmall, menu, stageRoot);
  }

  let currentClockSeconds = 0;
  let ytEvents = null;
  let clipboardText = '';
  let mallStateSaved = 0;

  const locationObj = {
    href: url.href,
    origin: url.origin,
    host: url.host,
    hostname: url.hostname,
    pathname: url.pathname,
    search: url.search,
    assign(target) {
      navigations.push(target);
    }
  };

  const sessionStorageObj = {
    getItem(k) { return sessionStore.has(k) ? sessionStore.get(k) : null; },
    setItem(k, v) { sessionStore.set(k, String(v)); }
  };

  const navigatorObj = {
    standalone: Boolean(opts.standalone),
    userAgent: opts.ua || 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15',
    userActivation: { isActive: opts.activation ?? true },
    clipboard: {
      async writeText(text) { clipboardText = text; }
    },
    serviceWorker: {
      controller: opts.swController === undefined ? {
        scriptURL: url.origin + '/member/member-sw.js',
        state: 'activated'
      } : opts.swController,
      async getRegistration() {
        return opts.swReg === undefined ? {
          active: { scriptURL: url.origin + '/member/member-sw.js' }
        } : opts.swReg;
      }
    }
  };

  const windowObj = {
    location: locationObj,
    document: doc,
    navigator: navigatorObj,
    sessionStorage: sessionStorageObj,
    URL,
    URLSearchParams,
    performance: { now: () => opts.now?.() ?? 100 },
    matchMedia: (q) => ({
      matches: q === '(display-mode: standalone)' ? Boolean(opts.standalone) : false
    }),
    caches: {
      async keys() { return opts.caches || ['pfmall-member-v19', 'unrelated-app-v1']; }
    },
    fetch: async (targetUrl) => {
      if (targetUrl === '/member/playback-probe/deployment.json' && opts.deploymentMeta) {
        return {
          ok: true,
          redirected: false,
          async json() { return opts.deploymentMeta; }
        };
      }
      return { ok: false, redirected: false, async json() { return null; } };
    },
    mallVideoProjection: mode === 'mall' ? {
      resolve: () => (opts.resolveMode === 'member' ? null : 'hpc'),
      resolveMember: () => (opts.resolveMode === 'member' ? 'hpc' : null)
    } : undefined,
    mallVideoPlayer: mode === 'mall' ? {
      getCurrentVideoId: () => opts.currentVideoId || null,
      getPlaybackSnapshot: () => opts.snapshot || null
    } : undefined,
    mallStateRestore: {
      save() { mallStateSaved += 1; }
    },
    YT: {
      Player: function (_iframe, cfg) {
        ytEvents = cfg.events;
        return {
          getCurrentTime() { return currentClockSeconds; }
        };
      }
    },
    MutationObserver: class {
      observe() {}
      disconnect() {}
    },
    addEventListener(type, fn) {
      if (!winListeners.has(type)) winListeners.set(type, []);
      winListeners.get(type).push(fn);
    },
    dispatchPlayback(detail) {
      for (const fn of winListeners.get('mallVideoPlayback') || []) {
        fn({ detail });
      }
    },
    setTimeout(fn, ms) {
      timeouts.push({ fn, ms });
      return timeouts.length;
    },
    clearTimeout() {},
    setInterval(fn, ms) {
      intervals.push({ fn, ms });
      return intervals.length;
    }
  };
  windowObj.window = windowObj;

  vm.runInNewContext(probeSource, windowObj, { filename: 'hpc_iphone_playback_probe.js' });

  return {
    doc,
    windowObj,
    sessionStore,
    navigations,
    intervals,
    getYtEvents: () => ytEvents,
    setClock: (sec) => { currentClockSeconds = sec; },
    getClipboard: () => clipboardText,
    getMallStateSaved: () => mallStateSaved,
    flushAsync: () => new Promise((r) => setImmediate(r))
  };
}

// 1. Reference HTML structure keeps controls outside #hpc-probe-embed
assert.match(refHtml, /<div id="hpc-probe-embed"><\/div>\s*<div id="hpc-probe-controls"><\/div>/);
assert.match(refHtml, /<a id="hpc-probe-return" href="\/member\/\?foundup=hpc">/);

// 2. Four diagnostic-only Shorts remain absent from public HPC catalog
const admittedIds = new Set(publicHpcCatalog.hpc.lane.videos.map((v) => v.video_id));
assert.equal(admittedIds.size, publicHpcCatalog.hpc.lane.videos.length, 'Public video IDs stay unique');
assert.deepEqual([...admittedIds].slice(0, 8), [
  'iJuguXpbRR4', 'sSzWdw7MNjs', 'BXCzUOh9Y8M', 'OTTz58wPi24',
  'fp2BkIS2FNI', 'DDAfdpJeUP0', 'Pdz1Q5tHmJQ', 'urXOSlVgPdk'
], 'Original reviewed queue identities/order survive incremental admission');
assert.ok(admittedIds.has('8qO3908bKAM'), 'Requested regular video is admitted');
for (const unadmitted of ['R7xm4MZ9N4w', 'TppBUj_7lC0', 'qNFSBWXhZSY', 'B0P1Zci5Pxo']) {
  assert.equal(admittedIds.has(unadmitted), false, `Unadmitted Short ${unadmitted} must not enter public catalog`);
}

// 3. Adversarial query parameters fall back strictly to default Short + official youtube.com
{
  const h = createHarness({
    mode: 'reference',
    url: 'https://foundupscom--probe.web.app/member/playback-probe/reference.html?v=AAAAAAAAAAA&host=https://evil.example'
  });
  await h.flushAsync();
  const embedDiv = h.doc.getElementById('hpc-probe-embed');
  assert.equal(embedDiv.children.length, 1, 'Only the official iframe belongs inside #hpc-probe-embed');
  const iframe = embedDiv.children[0];
  assert.equal(iframe.tagName, 'IFRAME');
  assert.match(iframe.src, /^https:\/\/www\.youtube\.com\/embed\/iJuguXpbRR4\?/);
  const controlsDiv = h.doc.getElementById('hpc-probe-controls');
  assert.ok(controlsDiv.findAll((el) => el.tagName === 'SELECT').length === 3);
}

// 4. Valid nocookie + diagnostic-only Short + advancing time + provenance receipt
{
  let nowMs = 1000;
  const h = createHarness({
    mode: 'reference',
    standalone: true,
    now: () => nowMs,
    deploymentMeta: {
      source_sha: '247e12ce6e05dea4c41456960b31445c93c15a41',
      channel_id: 'hpc-iphone-v19-probe',
      hosting_version: 'b59e90fef9473170',
      mall_build: 'v19'
    },
    url: 'https://foundupscom--probe.web.app/member/playback-probe/reference.html?v=R7xm4MZ9N4w&host=nocookie'
  });
  await h.flushAsync();
  const iframe = h.doc.getElementById('hpc-probe-embed').children[0];
  assert.match(iframe.src, /^https:\/\/www\.youtube-nocookie\.com\/embed\/R7xm4MZ9N4w\?/);

  h.windowObj.onYouTubeIframeAPIReady();
  nowMs = 1220;
  h.getYtEvents().onReady();
  nowMs = 1450;
  h.setClock(0.30);
  h.getYtEvents().onStateChange({ data: 1 });
  h.intervals[0].fn();
  nowMs = 2300;
  h.setClock(1.75);
  h.intervals[0].fn();

  const copyBtn = h.doc.getElementById('hpc-probe-controls').findAll(
    (el) => el.tagName === 'BUTTON' && el.textContent === 'Copy playback result'
  )[0];
  await copyBtn.trigger('click');
  const receipt = h.getClipboard();
  assert.match(receipt, /Path: Official YouTube embed/);
  assert.match(receipt, /Mode: Home Screen web app · iPhone OS 18_1/);
  assert.match(receipt, /Embed host: https:\/\/www\.youtube-nocookie\.com/);
  assert.match(receipt, /Source revision: 247e12ce6e05dea4c41456960b31445c93c15a41 · channel hpc-iphone-v19-probe · version b59e90fef9473170 · Build v19/);
  assert.match(receipt, /SW controller: \/member\/member-sw\.js \(activated\) · registration active:\/member\/member-sw\.js/);
  assert.match(receipt, /Mall caches seen: pfmall-member-v19/);
  assert.match(receipt, /Video: R7xm4MZ9N4w \(diagnostic-only\)/);
  assert.match(receipt, /Advancing media time: 1\.45 s \(0\.30 s -> 1\.75 s\)/);
  assert.equal(
    h.doc.getElementById('hpc-probe-return').href,
    '/member/?foundup=hpc&probe_v=R7xm4MZ9N4w&probe_host=nocookie'
  );
}

// 5. Distinguish official 101/150 embed refusal from screen-observed LOGIN_REQUIRED & autoplay-blocked
{
  const h = createHarness({
    mode: 'reference',
    swController: { scriptURL: 'https://evil.example/sw.js', state: 'activated' },
    url: 'https://foundupscom--probe.web.app/member/playback-probe/reference.html?v=OTTz58wPi24&host=youtube'
  });
  await h.flushAsync();
  h.windowObj.onYouTubeIframeAPIReady();
  h.getYtEvents().onAutoplayBlocked();
  h.getYtEvents().onError({ data: 150 });

  const controls = h.doc.getElementById('hpc-probe-controls');
  const copyBtn = controls.findAll((el) => el.tagName === 'BUTTON')[0];
  await copyBtn.trigger('click');
  const unconfirmedReceipt = h.getClipboard();
  assert.match(unconfirmedReceipt, /SW controller: cross-origin-worker \(activated\)/);
  assert.match(unconfirmedReceipt, /Autoplay status: autoplay-blocked/);
  assert.match(
    unconfirmedReceipt,
    /Error status: IFrame error 150 \(official 101\/150 embed refusal; distinct from confirmed LOGIN_REQUIRED unless prompt observed\)/
  );

  const promptSelect = controls.findAll(
    (el) => el.tagName === 'SELECT' && el.getAttribute('aria-label') === 'Observed screen prompt'
  )[0];
  promptSelect.value = 'login-required-bot-check';
  await promptSelect.trigger('change');
  await copyBtn.trigger('click');
  assert.match(h.getClipboard(), /Error status: IFrame error 150 \+ screen prompt LOGIN_REQUIRED challenge/);
  assert.match(h.getClipboard(), /Screen prompt: login-required-bot-check/);
}

// 6. Bidirectional selection retention between Mall (/member/?foundup=hpc) and reference.html
{
  const sharedSession = new Map();
  const mall = createHarness({
    mode: 'mall',
    resolveMode: 'member',
    sessionStore: sharedSession,
    url: 'https://foundupscom--probe.web.app/member/?foundup=hpc'
  });
  await mall.flushAsync();

  mall.windowObj.dispatchPlayback({
    videoId: 'DDAfdpJeUP0',
    state: 'playing',
    providerState: 1,
    positionSeconds: 0.5
  });

  const menu = mall.doc.getElementById('videoScopeOptions');
  const hostSelect = menu.findAll(
    (el) => el.tagName === 'SELECT' && el.getAttribute('aria-label') === 'Official YouTube host'
  )[0];
  hostSelect.value = 'nocookie';
  await hostSelect.trigger('change');

  const compareLink = menu.findAll((el) => el.tagName === 'A')[0];
  assert.equal(compareLink.href, '/member/playback-probe/reference.html?v=DDAfdpJeUP0&host=nocookie');
  await compareLink.trigger('click');
  assert.equal(mall.getMallStateSaved(), 1);
  assert.equal(sharedSession.size, 1);
  assert.equal(sharedSession.has('pfmall_video_scope_hpc_v1'), false);

  // Opening reference.html without query params restores selection from tab-local probe storage
  const refFromSession = createHarness({
    mode: 'reference',
    sessionStore: sharedSession,
    url: 'https://foundupscom--probe.web.app/member/playback-probe/reference.html'
  });
  await refFromSession.flushAsync();
  const refIframe = refFromSession.doc.getElementById('hpc-probe-embed').children[0];
  assert.match(refIframe.src, /^https:\/\/www\.youtube-nocookie\.com\/embed\/DDAfdpJeUP0\?/);
}

console.log('HPC iPhone playback probe runtime: 6 passed.');
