/* Standalone Story Time only. Generated placeholders bind this worker to a build. */
const REVISION = '__STORYTIME_REVISION__';
const ALLOWED_ORIGINS = __STORYTIME_PWA_ORIGINS__;
const SHELL_ASSETS = __STORYTIME_SHELL_ASSETS__;
const CACHE_PREFIX = 'eduit-storytime-';
const CACHE_NAME = CACHE_PREFIX + REVISION;
const ACTIVE_ORIGIN = ALLOWED_ORIGINS.includes(self.location.origin);

self.addEventListener('install', event => {
  if (!ACTIVE_ORIGIN) return;
  // A failed/partial install never replaces the previous coherent revision.
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_ASSETS))
    .catch(error => caches.delete(CACHE_NAME).then(() => { throw error; })));
  // Updates wait for the explicit Update & restart button; no mid-play reload.
});

self.addEventListener('activate', event => {
  if (!ACTIVE_ORIGIN) return;
  event.waitUntil((async () => {
    const owned = (await caches.keys()).filter(key => key.startsWith(CACHE_PREFIX));
    // Keep current plus the most recently installed previous shell for old tabs.
    const previous = owned.filter(key => key !== CACHE_NAME).slice(-1);
    await Promise.all(owned.filter(key => key !== CACHE_NAME && !previous.includes(key))
      .map(key => caches.delete(key)));
  })());
  // Do not claim existing tabs; they remain bound to their previous worker.
});

self.addEventListener('message', event => {
  if (ACTIVE_ORIGIN && event.data && event.data.type === 'STORYTIME_ACTIVATE' &&
      event.source && new URL(event.source.url).origin === self.location.origin &&
      event.source.url.startsWith(self.location.origin + '/storytime/')) {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', event => {
  if (!ACTIVE_ORIGIN || event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.search ||
      event.request.headers.has('range')) return;
  // Media including range requests is always network-only, at immutable URLs.
  // No APIs, auth, arbitrary routes, cross-origin assets or child records cached.
  if (event.request.mode === 'navigate' && url.pathname === '/') {
    event.respondWith(Promise.resolve(Response.redirect(new URL('/storytime/', self.location.origin).href, 302)));
    return;
  }
  let key = url.pathname;
  if (event.request.mode === 'navigate' &&
      (key === '/storytime/' || key === '/storytime/index.html')) key = '/storytime/';
  if (!SHELL_ASSETS.includes(key)) return;
  event.respondWith(caches.open(CACHE_NAME).then(cache => cache.match(key))
    .then(cached => cached || fetch(event.request, {credentials: 'omit'})));
});
