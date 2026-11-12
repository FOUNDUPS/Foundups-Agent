import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const code = readFileSync(new URL('../web/sw.js', import.meta.url), 'utf8');
const coverCode = readFileSync(new URL('../web/cover.js', import.meta.url), 'utf8');
const guideMarkup = readFileSync(new URL('../web/guide.html', import.meta.url), 'utf8');
const origin = 'https://vote.test';
const MIME = {
  css: 'text/css', js: 'text/javascript', mjs: 'text/javascript',
  json: 'application/json', webmanifest: 'application/manifest+json',
  svg: 'image/svg+xml', png: 'image/png', webp: 'image/webp',
};

function worker() {
  const handlers = {};
  const contents = new Map();
  const requests = [];
  const names = ['unrelated', 'vote-public-guide-v2', 'vote-public-guide-v3', 'vote-public-guide-v4', 'vote-public-guide-v5', 'vote-public-guide-v6', 'vote-public-guide-v7'];
  const deleted = [];
  const cache = {
    match: async (url) => contents.get(url),
    put: async (url, response) => contents.set(url, response),
  };
  let responseFor = (url) => {
    const media = MIME[new URL(url).pathname.split('.').pop()] || 'text/html';
    const response = {
      url, ok: true, redirected: false, headers: new Headers({'content-type': media}),
      clone: () => response,
    };
    return response;
  };
  vm.runInNewContext(code, {
    URL, Response,
    self: {
      registration: { scope: origin + '/' }, location: { origin },
      clients: { claim: async () => {} },
      addEventListener: (name, callback) => { handlers[name] = callback; },
    },
    caches: {
      open: async () => cache, keys: async () => names,
      delete: async (name) => deleted.push(name),
    },
    fetch: async (request, options) => {
      const url = typeof request === 'string' ? request : request.url;
      requests.push({url, options});
      return responseFor(url);
    },
  });
  function event(name, path, method = 'GET') {
    let result;
    const capture = (value) => { result = value; };
    handlers[name]({request: {url: new URL(path, origin).href, method}, waitUntil: capture, respondWith: capture});
    return result;
  }
  return {event, contents, requests, deleted, changeResponse: (handler) => { responseFor = handler; }};
}

test('canonical and prior HTML navigation use the same cached document offline', async () => {
  const sw = worker();
  await sw.event('install', '/');
  assert.equal(sw.contents.size, 25);
  assert.ok(sw.requests.every(({options}) => options.redirect === 'error'));
  await sw.event('activate', '/');
  assert.deepEqual(sw.deleted, ['vote-public-guide-v2', 'vote-public-guide-v3', 'vote-public-guide-v4', 'vote-public-guide-v5', 'vote-public-guide-v6']);
  sw.changeResponse(() => { throw new TypeError('offline'); });
  for (const path of ['/guide', '/contact', '/evidence', '/coalition']) {
    assert.equal(await sw.event('fetch', path), sw.contents.get(origin + path));
    assert.equal(await sw.event('fetch', path + '.html'), sw.contents.get(origin + path));
  }
  assert.equal(await sw.event('fetch', '/index.html'), sw.contents.get(origin + '/'));
  for (const path of ['/cover.css', '/cover.js', ...[1, 2, 3, 4, 5].map((n) => `/comics/photo-${n}.webp`)]) {
    assert.ok(sw.contents.has(origin + path));
    assert.equal(await sw.event('fetch', path), sw.contents.get(origin + path));
  }
  assert.equal(await sw.event('fetch', '/contact.html#main'), sw.contents.get(origin + '/contact'));
  for (const path of ['/contact?track=1', '/api', 'https://another.test/contact']) {
    assert.equal(sw.event('fetch', path), undefined);
  }
  assert.equal(sw.event('fetch', '/contact', 'POST'), undefined);
  assert.equal(sw.event('fetch', 'https://a12.asurahosting.com/listen/antifafm/radio.mp3'), undefined);
});

test('the cover hands every original guide fragment back to the guide', () => {
  const location = new URL(origin + '/?from=bookmark#comic-cover');
  const redirects = [];
  location.replace = (destination) => redirects.push(destination.href);
  let hashChanged;
  vm.runInNewContext(coverCode, {
    URL,
    location,
    navigator: {},
    document: { querySelector: () => null },
    window: {
      addEventListener: (name, callback) => { if (name === 'hashchange') hashChanged = callback; },
    },
  });
  assert.deepEqual(redirects, []);
  for (const [, id] of guideMarkup.matchAll(/\bid="([^"]+)"/g)) {
    location.hash = id;
    hashChanged();
    assert.equal(redirects.pop(), origin + '/guide?from=bookmark#' + id);
  }
  location.hash = '%6fversight';
  hashChanged();
  assert.equal(redirects.pop(), origin + '/guide?from=bookmark#%6fversight');
  for (const id of ['%E0%A4', 'comic-cover', '//outside.test/path']) {
    location.hash = id;
    hashChanged();
  }
  assert.deepEqual(redirects, []);
});

test('Oversight serves the scoped maps, roadmap and manual contact offline', async () => {
  const file = new URL('../oversight/public/sw.js', import.meta.url);
  const scope = origin + '/web/';
  let fetchHandler;
  const cached = new Response('Preserved professional shell');
  const offline = new Map(['', 'legislative-roadmap', 'contact', 'contact-roster.json', 'states-location.mjs', 'explore', 'map-data.json']
    .map((path) => [scope + path, cached]));
  vm.runInNewContext(readFileSync(file, 'utf8'), {
    URL, Response,
    self: {
      registration: {scope},
      addEventListener: (name, callback) => { if (name === 'fetch') fetchHandler = callback; },
    },
    caches: {
      open: async (name) => {
        assert.equal(name, 'oversight-public-shell-v0.10.0:/web/');
        return {match: async (key) => offline.get(key)};
      },
    },
    fetch: async () => { throw new TypeError('offline'); },
  });
  function navigate(path) {
    let result;
    fetchHandler({request: {url: origin + path, method: 'GET'}, respondWith: (value) => { result = value; }});
    return result;
  }
  assert.equal(await navigate('/web/#senate'), cached);
  assert.equal(await navigate('/web/index.html#house'), cached);
  for (const path of ['legislative-roadmap', 'legislative-roadmap.html#decide-referral',
    'contact', 'contact.html', 'contact-roster.json', 'states-location.mjs', 'explore#authority',
    'explore.html#edge-house--review', 'map-data.json']) {
    assert.equal(await navigate('/web/' + path), cached);
  }
  assert.equal(navigate('/contact'), undefined);
  assert.equal(navigate('/web/states-boundaries.json'), undefined);
  assert.equal(navigate('/web/?q=1#states'), undefined);
  assert.equal(navigate('/abc/style.css#x'), undefined);
  assert.equal(navigate('/web/app.js'), undefined);
  assert.equal(navigate('/web/openclaw.json'), undefined);
});

test('failed precache rejects redirects and misleading MIME without writing', async () => {
  for (const type of ['redirect', 'mime']) {
    const sw = worker();
    sw.changeResponse((url) => {
      const isContact = url.endsWith('/contact');
      const media = MIME[new URL(url).pathname.split('.').pop()] || 'text/html';
      return {
        url: isContact && type === 'redirect' ? origin + '/coalition' : url,
        ok: true, redirected: isContact && type === 'redirect',
        headers: new Headers({'content-type': isContact && type === 'mime' ? 'application/json' : media}),
      };
    });
    await assert.rejects(sw.event('install', '/'), /Invalid Vote shell response/);
    assert.equal(sw.contents.size, 0);
  }
});
