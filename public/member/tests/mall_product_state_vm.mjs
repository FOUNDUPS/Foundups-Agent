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
  const win = { location: { href }, mallTileField: tf, addEventListener: (kind, fn) => add('window:' + kind, fn) };
  const context = {
    window: win, document: doc, localStorage: storage(local), sessionStorage: storage(session),
    URL, URLSearchParams, Date: { now: () => clock },
    requestAnimationFrame: fn => frames.push(fn),
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id)
  };
  runInNewContext(stateSource, context);
  return {
    api: win.mallStateRestore, local, session, calls, events, win, tf, context, wrapper, bindings,
    time: value => { clock = value; },
    flushFrames: () => { for (const fn of frames.splice(0)) fn(); },
    flush: () => { for (const fn of [...timers.values()]) fn(); timers.clear(); },
    fire: (kind, event) => { for (const fn of events[kind] || []) fn(event); }
  };
}

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
function swRuntime() {
  const handlers = new Map(), stores = new Map(), deleted = [], precached = [], calls = [];
  const keyOf = key => new URL(typeof key === 'string' ? key : key.url, ORIGIN).href;
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const entries = stores.get(name);
      return {
        async match(key) { return entries.get(keyOf(key))?.clone(); },
        async put(key, response) { entries.set(keyOf(key), response.clone()); },
        async addAll(paths) {
          precached.push(...paths);
          for (const path of paths) {
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
    URL, Response, Headers, caches,
    fetch: (request, options = {}) => {
      calls.push({ request: typeof request === 'string' ? request : request.url, options: copy(options) });
      return Promise.resolve().then(() => network(request, options));
    }
  };
  runInNewContext(swSource, context);
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

await check('install precaches only explicit shell and product assets', async () => {
  const h = swRuntime();
  await h.event('install');
  for (const path of ['/member/js/mall-tile-field.js', '/move2japan/property-search.js', '/move2japan/move2japan.css']) {
    assert.equal(h.precached.includes(path), true);
  }
  assert.equal(h.precached.includes('/move2japan/properties.json'), false);
  assert.equal(h.precached.every(path => path.startsWith('/')), true);
  assert.equal(h.stores.has('pfmall-member-v4'), true);
});

await check('activation retires only obsolete caches owned by this Mall', async () => {
  const h = swRuntime();
  for (const name of ['pfmall-member-v2', 'pfmall-member-v3', 'pfmall-member-v4', 'pfmall-properties-v1', 'pfmall-posters-v1', 'gotjunk-offline-v1', 'other-app-cache']) {
    await h.caches.open(name);
  }
  await h.event('activate');
  assert.deepEqual(h.deleted.sort(), ['pfmall-member-v2', 'pfmall-member-v3']);
  assert.equal(h.stores.has('pfmall-member-v4'), true);
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
  const cache = await h.caches.open('pfmall-member-v4');
  assert.equal((await cache.keys()).some(key => key.url.includes('?')), false);
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
  const first = await h.request('/member/js/mall-tile-field.js');
  const body = await first.response.text();
  assert.equal(h.calls.length, 1);
  h.setNetwork(async () => { throw new Error('offline'); });
  const cached = await h.request('/member/js/mall-tile-field.js');
  assert.equal(await cached.response.text(), body);
  assert.equal(h.calls.length, 1);
  const video = await h.request('/member/mall-video-catalog.json');
  assert.equal(await video.response.text(), '[]');
  assert.equal(video.response.headers.get('X-Offline-Fallback'), '1');
});

console.log('Mall product state and service worker runtime: ' + checks + ' passed.');
