'use strict';

// Only this public guide's exact same-origin shell paths are eligible for caching.
const CACHE = 'vote-public-guide-v5';
const PAGES = ['guide', 'coalition', 'evidence', 'contact'];
const SHELL = [
  './', ...PAGES.map((page) => './' + page),
  './cover.css', './cover.js',
  ...[1, 2, 3, 4, 5].map((photo) => `./comics/photo-${photo}.webp`),
  './style.css', './app.js', './manifest.webmanifest',
  './coalition.js', './coalition-draft.mjs', './evidence.css',
  './contact.js', './contact.css', './contact-queue.mjs', './contact-roster.json',
  './icons/icon.svg', './icons/icon-192.png', './icons/icon-512.png',
];
const scopeURL = (path) => new URL(path, self.registration.scope).href;
const SHELL_URLS = new Set(SHELL.map(scopeURL));
const PAGE_ALIASES = new Map([
  [scopeURL('./index.html'), scopeURL('./')],
  ...PAGES.map((page) => [scopeURL('./' + page + '.html'), scopeURL('./' + page)]),
]);

const CONTENT_TYPES = new Map([
  ['css', 'text/css'],
  ['js', 'text/javascript'],
  ['mjs', 'text/javascript'],
  ['json', 'application/json'],
  ['webmanifest', 'application/manifest+json'],
  ['svg', 'image/svg+xml'],
  ['png', 'image/png'],
  ['webp', 'image/webp'],
]);

function isShellResponse(response, url) {
  const extension = new URL(url).pathname.split('.').pop();
  const contentType = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
  const expected = CONTENT_TYPES.get(extension) || 'text/html';
  return response.ok && !response.redirected && response.url === url && contentType === expected;
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const responses = await Promise.all(Array.from(SHELL_URLS, async (url) => {
      const response = await fetch(url, {redirect: 'error', cache: 'reload'});
      if (!isShellResponse(response, url)) throw new Error('Invalid Vote shell response');
      return [url, response];
    }));
    const cache = await caches.open(CACHE);
    await Promise.all(responses.map(([url, response]) => cache.put(url, response)));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('vote-public-guide-') && key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  url.hash = '';
  const cacheKey = PAGE_ALIASES.get(url.href) || url.href;
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.search || !SHELL_URLS.has(cacheKey)) return;
  event.respondWith(fetch(event.request).then(async (response) => {
    if (isShellResponse(response, cacheKey)) {
      try {
        const cache = await caches.open(CACHE);
        await cache.put(cacheKey, response.clone());
      } catch {
        // A cache denial must not replace a successful network response.
      }
    }
    return response;
  }).catch(async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(cacheKey);
    return cached || new Response('This public guide is offline. Reconnect to load the latest version.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }));
});
