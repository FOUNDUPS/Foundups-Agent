'use strict';

const scope = new URL(self.registration.scope);
const scopeSuffix = ':' + scope.pathname;
const CACHE = 'oversight-public-shell-v0.6.0' + scopeSuffix;
const indexAlias = new URL('index.html', scope).href;
const shell = new Set([
  './', 'style.css', 'app.js', 'documents.js', 'explore.js', 'overview.css',
  'overview.js', 'manifest.webmanifest', 'icons/icon-192.png',
  'icons/icon-512.png', 'icons/icon.svg',
].map((path) => new URL(path, scope).href));

self.addEventListener('install', (event) => {
  const requests = Array.from(shell, (url) => new Request(url, {redirect: 'error', cache: 'reload'}));
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(requests)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith('oversight-public-shell-')
      && key.endsWith(scopeSuffix) && key !== CACHE).map((key) => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const {url, method} = event.request;
  // Navigation requests can carry a fragment used by the preserved router.
  const resource = new URL(url);
  resource.hash = '';
  const cacheKey = resource.href === indexAlias ? scope.href : resource.href;
  if (method !== 'GET' || !shell.has(cacheKey)) return;
  event.respondWith(fetch(event.request).catch(async () => {
    const cache = await caches.open(CACHE);
    return await cache.match(cacheKey) || new Response(
      'The public playbook is offline. Reconnect to open the latest document.',
      {status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8'}}
    );
  }));
});
