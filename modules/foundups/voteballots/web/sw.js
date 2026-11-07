'use strict';

// Only this public guide's exact same-origin shell paths are eligible for caching.
const CACHE = 'vote-public-guide-v2';
const SHELL = ['./', './index.html', './coalition.html', './style.css', './app.js', './coalition.js', './coalition-draft.mjs', './manifest.webmanifest', './icons/icon.svg', './icons/icon-192.png', './icons/icon-512.png'];
const SHELL_URLS = new Set(SHELL.map((path) => new URL(path, self.registration.scope).href));

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('vote-public-guide-') && key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.search || !SHELL_URLS.has(url.href)) return;
  event.respondWith(fetch(event.request).then(async (response) => {
    const finalURL = response.url ? new URL(response.url) : null;
    if (response.ok && !response.redirected && finalURL && finalURL.origin === self.location.origin && !finalURL.search && SHELL_URLS.has(finalURL.href)) {
      try {
        const cache = await caches.open(CACHE);
        await cache.put(event.request, response.clone());
      } catch {
        // A cache denial must not replace a successful network response.
      }
    }
    return response;
  }).catch(async () => {
    const cached = await caches.match(event.request);
    return cached || new Response('This public guide is offline. Reconnect to load the latest version.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }));
});
