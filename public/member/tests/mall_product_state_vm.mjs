/**
 * Actual shared state/SW execution with bounded storage and fetch fixtures.
 * No browser, provider credentials, remote requests or visual claims.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const stateSource = readFileSync(join(root, 'js/mall-state-restore.js'), 'utf8');
const swSource = readFileSync(join(root, 'member-sw.js'), 'utf8');
const rootSwSource = readFileSync(join(root, '..', 'sw.js'), 'utf8');
const gatewayHtml = readFileSync(join(root, '..', 'index.html'), 'utf8');
const videoProjectionSource = readFileSync(join(root, 'js/mall-video-projection.js'), 'utf8');
const VIDEO_KEY = 'pfmall_mall_state_v1';
const PRODUCT_KEY = 'pfmall_product_move2japan_state_v1';
const RETURN_KEY = 'pfmall_product_return_v1';
const ORIGIN = 'https://foundups.com';
let checks = 0;
const copy = value => JSON.parse(JSON.stringify(value));
async function check(name, fn) {
  await fn();
  checks++;
  console.log('PASS ' + name);
}
function storage(map) {
  return {
    getItem: key => map.get(key) ?? null,
    setItem: (key, value) => map.set(key, value),
    removeItem: key => map.delete(key)
  };
}
function stateRuntime(href = ORIGIN + '/member/?foundup=move2japan') {
  const local = new Map(), session = new Map(), events = {}, timers = new Map(), calls = [], frames = [], bindings = [];
  let clock = 1000000, timerId = 0;
  const add = (kind, fn, options) => { (events[kind] ||= []).push(fn); bindings.push({ kind, options }); };
  const wrapper = { scrollTop: 40, scrollLeft: 0, addEventListener: (kind, fn, options) => add('wrapper:' + kind, fn, options) };
  const tf = {
    geographic: { version: 1, foundup_id: 'move2japan', activeGroupKey: 'wakasa', scrollTop: 40, groupOffset: 0, rows: [] },
    getGeographicState() { return this.geographic; },
    restoreGeographicState(value) { calls.push(['geo', copy(value)]); return true; },
    scope: { type: 'creator', query: '012' },
    layout: 'rows',
    offsets: { travel: 180, music: 30 },
    getLayoutMode() { return this.layout; },
    getRowOffsets() { return this.offsets; },
    setLayoutMode(value) { calls.push(['layout', value]); this.layout = value; return true; },
    restoreRowOffsets(value) { calls.push(['rows', copy(value)]); this.offsets = value; },
    getProjection: () => 'category',
    getFieldScope() { return this.scope; },
    setProjection: value => calls.push(['projection', value]),
    setFieldScope(value) { calls.push(['scope', copy(value)]); this.scope = value; },
    clearFieldScope() { calls.push(['clear']); this.scope = null; }
  };
  const doc = { querySelector: () => wrapper, addEventListener: add, visibilityState: 'visible' };
  const win = { location: new URL(href), mallTileField: tf, addEventListener: (kind, fn) => add('window:' + kind, fn) };
  const context = {
    window: win, document: doc, localStorage: storage(local), sessionStorage: storage(session),
    URL, URLSearchParams, Date: { now: () => clock },
    requestAnimationFrame: fn => frames.push(fn),
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id)
  };
  runInNewContext(videoProjectionSource, { window: win, URLSearchParams });
  runInNewContext(stateSource, context);
  return {
    api: win.mallStateRestore, local, session, calls, events, win, tf, context, wrapper, bindings,
    time: value => { clock = value; },
    flushFrames: () => { for (const fn of frames.splice(0)) fn(); },
    flush: () => { for (const fn of [...timers.values()]) fn(); timers.clear(); },
    fire: (kind, event) => { for (const fn of events[kind] || []) fn(event); }
  };
}

await check('public and member video routes have separate exact selectors', () => {
  const window = { location: new URL(ORIGIN) };
  runInNewContext(videoProjectionSource, { window, URLSearchParams });
  const route = window.mallVideoProjection;
  for (const path of ['/member/?foundup=hpc', '/member/index.html?foundup=hpc&account=1']) {
    assert.equal(route.resolve(new URL(path, ORIGIN)), null);
    assert.equal(route.resolveMember(new URL(path, ORIGIN)), 'hpc');
  }
  for (const path of ['/member/?foundup=hpc&foundup=move2japan', '/member/?foundup=__proto__', '/f/hpc/app?foundup=hpc']) {
    assert.equal(route.resolve(new URL(path, ORIGIN)), null);
    assert.equal(route.resolveMember(new URL(path, ORIGIN)), null);
  }
  assert.equal(route.resolve(new URL('https://hpc.foundups.com/member/?foundup=move2japan')), 'hpc');
  assert.equal(route.resolve(new URL('https://hpc.foundups.com/f/hpc/app')), null);
  assert.equal(route.resolveMember(new URL('https://hpc.foundups.com/member/?foundup=hpc')), null);
  assert.equal(route.hostScope(new URL('https://hpc.foundups.com/')), 'hpc');
  assert.equal(route.hostScope(new URL('https://hpc.foundups.com.example.org/')), null);
  const publicUrl = 'https://hpc.foundups.com/';
  assert.equal(route.discoveryPath('hpc', publicUrl), publicUrl);
  assert.equal(route.discoveryPath('hpc', ORIGIN + '/member/?foundup=hpc'), publicUrl);
  assert.equal(route.discoveryPath('hpc', 'https://example.invalid/member/?foundup=hpc'), null);
  assert.equal(route.discoveryPath('move2japan', publicUrl), null);
  assert.equal(route.memberPath('hpc'), '/member/?foundup=hpc');
  assert.equal(route.memberPath('move2japan'), null);
});

await check('HPC sign-in return is bounded to a registered member path and one use', () => {
  const h = stateRuntime(ORIGIN + '/member/?foundup=hpc&next=https%3A%2F%2Fexample.invalid#account');
  assert.equal(h.api.rememberMemberVideoReturn(), true);
  const record = JSON.parse(h.session.get(RETURN_KEY));
  assert.deepEqual(record, { product_id: 'hpc', created_at: 1000000, filters: {} });
  assert.equal(h.api.consumeProductReturn(), '/member/?foundup=hpc');
  assert.equal(h.api.consumeProductReturn(), null);
  h.session.set(RETURN_KEY, JSON.stringify({ ...record, filters: { q: 'unused' } }));
  assert.equal(h.api.consumeProductReturn(), null);
  h.session.set(RETURN_KEY, JSON.stringify(record));
  h.time(1900001);
  assert.equal(h.api.consumeProductReturn(), null);
  for (const url of ['https://hpc.foundups.com/member/?foundup=hpc', ORIGIN + '/member/?foundup=hpc&foundup=hpc']) {
    assert.equal(stateRuntime(url).api.rememberMemberVideoReturn(), false);
  }
});

await check('fixed video projection restores only tab-local position', () => {
  const h = stateRuntime(ORIGIN + '/member/?foundup=hpc');
  h.local.set(VIDEO_KEY, 'preserve-video');
  h.local.set(PRODUCT_KEY, 'preserve-product');
  const key = 'pfmall_video_scope_hpc_v1';
  assert.equal(h.api.selectVideoScope('hpc'), true);
  assert.equal(h.api.selectProduct('move2japan'), false);
  h.api.save();
  assert.deepEqual(JSON.parse(h.session.get(key)), { scrollTop: 40, scrollLeft: 0 });
  assert.equal(h.local.has(key), false);
  assert.equal(h.local.get(VIDEO_KEY), 'preserve-video');
  assert.equal(h.local.get(PRODUCT_KEY), 'preserve-product');
  h.wrapper.scrollTop = 5;
  assert.equal(h.api.restore(), true);
  h.flushFrames();
  assert.equal(h.wrapper.scrollTop, 40);
  assert.deepEqual(h.calls, []);
  const desktop = { scrollTop: 40, scrollLeft: 0, anchorVideoId: 'HPC00000024', anchorOffset: -12,
    theater: { videoId: 'HPC00000012', query: 'creator commentary' } };
  h.session.set(key, JSON.stringify(desktop));
  assert.equal(h.api.restore(), true);
  h.flushFrames();
  assert.deepEqual(JSON.parse(h.session.get(key)), desktop);
  h.session.set(key, JSON.stringify({ ...desktop, theater: { videoId: 'bad/id', query: 'x'.repeat(301) } }));
  assert.equal(h.api.restore(), false);
  assert.equal(h.session.has(key), false);
  h.session.set(key, JSON.stringify({ scrollTop: 40, scrollLeft: 0, fieldScope: {} }));
  assert.equal(h.api.restore(), false);
  assert.equal(h.session.has(key), false);
});

await check('video namespace retains category layout and rows while product state stays separate', () => {
  const h = stateRuntime();
  h.api.save();
  const video = h.local.get(VIDEO_KEY);
  assert.equal(JSON.parse(video).projection, 'category');
  assert.equal(JSON.parse(video).layoutMode, 'rows');
  assert.equal(JSON.parse(video).rowOffsets.travel, 180);
  h.api.restore();
  assert.deepEqual(h.calls.map(call => call[0]), ['layout', 'scope', 'projection']);
  h.flushFrames();
  assert.deepEqual(h.calls.map(call => call[0]), ['layout', 'scope', 'projection', 'rows']);
  assert.equal(h.api.selectProduct('move2japan'), true);
  assert.equal(h.api.peek(), null);
  h.api.save();
  assert.equal(h.local.get(VIDEO_KEY), video);
  assert.equal(JSON.parse(h.local.get(PRODUCT_KEY)).product_id, 'move2japan');
  h.calls.length = 0;
  assert.equal(h.api.restore(), true);
  assert.deepEqual(h.calls.map(call => call[0]), ['geo']);
  assert.equal(h.api.selectProduct(null), true);
  assert.equal(h.api.peek().projection, 'category');
});

await check('unknown products and foreign or mixed stored state cannot cross namespaces', () => {
  const h = stateRuntime();
  h.api.selectProduct('move2japan');
  for (const id of ['other', '__proto__', 'constructor', '/member/', undefined, {}, Object.create(null)]) assert.equal(h.api.selectProduct(id), false);
  h.api.save();
  const good = JSON.parse(h.local.get(PRODUCT_KEY));
  h.local.set(VIDEO_KEY, 'preserve-video');
  for (const mixed of [{ fieldScope: { type: 'personal' } }, { layoutMode: 'grid' }, { rowOffsets: { travel: 999 } }]) {
    h.local.set(PRODUCT_KEY, JSON.stringify({ ...good, ...mixed }));
    assert.equal(h.api.restore(), false);
    assert.equal(h.local.has(PRODUCT_KEY), false);
  }
  h.local.set(PRODUCT_KEY, JSON.stringify({ ...good, geographic: { ...good.geographic, foundup_id: 'another' } }));
  assert.equal(h.api.restore(), false);
  assert.equal(h.local.get(VIDEO_KEY), 'preserve-video');
  assert.equal(h.calls.length, 0);
});

await check('early or empty product load cannot erase a saved position', () => {
  const h = stateRuntime();
  h.api.selectProduct('move2japan');
  h.api.save();
  const saved = h.local.get(PRODUCT_KEY);
  h.tf.geographic = null;
  h.api.save();
  assert.equal(h.local.get(PRODUCT_KEY), saved);
  h.win.mallTileField = null;
  h.api.save();
  assert.equal(h.local.get(PRODUCT_KEY), saved);
});

await check('one dynamic-row capture listener saves product state only', () => {
  const h = stateRuntime();
  h.api.selectProduct('move2japan');
  h.api.bindAutoSave();
  h.api.bindAutoSave();
  assert.equal(h.events.scroll.length, 1);
  h.fire('scroll', { target: { matches: selector => selector === '.mall-field-group-track' } });
  h.flush();
  assert.equal(h.local.has(PRODUCT_KEY), true);
  assert.equal(h.local.has(VIDEO_KEY), false);
});

await check('explicit account handoff retains safe filters and a fixed destination', () => {
  const h = stateRuntime(ORIGIN + '/member/?foundup=move2japan&q=river&country=jp&area=Wakasa&locality=%E5%AE%89%E8%B3%80%E9%87%8C&max=1e6&land=with_land&sort=land_desc&group=locality&large=1&tour=1&next=https%3A%2F%2Fevil.test&return_url=%2F%2Fevil.test');
  assert.equal(h.api.rememberProductReturn('move2japan'), false, 'must select the actual product first');
  h.api.selectProduct('move2japan');
  assert.equal(h.api.rememberProductReturn('move2japan'), true);
  const path = h.api.consumeProductReturn();
  const url = new URL(path, ORIGIN);
  assert.equal(url.origin, ORIGIN);
  assert.equal(url.pathname, '/member/');
  assert.equal(url.hash, '#account');
  assert.equal(url.searchParams.get('foundup'), 'move2japan');
  assert.equal(url.searchParams.get('country'), 'JP');
  assert.equal(url.searchParams.get('city'), 'Wakasa');
  assert.equal(url.searchParams.get('max'), '1000000');
  assert.equal(url.searchParams.has('next'), false);
  assert.equal(url.searchParams.has('return_url'), false);
  assert.equal(url.searchParams.has('area'), false);
  assert.equal(h.api.consumeProductReturn(), null, 'one use only');
});

await check('return rejects wrong routes, duplicate product selection and unsafe values', () => {
  for (const suffix of ['/member/private', '/?foundup=move2japan', '/member/?foundup=other', '/member/?foundup=move2japan&foundup=other']) {
    const h = stateRuntime(ORIGIN + suffix);
    h.api.selectProduct('move2japan');
    assert.equal(h.api.rememberProductReturn('move2japan'), false);
    assert.equal(h.session.size, 0);
  }
  const h = stateRuntime(ORIGIN + '/member/index.html?foundup=move2japan&city=A&city=B&max=Infinity&land=private&country=evil.test&group=script&tour=2');
  h.api.selectProduct('move2japan');
  assert.equal(h.api.rememberProductReturn('move2japan'), true);
  assert.equal(h.api.consumeProductReturn(), '/member/?foundup=move2japan#account');
});

await check('return expires, refuses future/tampered records and consumes failed records', () => {
  const h = stateRuntime();
  const valid = { product_id: 'move2japan', created_at: 1000000, filters: {} };
  const cases = [
    { ...valid, created_at: 1 },
    { ...valid, created_at: 1000001 },
    { ...valid, product_id: 'other' },
    { ...valid, return_url: 'https://evil.test' },
    { ...valid, filters: { next: 'https://evil.test' } },
    { ...valid, filters: [] }
  ];
  for (const record of cases) {
    h.session.set(RETURN_KEY, JSON.stringify(record));
    assert.equal(h.api.consumeProductReturn(), null);
    assert.equal(h.session.has(RETURN_KEY), false);
  }
  h.session.set(RETURN_KEY, JSON.stringify(valid));
  h.time(1900001);
  assert.equal(h.api.consumeProductReturn(), null);
});

await check('unavailable browser storage does not block discovery or admission', () => {
  const h = stateRuntime();
  const fail = () => { throw new Error('storage disabled'); };
  h.context.localStorage.getItem = h.context.localStorage.setItem = h.context.localStorage.removeItem = fail;
  h.context.sessionStorage.getItem = h.context.sessionStorage.setItem = h.context.sessionStorage.removeItem = fail;
  h.api.selectProduct('move2japan');
  assert.doesNotThrow(() => h.api.save());
  assert.equal(h.api.restore(), false);
  assert.equal(h.api.rememberProductReturn('move2japan'), false);
  assert.equal(h.api.consumeProductReturn(), null);
});

await check('ordinary query scope and unfiltered restore retain upstream category behavior', () => {
  const h = stateRuntime();
  h.tf.scope = { type: 'query', query: 'show me houses' };
  h.tf.layout = 'grid';
  h.api.save();
  h.tf.scope = null;
  h.api.restore();
  h.flushFrames();
  assert.deepEqual(copy(h.tf.scope), { type: 'query', query: 'show me houses' });
  assert.equal(h.tf.layout, 'grid');
  assert.deepEqual(copy(h.tf.offsets), { travel: 180, music: 30 });

  h.tf.scope = null;
  h.api.save();
  h.tf.scope = { type: 'query', query: 'cars' };
  h.calls.length = 0;
  h.api.restore();
  h.flushFrames();
  assert.equal(h.tf.scope, null);
  assert.equal(h.calls.some(call => call[0] === 'clear'), true);
  assert.equal(h.calls.some(call => call[0] === 'scope'), false);

  h.api.bindAutoSave();
  const binding = h.bindings.find(item => item.kind === 'wrapper:scroll');
  assert.equal(binding.options.capture, true);
  h.tf.offsets.travel = 290;
  h.fire('wrapper:scroll', { target: h.wrapper });
  h.flush();
  assert.equal(JSON.parse(h.local.get(VIDEO_KEY)).rowOffsets.travel, 290);
  assert.equal(h.local.has(PRODUCT_KEY), false);
});

await check('deferred video restoration cannot overwrite a newly selected geographic product', () => {
  const h = stateRuntime();
  h.api.save();
  h.api.restore();
  h.api.selectProduct('move2japan');
  h.api.save();
  h.calls.length = 0;
  h.wrapper.scrollTop = 330;
  h.api.restore();
  h.flushFrames();
  assert.deepEqual(h.calls.map(call => call[0]), ['geo']);
  assert.equal(h.wrapper.scrollTop, 330);
});

// Browser-owned cache/fetch interfaces are bounded in memory; the listeners
// under test execute the actual service-worker source above.
function swRuntime(source = swSource) {
  const handlers = new Map(), stores = new Map(), deleted = [], precached = [], calls = [];
  const keyOf = key => new URL(typeof key === 'string' ? key : key.url, ORIGIN).href;
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const entries = stores.get(name);
      return {
        async match(key) { return entries.get(keyOf(key))?.clone(); },
        async put(key, response) { entries.set(keyOf(key), response.clone()); },
        async addAll(requests) {
          precached.push(...requests);
          for (const request of requests) {
            const url = new URL(keyOf(request));
            const path = url.pathname + url.search;
            entries.set(keyOf(path), new Response(path === '/member/' ? 'public /member/' : 'public ' + path, {
              headers: { 'Content-Type': path === '/member/' ? 'text/html' : 'text/plain' }
            }));
          }
        },
        async keys() { return [...entries.keys()].map(url => ({ url })); },
        async delete(key) { return entries.delete(keyOf(key)); }
      };
    },
    async keys() { return [...stores.keys()]; },
    async delete(name) { deleted.push(name); return stores.delete(name); }
  };
  let network = async () => new Response('public /member/', { headers: { 'Content-Type': 'text/html' } });
  const context = {
    self: {
      location: { origin: ORIGIN },
      addEventListener: (kind, handler) => handlers.set(kind, handler),
      skipWaiting: () => Promise.resolve(),
      clients: { claim: () => Promise.resolve() }
    },
    URL, Request, Response, Headers, caches,
    fetch: (request, options = {}) => {
      calls.push({ request: typeof request === 'string' ? request : request.url, options: copy(options) });
      return Promise.resolve().then(() => network(request, options));
    }
  };
  runInNewContext(source, context);
  return {
    caches, stores, deleted, precached, calls,
    setNetwork: callback => { network = callback; },
    async event(kind) {
      const waiting = [];
      handlers.get(kind)({ waitUntil: promise => waiting.push(promise) });
      await Promise.all(waiting);
    },
    async request(path, options = {}) {
      let response, intercepted = false;
      const request = { url: new URL(path, ORIGIN).href, method: 'GET', mode: 'cors', ...options };
      handlers.get('fetch')({
        request,
        respondWith: promise => {
          assert.equal(intercepted, false, 'each request is intercepted at most once');
          intercepted = true;
          response = promise;
        }
      });
      return { intercepted, response: intercepted ? await response : undefined };
    }
  };
}

await check('install reloads only explicit public shell and product assets', async () => {
  const h = swRuntime();
  await h.event('install');
  const installed = h.precached.map(request => {
    const url = new URL(request.url);
    assert.equal(url.origin, ORIGIN);
    assert.equal(request.cache, 'reload');
    assert.equal(request.credentials, 'omit');
    return url.pathname + url.search;
  });
  for (const path of ['/member/js/mall-tile-field.js?v=26', '/member/js/mall-video-player.js?v=26', '/member/js/mall-video-projection.js?v=26', '/member/js/mall-state-restore.js?v=26', '/member/js/mall-planes.js?v=26', '/member/js/mall-discovery-pager.js?v=26', '/logo-foundups.svg', '/member/hpc-banner.webp', '/member/hpc.webmanifest', '/member/hpc-icon-180.png', '/member/hpc-icon-192.png', '/member/hpc-icon-512.png', '/move2japan/property-search.js', '/move2japan/move2japan.css']) {
    assert.equal(installed.includes(path), true, 'missing precached asset: ' + path);
  }
  assert.equal(installed.includes('/move2japan/properties.json'), false);
  assert.ok(installed.includes('/js/reddog-public-client.js'));
  assert.ok(installed.includes('/js/reddog-fractal-focus.js'));
  assert.equal(installed.includes('/member/js/mall-video-projection.js'), false);
  for (const path of installed.filter(path => /[?&]v=/.test(path))) {
    assert.equal(new URL(path, ORIGIN).searchParams.get('v'), '26',
      'all versioned precache assets must agree with the displayed build: ' + path);
  }
  assert.equal(installed.some(path => path.startsWith('/member/discovery/')), false,
    'install must not fetch the metadata/video page graph');
  assert.equal(h.stores.has('pfmall-member-v26'), true);
  const build = videoProjectionSource.match(/const mallBuild = '(v\d+)';/)?.[1];
  assert.equal('pfmall-member-' + build, 'pfmall-member-v26');
});

await check('activation retires only obsolete caches owned by this Mall', async () => {
  const h = swRuntime();
  const obsoleteVersions = Array.from({ length: 24 }, (_, index) => `pfmall-member-v${index + 2}`);
  for (const name of [...obsoleteVersions, 'pfmall-member-v26', 'pfmall-properties-v1',
    'pfmall-posters-v1', 'gotjunk-offline-v1', 'other-app-cache']) {
    await h.caches.open(name);
  }
  await h.event('activate');
  assert.deepEqual(h.deleted.sort(), obsoleteVersions.sort());
  assert.equal(h.stores.has('pfmall-member-v20'), false);
  assert.equal(h.stores.has('pfmall-member-v21'), false);
  assert.equal(h.stores.has('pfmall-member-v22'), false);
  assert.equal(h.stores.has('pfmall-member-v23'), false);
  assert.equal(h.stores.has('pfmall-member-v24'), false);
  assert.equal(h.stores.has('pfmall-member-v26'), true);
  assert.equal(h.stores.has('gotjunk-offline-v1'), true);
  assert.equal(h.stores.has('other-app-cache'), true);
});

await check('property catalog is network-first and retains observed source bytes offline', async () => {
  const h = swRuntime();
  const raw = '{"foundup_id":"move2japan","observed_on":"2026-10-17","properties":[]}';
  h.setNetwork(async () => new Response(raw, { headers: { 'Content-Type': 'application/json' } }));
  const online = await h.request('/move2japan/properties.json');
  assert.equal(online.intercepted, true);
  assert.equal(await online.response.text(), raw);
  assert.equal(h.calls[0].options.credentials, 'omit');
  assert.equal(h.calls[0].options.cache, 'no-cache');
  h.setNetwork(async () => { throw new Error('offline'); });
  const offline = await h.request('/move2japan/properties.json');
  assert.equal(await offline.response.text(), raw);
  assert.equal(h.calls.length, 2);
});

await check('hosting HTML fallback cannot poison the public property catalog cache', async () => {
  const h = swRuntime();
  h.setNetwork(async () => new Response('<html>Hosting fallback</html>', { headers: { 'Content-Type': 'text/html' } }));
  const result = await h.request('/move2japan/properties.json');
  assert.equal(result.response.status, 503);
  const cache = await h.caches.open('pfmall-properties-v1');
  assert.equal(await cache.match('/move2japan/properties.json'), undefined);
});

await check('product navigation shares one static member shell without query cache keys', async () => {
  const h = swRuntime();
  await h.event('install');
  const online = await h.request('/member/?foundup=move2japan&city=Wakasa&account=1', { mode: 'navigate' });
  assert.equal(online.response.status, 200);
  assert.equal(h.calls.at(-1).request, '/member/');
  assert.equal(h.calls.at(-1).options.credentials, 'omit');
  const cache = await h.caches.open('pfmall-member-v26');
  assert.equal((await cache.keys()).some(key => {
    const url = new URL(key.url);
    return url.pathname === '/member/' && !!url.search;
  }), false);
  h.setNetwork(async () => { throw new Error('offline'); });
  const offline = await h.request('/member/?foundup=move2japan&q=clerk.accounts.dev', { mode: 'navigate' });
  assert.equal(offline.intercepted, true, 'a filter value is not an authentication path');
  assert.match(await offline.response.text(), /public \/member\//);
});

await check('private routes, query assets, foreign origins and non-GET remain unintercepted', async () => {
  const h = swRuntime();
  for (const path of [
    '/member/private.json', '/member/api/profile', '/member/account?token=secret',
    '/member/js/account-concierge.js?token=secret',
    '/move2japan/properties.json?private=1',
    'https://evil.test/member/mall-video-catalog.json',
    'https://clerk.example/member/'
  ]) {
    assert.equal((await h.request(path)).intercepted, false, path);
  }
  assert.equal((await h.request('/member/private', { mode: 'navigate' })).intercepted, false);
  assert.equal((await h.request('/move2japan/properties.json', { method: 'POST' })).intercepted, false);
  assert.equal(h.calls.length, 0);
});

await check('declared static assets keep cache-first behavior and video fallback stays explicit', async () => {
  const h = swRuntime();
  const first = await h.request('/member/js/mall-tile-field.js?v=26');
  const body = await first.response.text();
  assert.equal(h.calls.length, 1);
  h.setNetwork(async () => { throw new Error('offline'); });
  const cached = await h.request('/member/js/mall-tile-field.js?v=26');
  assert.equal(await cached.response.text(), body);
  assert.equal(h.calls.length, 1);
  const video = await h.request('/member/mall-video-catalog.json');
  assert.equal(await video.response.text(), '[]');
  assert.equal(video.response.headers.get('X-Offline-Fallback'), '1');
});

await check('scoped catalog has a separate cache key and no fallback to the member catalog', async () => {
  const h = swRuntime();
  const scoped = '/member/mall-public-video-catalog.json';
  const raw = '{"hpc":{"lane":{"foundup_id":"hpc"}}}';
  h.setNetwork(async () => new Response(raw, { headers: { 'Content-Type': 'application/json' } }));
  assert.equal(await (await h.request(scoped)).response.text(), raw);
  assert.equal(h.calls.at(-1).options.credentials, 'omit');
  h.setNetwork(async () => { throw new Error('offline'); });
  assert.equal(await (await h.request(scoped)).response.text(), raw);
  assert.equal(await (await h.request('/member/mall-video-catalog.json')).response.text(), '[]');
  const uncached = swRuntime();
  uncached.setNetwork(async () => { throw new Error('offline'); });
  assert.equal((await uncached.request(scoped)).response.status, 503);
  assert.equal((await h.request('/member/js/mall-tile-field.js?v=unrecognized')).intercepted, false);
});

await check('public discovery caches only requested generation-bound pages and retains exact offline bytes', async () => {
  const h = swRuntime();
  const generation = 'a'.repeat(64);
  const root = '/member/discovery/catalog.json';
  const selected = `/member/discovery/${generation}/videos/move2japan/catalog/0000.json`;
  const unread = `/member/discovery/${generation}/videos/move2japan/catalog/0001.json`;
  const newer = `/member/discovery/${'b'.repeat(64)}/videos/move2japan/catalog/0000.json`;
  const raw = new Map([
    [root, JSON.stringify({ schema_version: 1, generation, kind: 'catalog', items: [{ foundup_id: 'move2japan' }] })],
    [selected, JSON.stringify({ schema_version: 1, generation, kind: 'videos', record_id: 'move2japan', items: [{ video_id: 'fixture0001', title: 'Controlled page bytes' }] })]
  ]);
  h.setNetwork(async request => {
    const path = new URL(typeof request === 'string' ? request : request.url, ORIGIN).pathname;
    assert.equal(raw.has(path), true, 'no unrelated page may be fetched');
    return new Response(raw.get(path), { headers: { 'Content-Type': 'application/json' } });
  });
  for (const path of [root, selected]) {
    const result = await h.request(path);
    assert.equal(result.intercepted, true);
    assert.equal(await result.response.text(), raw.get(path));
    assert.deepEqual(h.calls.at(-1).options, { cache: 'no-cache', credentials: 'omit' });
  }
  assert.equal(h.calls.length, 2, 'requesting two pages must not prefetch successors');
  const cache = await h.caches.open('pfmall-member-v26');
  assert.deepEqual((await cache.keys()).map(x => new URL(x.url).pathname).sort(), [root, selected].sort());
  h.setNetwork(async () => { throw new Error('offline fixture'); });
  for (const path of [root, selected]) {
    assert.equal(await (await h.request(path)).response.text(), raw.get(path));
  }
  for (const path of [unread, newer]) {
    const result = await h.request(path);
    assert.equal(result.response.status, 503);
    assert.equal(result.response.headers.get('X-Offline-Fallback'), '1');
    assert.deepEqual(await result.response.json(), { error: 'public_discovery_page_unavailable' });
    assert.equal(await cache.match(path), undefined, 'a failure must not become catalog data');
  }
});

await check('public discovery rejects hosting fallbacks and leaves queries/private or foreign requests unintercepted', async () => {
  const h = swRuntime();
  const root = '/member/discovery/catalog.json';
  // An old raw catalog must never substitute for an unread bounded page.
  h.setNetwork(async () => new Response('[]', { headers: { 'Content-Type': 'application/json' } }));
  await h.request('/member/mall-video-catalog.json');
  h.setNetwork(async () => new Response('<html>Hosting fallback</html>', { headers: { 'Content-Type': 'text/html' } }));
  const html = await h.request(root);
  assert.equal(html.response.status, 503);
  assert.notEqual(await html.response.text(), '[]');
  const cache = await h.caches.open('pfmall-member-v26');
  assert.equal(await cache.match(root), undefined);
  h.setNetwork(async () => { throw new Error('offline fixture'); });
  assert.equal((await h.request(root)).response.status, 503);
  for (const path of [root + '?private=1', 'https://foreign.test' + root,
    '/member/discovery/invalid/catalog/0000.json',
    `/member/discovery/${'a'.repeat(64)}/videos/unsafe%2fidentity/catalog/0000.json`]) {
    assert.equal((await h.request(path)).intercepted, false, path);
  }
  assert.equal((await h.request(root, { method: 'POST' })).intercepted, false);
});

await check('normal Mall round-trips source_group fieldScope in localStorage', () => {
  const h = stateRuntime(ORIGIN + '/member/');
  h.tf.scope = { type: 'source_group', query: 'apps' };
  h.api.save();
  const saved = JSON.parse(h.local.get(VIDEO_KEY));
  assert.deepEqual(saved.fieldScope, { type: 'source_group', query: 'apps' });
  h.calls.length = 0;
  h.tf.scope = null;
  assert.equal(h.api.restore(), true);
  assert.deepEqual(h.calls.find(c => c[0] === 'scope'), ['scope', { type: 'source_group', query: 'apps' }]);
});

await check('ordinary Mall persists and restores activeVideo without touching HPC sessionStorage', () => {
  const h = stateRuntime(ORIGIN + '/member/');
  let active = { foundupId: 'move2japan', videoId: 'vid_m2j_01', queueQuery: 'onsen' };
  const restoredVideos = [];
  h.tf.getActiveVideo = () => active;
  h.tf.restoreActiveVideo = value => { restoredVideos.push(copy(value)); return true; };
  h.api.save();
  const saved = JSON.parse(h.local.get(VIDEO_KEY));
  assert.deepEqual(saved.activeVideo, active);
  assert.equal(h.session.size, 0, 'ordinary Mall activeVideo must never write to sessionStorage');

  active = null;
  assert.equal(h.api.restore(), true);
  assert.equal(restoredVideos.length, 0, 'activeVideo restores on animation frame after layout');
  h.flushFrames();
  assert.deepEqual(restoredVideos, [{ foundupId: 'move2japan', videoId: 'vid_m2j_01', queueQuery: 'onsen' }]);

  // Malformed activeVideo payloads are rejected and cleared
  for (const bad of [
    { foundupId: '../bad', videoId: 'vid_1', queueQuery: '' },
    { foundupId: 'move2japan', videoId: '', queueQuery: '' },
    { foundupId: 'move2japan', videoId: 'vid_1', queueQuery: 'x'.repeat(301) },
    { foundupId: 'move2japan', videoId: 'vid_1', extra: 1 }
  ]) {
    h.local.set(VIDEO_KEY, JSON.stringify({ projection: 'default', activeVideo: bad }));
    assert.equal(h.api.restore(), false);
    assert.equal(h.local.has(VIDEO_KEY), false);
  }

  // HPC sessionStorage contract strictly rejects activeVideo mixed into scoped state
  const hpc = stateRuntime(ORIGIN + '/member/?foundup=hpc');
  assert.equal(hpc.api.selectVideoScope('hpc'), true);
  hpc.session.set('pfmall_video_scope_hpc_v1', JSON.stringify({
    scrollTop: 20, scrollLeft: 0, activeVideo: { foundupId: 'hpc', videoId: 'HPC01', queueQuery: '' }
  }));
  assert.equal(hpc.api.restore(), false);
  assert.equal(hpc.session.has('pfmall_video_scope_hpc_v1'), false);
});

await check('Play public details and same-host sign-in remain distinct', () => {
  const window = { location: new URL(ORIGIN) };
  runInNewContext(videoProjectionSource, { window, URLSearchParams });
  const route = window.mallVideoProjection;
  assert.equal(route.hostScope(new URL('https://play.foundups.com/')), 'mall');
  assert.equal(route.isOpenMallHost(new URL('https://play.foundups.com/member/')), true);
  assert.equal(route.isOpenMallHost(new URL('https://foundups.com/member/')), false);
  assert.equal(route.resolve(new URL('https://play.foundups.com/member/')), 'mall');
  assert.equal(route.resolve(new URL('https://play.foundups.com/member/?foundup=hpc')), 'hpc');
  assert.equal(route.resolve(new URL('https://play.foundups.com/member/?foundup=move2japan')), null);
  assert.equal(route.resolveMember(new URL('https://play.foundups.com/member/?foundup=hpc')), null);
  assert.equal(route.memberPortalUrl('gotjunk_001'), 'https://play.foundups.com/member/foundup.html?id=gotjunk_001');
  assert.equal(route.memberPortalUrl('../evil'), 'https://play.foundups.com/?signin=required');
  assert.equal(route.resolveMemberEntry(new URL('https://foundups.com/member/?enter=gotjunk_001')), 'gotjunk_001');
  assert.equal(route.resolveMemberEntry(new URL('https://play.foundups.com/member/?enter=gotjunk_001')), null);
  assert.equal(route.resolveMemberEntry(new URL('https://foundups.com/member/?enter=__proto__')), null);
  assert.equal(route.canonicalEntryId({ foundup_id: 'antifafm', canonical_foundup_id: 'antifafm_001' }), 'antifafm_001');
  assert.equal(route.canonicalEntryId({ foundup_id: 'science_swarm', canonical_foundup_id: 'science_swarm_hub' }), 'science_swarm_hub');
  assert.equal(route.canonicalEntryId({ foundup_id: 'undaodu', canonical_foundup_id: null }), null);
  assert.equal(route.canonicalEntryId({ foundup_id: 'foundups_house_project', canonical_foundup_id: null, discovery_kind: 'candidate' }), null);
  assert.equal(route.canonicalEntryId({ foundup_id: 'legacy_identity' }), 'legacy_identity');
  assert.equal(route.canonicalEntryId({ id: 'legacy_id' }), 'legacy_id');
  for (const invalid of ['', '../evil', '__proto__', 'constructor', 'prototype', undefined, {}, 42]) {
    assert.equal(route.canonicalEntryId({ foundup_id: 'must_not_fallback', canonical_foundup_id: invalid }), null);
  }
  assert.equal(route.canonicalEntryId(null), null);

  const entryHandoff = stateRuntime(ORIGIN + '/member/?enter=gotjunk_001');
  assert.equal(entryHandoff.api.rememberMemberVideoReturn(), true);
  const record = JSON.parse(entryHandoff.session.get(RETURN_KEY));
  assert.deepEqual(record, { product_id: 'enter', created_at: 1000000, filters: { enter: 'gotjunk_001' } });
  assert.equal(entryHandoff.api.consumeProductReturn(), '/member/foundup.html?id=gotjunk_001');
  assert.equal(entryHandoff.api.consumeProductReturn(), null);
  entryHandoff.session.set(RETURN_KEY, JSON.stringify({ product_id: 'enter', created_at: 1000000, filters: { enter: '../evil' } }));
  assert.equal(entryHandoff.api.consumeProductReturn(), null);
});

await check('root activation retires only obsolete numeric root caches and preserves foreign sentinel bytes', async () => {
  const current = rootSwSource.match(/const CACHE_NAME = ['"]([^'"]+)['"]/)?.[1];
  assert.match(current || '', /^foundups-root-v\d+$/);
  const h = swRuntime(rootSwSource);
  const survivors = [current, 'pfmall-member-v23', 'pfmall-posters-v1', 'pfmall-properties-v1',
    'other-app-cache', 'foundups-root-vX', 'foundups-root-v1-extra', 'foundups-root', 'FOUNDUPS-root-v1'];
  const sentinel = new Uint8Array([0, 255, 10, 34, 92, 127]);
  const key = '/__cache_owner_fixture__/sentinel';
  for (const name of survivors) {
    const cache = await h.caches.open(name);
    await cache.put(key, new Response(sentinel));
  }
  const obsolete = ['foundups-root-v0', 'foundups-root-v1', 'foundups-root-v3', 'foundups-root-v27']
    .filter(name => name !== current);
  for (const name of obsolete) await h.caches.open(name);
  await h.event('activate');
  // Ownership and bytes are the regression: checking v2 first would mask the
  // baseline's destructive deletion of other applications' cache namespaces.
  for (const name of survivors) {
    assert.equal(h.stores.has(name), true, 'root activation deleted foreign/current cache: ' + name);
    const response = await (await h.caches.open(name)).match(key);
    assert.ok(response, 'missing sentinel in ' + name);
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), sentinel, 'changed bytes in ' + name);
  }
  assert.deepEqual(h.deleted.slice().sort(), obsolete.slice().sort());
  assert.equal(h.calls.length, 0, 'activation must not make network calls');
  assert.equal(current, 'foundups-root-v2', 'the repaired root worker must promote its generation');
});

function gatewaySignInRuntime(showButton) {
  const start = gatewayHtml.indexOf('const showSignInModalBtn =');
  const panel = gatewayHtml.indexOf('Panel toggle', start);
  const end = gatewayHtml.lastIndexOf('\n', panel);
  assert.ok(start > 0 && end > start && end - start < 30000, 'bounded actual sign-in section missing');
  const source = gatewayHtml.slice(start, end);
  const nodes = new Map(), calls = [], bindings = [];
  const trace = { auth: 0, network: 0 };
  function node(id) {
    const listeners = new Map();
    const element = {
      id, style: { display: 'initial' },
      addEventListener(kind, fn) {
        (listeners.get(kind) || listeners.set(kind, []).get(kind)).push(fn);
        bindings.push({ id, kind, fn });
      },
      emit(kind, event = {}) {
        const e = { target: element, preventDefault() { calls.push(['prevent', id]); }, ...event };
        for (const fn of listeners.get(kind) || []) fn(e);
      }
    };
    nodes.set(id, element);
    return element;
  }
  for (const id of ['closeSignInModal', 'signInGoogle', 'signInLinkedIn', 'signInError', 'backToDisclaimer']) node(id);
  if (showButton) node('showSignInModal');
  const disclaimerModal = node('disclaimerModal'), signInModal = node('signInModal');
  const forbiddenAuth = () => { trace.auth++; throw new Error('Auth must not execute in this listener-binding fixture'); };
  const context = {
    document: { getElementById: id => nodes.get(id) || null }, disclaimerModal, signInModal,
    openModal: element => { calls.push(['open', element.id]); element.style.display = 'block'; },
    closeModal: element => { calls.push(['close', element.id]); element.style.display = 'none'; },
    signInWithPopup: forbiddenAuth, getDoc: forbiddenAuth, doc: forbiddenAuth,
    navigateToMember: forbiddenAuth, auth: { signOut: forbiddenAuth }, db: {}, googleProvider: {}, linkedinProvider: {},
    fetch: () => { trace.network++; throw new Error('Network forbidden'); }
  };
  runInNewContext(source, context);
  return { nodes, calls, bindings, trace };
}

function verifyGatewayBindings(showButton) {
  for (const id of ['closeSignInModal', 'backToDisclaimer', 'signInGoogle', 'signInLinkedIn',
    'signInError', 'signInModal', 'disclaimerModal']) {
    assert.match(gatewayHtml, new RegExp(`\\bid\\s*=\\s*["']${id}["']`),
      'fixture required node must exist in actual gateway HTML: ' + id);
  }
  const h = gatewaySignInRuntime(showButton);
  for (const id of ['closeSignInModal', 'backToDisclaimer', 'signInGoogle', 'signInLinkedIn']) {
    assert.equal(h.bindings.filter(x => x.id === id && x.kind === 'click').length, 1,
      'later listener must still bind: ' + id);
  }
  h.nodes.get('closeSignInModal').emit('click');
  assert.equal(h.nodes.get('signInModal').style.display, 'none');
  h.nodes.get('backToDisclaimer').emit('click');
  assert.equal(h.nodes.get('disclaimerModal').style.display, 'block');
  assert.equal(h.nodes.get('signInModal').style.display, 'none');
  if (showButton) {
    h.nodes.get('showSignInModal').emit('click');
    assert.equal(h.nodes.get('disclaimerModal').style.display, 'none');
    assert.equal(h.nodes.get('signInModal').style.display, 'block');
    assert.equal(h.bindings.filter(x => x.id === 'showSignInModal' && x.kind === 'click').length, 1);
  }
  assert.equal(h.trace.auth, 0, 'listener initialization/Close/Back must not authenticate');
  assert.equal(h.trace.network, 0);
}

await check('gateway actual sign-in section binds later controls when optional show button is absent', () => {
  assert.doesNotMatch(gatewayHtml, /\bid\s*=\s*['"]showSignInModal['"]/,
    'the absent-button fixture must represent the current actual HTML');
  verifyGatewayBindings(false);
});

await check('gateway present-button positive control opens sign-in and preserves later listeners without auth', () => {
  verifyGatewayBindings(true);
});

console.log('Mall product state and service worker runtime: ' + checks + ' passed.');
