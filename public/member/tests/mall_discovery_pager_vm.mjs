/** Actual pager execution with controlled HTTP responses; no remote/provider/device claims. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const memberRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(memberRoot, 'js/mall-discovery-pager.js'), 'utf8');
const ROOT = '/member/discovery/';
const GEN = 'a'.repeat(64);
const origin = 'https://preview.example';
const copy = value => JSON.parse(JSON.stringify(value));
const flush = () => new Promise(done => setImmediate(done));
let checks = 0;

async function check(name, fn) {
  await fn();
  checks++;
  console.log('PASS ' + name);
}

function path(kind, id, page, generation = GEN) {
  return ROOT + generation + '/' + (kind === 'catalog' ? 'catalog/' : 'videos/' + id + '/catalog/') +
    String(page).padStart(4, '0') + '.json';
}

function record(index, videoCount = 13, generation = GEN) {
  const id = 'lane_' + index;
  return {
    foundup_id: id, canonical_foundup_id: null, title: 'Source ' + index,
    video_count: videoCount, available_orders: ['catalog'],
    video_pages: { catalog: videoCount ? path('videos', id, 0, generation) : null }
  };
}

function page(kind = 'catalog', number = 0, total = 13, id = null, generation = GEN) {
  const offset = number * 6;
  const length = Math.min(6, Math.max(0, total - offset));
  const result = {
    schema_version: 1, generation, kind, record_id: id, order: 'catalog',
    page: number, page_size: 6, total,
    items: Array.from({ length }, (_, index) => kind === 'catalog'
      ? record(offset + index, 13, generation)
      : { video_id: String(offset + index).padStart(11, '0'), title: id + ' video ' + (offset + index) }),
    next: offset + length < total ? path(kind, id, number + 1, generation) : null
  };
  if (kind === 'videos') result.available_orders = ['catalog'];
  return result;
}

function response(data, options = {}) {
  return {
    ok: options.ok ?? true, redirected: options.redirected ?? false, url: options.url ?? '',
    headers: { get: key => key.toLowerCase() === 'content-type' ? options.mime ?? 'application/json; charset=utf-8' : null },
    json: options.json || (async () => copy(data))
  };
}

function deferred() {
  let resolvePromise, reject;
  const promise = new Promise((yes, no) => { resolvePromise = yes; reject = no; });
  return { promise, resolve: resolvePromise, reject };
}

function runtime() {
  const routes = new Map();
  const requests = [];
  const win = {
    location: new URL(origin + '/member/'),
    fetch: async (target, options) => {
      requests.push({ target, options });
      assert.equal(options.credentials, 'omit');
      assert.equal(options.redirect, 'error');
      assert.equal(options.cache, 'no-store');
      assert.ok(options.signal instanceof AbortSignal);
      assert.ok(target.startsWith(ROOT), 'Never request a legacy full catalog');
      if (!routes.has(target)) throw new Error('Unexpected request: ' + target);
      const entry = routes.get(target);
      return typeof entry === 'function' ? entry(target, options) : response(entry);
    }
  };
  runInNewContext(source, { window: win, URL, AbortController, DOMException });
  return { api: win.mallDiscoveryPager, routes, requests };
}

function catalogRuntime() {
  const h = runtime();
  h.routes.set(ROOT + 'catalog.json', page());
  h.routes.set(path('catalog', null, 1), page('catalog', 1));
  h.routes.set(path('catalog', null, 2), page('catalog', 2));
  return h;
}

await check('catalog boot fetches only six records; explicit loads fetch one sequential batch each', async () => {
  const h = catalogRuntime();
  const session = await h.api.openCatalog();
  assert.equal(h.requests.length, 1);
  assert.equal(session.items.length, 6);
  assert.equal(session.total, 13);
  await flush();
  assert.equal(h.requests.length, 1, 'No eager next-page fetch');
  assert.equal((await session.loadNext()).length, 6);
  assert.equal(session.items.length, 6, 'Initial snapshot is not appended by the pager');
  assert.equal((await session.loadNext()).length, 1);
  assert.equal(session.hasMore, false);
  assert.equal((await session.loadNext()).length, 0);
  assert.deepEqual(h.requests.map(request => request.target), [
    ROOT + 'catalog.json', path('catalog', null, 1), path('catalog', null, 2)
  ]);
  session.close();
});

await check('video browsing requests only the selected record, never other lanes or the full catalog', async () => {
  const h = runtime();
  h.routes.set(path('videos', 'lane_7', 0), page('videos', 0, 13, 'lane_7'));
  h.routes.set(path('videos', 'lane_7', 1), page('videos', 1, 13, 'lane_7'));
  const session = await h.api.openVideos(record(7), 'catalog');
  assert.equal(h.requests.length, 1);
  assert.equal(session.items.length, 6);
  assert.equal((await session.loadNext()).length, 6);
  assert.ok(h.requests.every(request => request.target.includes('/videos/lane_7/catalog/')));
  assert.equal(session.availableOrders.join(','), 'catalog');
  session.close();
});

await check('concurrent loadNext calls share one request and advance the cursor once', async () => {
  const h = catalogRuntime();
  const pending = deferred();
  h.routes.set(path('catalog', null, 1), () => pending.promise);
  const session = await h.api.openCatalog();
  const one = session.loadNext();
  const two = session.loadNext();
  assert.equal(one, two);
  assert.equal(h.requests.length, 2);
  pending.resolve(response(page('catalog', 1)));
  assert.equal((await one).length, 6);
  assert.equal((await session.loadNext()).length, 1);
  assert.equal(h.requests.length, 3);
  session.close();
});

await check('failed HTTP and invalid JSON responses retry the same cursor without discarding loaded state', async () => {
  const h = catalogRuntime();
  const target = path('catalog', null, 1);
  const session = await h.api.openCatalog();
  h.routes.set(target, () => response(null, { ok: false }));
  await assert.rejects(session.loadNext());
  assert.equal(session.hasMore, true);
  h.routes.set(target, () => response(null, { json: async () => { throw new SyntaxError('Bad JSON'); } }));
  await assert.rejects(session.loadNext());
  h.routes.set(target, page('catalog', 1));
  assert.equal((await session.loadNext()).length, 6);
  assert.equal(session.items.length, 6);
  assert.deepEqual(h.requests.slice(1).map(request => request.target), [target, target, target]);
  session.close();
});

await check('forged next URLs are refused before any follow-up request', async () => {
  const attacks = [
    'https://evil.example/steal', '//evil.example/steal',
    ROOT + GEN + '/catalog/0002.json', ROOT + GEN + '/catalog/../0001.json',
    path('catalog', null, 1) + '?credential=secret', path('catalog', null, 1) + '#fragment',
    ROOT + '%2e%2e/private.json', ROOT + GEN + '\\catalog\\0001.json'
  ];
  for (const next of attacks) {
    const h = catalogRuntime();
    h.routes.set(ROOT + 'catalog.json', { ...page(), next });
    await assert.rejects(h.api.openCatalog());
    assert.equal(h.requests.length, 1);
  }
});

await check('next pages must retain generation, kind, record, order, total, exact batch size and sequence', async () => {
  const mutations = [
    value => { value.generation = 'b'.repeat(64); },
    value => { value.kind = 'catalog'; },
    value => { value.record_id = 'lane_8'; },
    value => { value.order = 'popular'; },
    value => { value.available_orders = ['catalog', 'popular']; },
    value => { value.total = 14; },
    value => { value.total = 12; },
    value => { value.page = 2; },
    value => { value.page_size = 7; },
    value => { value.items.push({ video_id: 'extra000000', title: 'Extra' }); },
    value => { value.items.pop(); },
    value => { value.next = null; },
    value => { value.next = path('videos', 'lane_7', 3); }
  ];
  for (const mutate of mutations) {
    const h = runtime();
    const first = path('videos', 'lane_7', 0);
    const next = path('videos', 'lane_7', 1);
    h.routes.set(first, page('videos', 0, 13, 'lane_7'));
    const bad = page('videos', 1, 13, 'lane_7');
    mutate(bad);
    h.routes.set(next, bad);
    const session = await h.api.openVideos(record(7), 'catalog');
    await assert.rejects(session.loadNext());
    assert.equal(session.hasMore, true);
    h.routes.set(next, page('videos', 1, 13, 'lane_7'));
    assert.equal((await session.loadNext()).length, 6, 'Invalid data must not poison retry identity tracking');
    session.close();
  }
});

await check('duplicate video IDs across loaded pages are rejected and remain retryable', async () => {
  const h = runtime();
  h.routes.set(path('videos', 'lane_0', 0), page('videos', 0, 13, 'lane_0'));
  const second = page('videos', 1, 13, 'lane_0');
  second.items[0].video_id = '00000000000';
  h.routes.set(path('videos', 'lane_0', 1), second);
  const session = await h.api.openVideos(record(0));
  await assert.rejects(session.loadNext(), /identity/);
  h.routes.set(path('videos', 'lane_0', 1), page('videos', 1, 13, 'lane_0'));
  assert.equal((await session.loadNext()).length, 6);
  session.close();
});

await check('metadata cannot repeat record identities, expose nested videos/runtime fields, or forge video pointers', async () => {
  const changes = [
    data => { data.items[1].foundup_id = data.items[0].foundup_id; },
    data => { data.items[0].foundup_id = 'CONSTRUCTOR'; },
    data => { data.items[0].videos = []; },
    data => { data.items[0].creator_id = 'private'; },
    data => { data.items[0].data_namespace = 'private'; },
    data => { data.items[0].entry_url = '/private'; },
    data => { data.items[0].video_pages.catalog = path('videos', 'lane_9', 0); },
    data => { data.items[0].available_orders = ['popular']; }
  ];
  for (const mutate of changes) {
    const h = catalogRuntime();
    const invalid = page();
    mutate(invalid);
    h.routes.set(ROOT + 'catalog.json', invalid);
    await assert.rejects(h.api.openCatalog());
    assert.equal(h.requests.length, 1);
  }
  const h = catalogRuntime();
  const session = await h.api.openCatalog();
  const second = page('catalog', 1);
  second.items[0] = { ...record(0), foundup_id: 'LANE_0', video_pages: { catalog: path('videos', 'LANE_0', 0) } };
  h.routes.set(path('catalog', null, 1), second);
  await assert.rejects(session.loadNext(), /metadata/);
  session.close();
});

await check('close aborts the request and rejects late fetch/body completions without another request', async () => {
  for (const delayedBody of [false, true]) {
    const h = catalogRuntime();
    const pending = deferred();
    const next = path('catalog', null, 1);
    h.routes.set(next, () => delayedBody
      ? response(null, { json: () => pending.promise }) : pending.promise);
    const session = await h.api.openCatalog();
    const loading = session.loadNext();
    await flush();
    session.close();
    assert.equal(h.requests[1].options.signal.aborted, true);
    pending.resolve(delayedBody ? page('catalog', 1) : response(page('catalog', 1)));
    await assert.rejects(loading, { name: 'AbortError' });
    assert.equal(session.hasMore, false);
    await assert.rejects(session.loadNext(), { name: 'AbortError' });
    assert.equal(h.requests.length, 2);
    session.close();
  }
});

await check('optional external AbortSignal cancels a pending initial scope and pre-aborted signals do not fetch', async () => {
  const h = catalogRuntime();
  const pending = deferred();
  h.routes.set(ROOT + 'catalog.json', () => pending.promise);
  const controller = new AbortController();
  const opening = h.api.openCatalog({ signal: controller.signal });
  controller.abort();
  assert.equal(h.requests[0].options.signal.aborted, true);
  pending.resolve(response(page()));
  await assert.rejects(opening, { name: 'AbortError' });
  const none = runtime();
  await assert.rejects(none.api.openCatalog({ signal: controller.signal }), { name: 'AbortError' });
  assert.equal(none.requests.length, 0);
});

await check('redirects, changed response URLs, and HTML/non-JSON MIME cannot become catalog data', async () => {
  const options = [
    { redirected: true }, { url: 'https://evil.example/catalog.json' },
    { url: origin + '/private.json' }, { mime: 'text/html' },
    { mime: 'text/application/json' }, { mime: 'application/json-malformed' }
  ];
  for (const option of options) {
    const h = runtime();
    h.routes.set(ROOT + 'catalog.json', () => response(page(), option));
    await assert.rejects(h.api.openCatalog());
    assert.equal(h.requests.length, 1);
  }
});

await check('abort between initial validation and open continuation cannot return stale initial items', async () => {
  const h = runtime();
  const controller = new AbortController();
  h.routes.set(ROOT + 'catalog.json', () => response(null, { json: async () => {
    queueMicrotask(() => queueMicrotask(() => controller.abort()));
    return page();
  } }));
  await assert.rejects(h.api.openCatalog({ signal: controller.signal }), { name: 'AbortError' });
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].options.signal.aborted, true);
});

await check('invalid selected-record paths/orders and zero-video records do not perform network requests', async () => {
  const invalid = [
    null, record(0, 0), { ...record(0), foundup_id: '__proto__' },
    { ...record(0), video_pages: { catalog: 'https://evil.example/' } },
    { ...record(0), video_pages: { catalog: path('videos', 'lane_9', 0) } },
    { ...record(0), video_count: -1 }, { ...record(0), available_orders: ['popular'] }
  ];
  const h = runtime();
  for (const selected of invalid) await assert.rejects(h.api.openVideos(selected));
  await assert.rejects(h.api.openVideos(record(0), 'popular'));
  assert.equal(h.requests.length, 0);
});

await check('video total must match selected metadata and empty catalogs finish after one request', async () => {
  const h = runtime();
  h.routes.set(path('videos', 'lane_0', 0), page('videos', 0, 7, 'lane_0'));
  await assert.rejects(h.api.openVideos(record(0)));
  const empty = runtime();
  empty.routes.set(ROOT + 'catalog.json', page('catalog', 0, 0));
  const session = await empty.api.openCatalog();
  assert.equal(session.items.length, 0);
  assert.equal(session.hasMore, false);
  assert.equal((await session.loadNext()).length, 0);
  assert.equal(empty.requests.length, 1);
  session.close();
});

await check('actual generated assets work without fetching undisplayed pages or other video records', async () => {
  const h = runtime();
  const publicRoot = resolve(memberRoot, '..');
  h.routes.set(ROOT + 'catalog.json', () => response(JSON.parse(readFileSync(join(publicRoot, ROOT + 'catalog.json'), 'utf8'))));
  const catalog = await h.api.openCatalog();
  assert.equal(h.requests.length, 1);
  const selected = catalog.items.find(item => item.video_count > 6);
  assert.ok(selected);
  const firstPath = selected.video_pages.catalog;
  const first = JSON.parse(readFileSync(join(publicRoot, firstPath), 'utf8'));
  h.routes.set(firstPath, first);
  h.routes.set(first.next, () => response(JSON.parse(readFileSync(join(publicRoot, first.next), 'utf8'))));
  const videos = await h.api.openVideos(selected);
  assert.equal(videos.items.length, 6);
  assert.equal(h.requests.length, 2);
  assert.equal((await videos.loadNext()).length, 6);
  assert.equal(h.requests.length, 3);
  assert.ok(h.requests.slice(1).every(request => request.target.includes('/videos/' + selected.foundup_id + '/catalog/')));
  videos.close();
  catalog.close();
});

console.log('Discovery pager runtime: ' + checks + ' checks passed; controlled responses only.');
