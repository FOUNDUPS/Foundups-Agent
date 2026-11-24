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
  svg: 'image/svg+xml', png: 'image/png', webp: 'image/webp', jpg: 'image/jpeg',
};

function worker() {
  const handlers = {};
  const contents = new Map();
  const requests = [];
  const names = ['unrelated', ...Array.from({length: 11}, (_, i) => `vote-public-guide-v${i + 2}`)];
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
  assert.equal(sw.contents.size, 36);
  assert.ok(sw.requests.every(({options}) => options.redirect === 'error'));
  await sw.event('activate', '/');
  assert.deepEqual(sw.deleted, Array.from({length: 11}, (_, i) => `vote-public-guide-v${i + 2}`));
  for (const asset of ['contact-script.js', 'contact-script.mjs']) assert.ok(sw.contents.has(origin + '/' + asset));
  sw.changeResponse(() => { throw new TypeError('offline'); });
  for (const path of ['/guide', '/contact', '/evidence', '/coalition']) {
    assert.equal(await sw.event('fetch', path), sw.contents.get(origin + path));
    assert.equal(await sw.event('fetch', path + '.html'), sw.contents.get(origin + path));
  }
  assert.equal(await sw.event('fetch', '/index.html'), sw.contents.get(origin + '/'));
  for (const path of ['/cover.css', '/cover.js', ...[1, 2, 3, 4, 5].map((n) => `/comics/photo-${n}.webp`), ...['schumer', 'jeffries'].flatMap((name) => [`/comics/${name}-card-loop.webp`, `/comics/${name}-card-still.webp`])]) {
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

test('cover portraits use stills while hidden or paused and require explicit play after a pause', () => {
  const markup = readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
  const nativeSources = [...markup.matchAll(/<source\s+media="([^"]+)"\s+srcset="comics\/(schumer|jeffries)-card-loop\.webp"/g)];
  assert.equal(nativeSources.length, 2);
  for (const [, media, name] of nativeSources) {
    assert.equal(media, '(prefers-reduced-motion: no-preference)');
    assert.ok(markup.includes(`src="comics/${name}-card-still.webp"`));
  }

  const sources = nativeSources.map(([, media]) => ({media}));
  const clicks = {};
  const toggle = {
    hidden: true,
    textContent: 'Pause portraits',
    addEventListener: (name, callback) => { clicks[name] = callback; },
  };
  const portraits = {
    querySelectorAll: (selector) => {
      assert.equal(selector, 'picture source');
      return sources;
    },
    querySelector: (selector) => {
      assert.equal(selector, '.cover-portraits-toggle');
      return toggle;
    },
  };
  const listeners = {};
  const document = {
    hidden: true,
    querySelector: (selector) => selector === '.cover-portraits' ? portraits : null,
    addEventListener: (name, callback) => { listeners[name] = callback; },
  };
  vm.runInNewContext(coverCode, {
    URL, location: new URL(origin + '/'), navigator: {}, document,
    window: {addEventListener: () => {}},
  });
  const expectMedia = (media) => assert.deepEqual(sources.map((source) => source.media), [media, media]);

  assert.equal(toggle.hidden, false);
  expectMedia('not all');
  document.hidden = false;
  listeners.visibilitychange();
  expectMedia('(prefers-reduced-motion: no-preference)');

  clicks.click();
  assert.equal(toggle.textContent, 'Play portraits');
  expectMedia('not all');
  for (const hidden of [true, false]) {
    document.hidden = hidden;
    listeners.visibilitychange();
    expectMedia('not all');
    assert.equal(toggle.textContent, 'Play portraits');
  }

  clicks.click();
  assert.equal(toggle.textContent, 'Pause portraits');
  expectMedia('(prefers-reduced-motion: no-preference)');
  document.hidden = true;
  listeners.visibilitychange();
  expectMedia('not all');
  document.hidden = false;
  listeners.visibilitychange();
  expectMedia('(prefers-reduced-motion: no-preference)');
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

test('both whole HPC banners and separate Mall links remain native anchors without script', () => {
  for (const name of ['index.html', 'contact.html']) {
    const markup = readFileSync(new URL('../web/' + name, import.meta.url), 'utf8');
    const navigation = markup.match(/<nav class="hpc-navigation"[\s\S]*?<\/nav>/)?.[0];
    assert.ok(navigation, name);
    const links = [...navigation.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)];
    assert.equal(links.length, 2, name);
    assert.match(links[0][1], /href="https:\/\/hpc\.foundups\.com"/);
    assert.match(links[0][1], /aria-label="HPC — return to HPC"/);
    assert.match(links[0][2], /icons\/hpc-portrait\.png/);
    assert.match(links[0][2], /Return to HPC/);
    assert.doesNotMatch(links[0][2], /<(?:a|button)\b/);
    assert.match(links[1][1], /href="https:\/\/play\.foundups\.com"/);
    assert.match(links[1][2], /icons\/red-dog\.png/);
    assert.match(markup, /href="hpc-navigation\.css"/);
    assert.match(markup, /src="hpc-navigation\.js" defer/);
  }
});

test('portrait motion starts only while visible and stops on hidden-page changes', () => {
  const listeners = {};
  const classes = new Set();
  const doc = {
    hidden: true,
    documentElement: {classList: {toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name)}},
    addEventListener: (name, callback) => { listeners[name] = callback; },
  };
  vm.runInNewContext(readFileSync(new URL('../web/hpc-navigation.js', import.meta.url), 'utf8'), {document: doc});
  assert.ok(!classes.has('hpc-navigation-motion'));
  doc.hidden = false; listeners.visibilitychange();
  assert.ok(classes.has('hpc-navigation-motion'));
  doc.hidden = true; listeners.visibilitychange();
  assert.ok(!classes.has('hpc-navigation-motion'));
});

test('new navigation assets are available offline but external destinations never enter the cache', async () => {
  const sw = worker();
  await sw.event('install', '/');
  sw.changeResponse(() => { throw new TypeError('offline'); });
  for (const path of ['/hpc-navigation.css', '/hpc-navigation.js', '/icons/hpc-portrait.png', '/icons/red-dog.png']) {
    assert.ok(sw.contents.has(origin + path), path);
    assert.equal(await sw.event('fetch', path), sw.contents.get(origin + path));
  }
  for (const url of ['https://hpc.foundups.com', 'https://play.foundups.com']) assert.equal(sw.event('fetch', url), undefined);
});
