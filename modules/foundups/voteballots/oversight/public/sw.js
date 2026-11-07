'use strict';

const scope = new URL(self.registration.scope);
const scopeSuffix = ':' + scope.pathname;
const CACHE = 'oversight-public-shell-v0.7.0' + scopeSuffix;
const resolve = (path) => new URL(path, scope).href;
const aliases = new Map([
  [resolve('index.html'), scope.href],
  [resolve('state-ag-transitions.html'), resolve('state-ag-transitions')],
]);
const shell = new Set([
  './', 'state-ag-transitions', 'overview.css', 'overview.js', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon.svg',
].map(resolve));

self.addEventListener('install', (event) => {
  const requests = Array.from(shell, (url) => new Request(url, {redirect: 'error', cache: 'reload'}));
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(requests)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => (
    key === 'oversight-public-shell-v0.5.0' ||
    (key.startsWith('oversight-public-shell-') && key.endsWith(scopeSuffix) && key !== CACHE)
  )).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const resource = new URL(event.request.url);
  resource.hash = '';
  const cacheKey = aliases.get(resource.href) || resource.href;
  if (event.request.method !== 'GET' || !shell.has(cacheKey)) return;
  event.respondWith(fetch(event.request).catch(async () => {
    const cache = await caches.open(CACHE);
    return await cache.match(cacheKey) || new Response('Reconnect to open this resource.', {
      status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8'},
    });
  }));
});
