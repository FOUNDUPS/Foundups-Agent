// Kosei AI Systems - Service Worker
// Static asset caching only. No aggressive offline behavior.
// Does NOT cache Firebase SDK, auth flows, or Firestore writes.

const CACHE_NAME = 'kosei-v1';

const STATIC_ASSETS = [
  '/kosei/',
  '/kosei/manifest.json',
  '/kosei/css/kosei.css',
  '/kosei/js/kosei-i18n.js',
  '/kosei/js/kosei-intake.js'
];

// URLs that must NEVER be cached - auth, Firebase, dynamic
const NEVER_CACHE = [
  'firebaseapp.com',
  'googleapis.com/identitytoolkit',
  'googleapis.com/securetoken',
  'cloudfunctions.net',
  'firestore.googleapis.com',
  'gstatic.com/firebasejs'
];

function shouldNeverCache(url) {
  return NEVER_CACHE.some(pattern => url.includes(pattern));
}

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key.startsWith('kosei-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for HTML, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Never intercept non-GET requests (form submissions)
  if (event.request.method !== 'GET') return;

  // Never cache Firebase/auth URLs
  if (shouldNeverCache(url)) return;

  // HTML pages: network-first with cache fallback
  if (event.request.mode === 'navigate' || event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static assets: cache-first with network fallback
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response.ok && new URL(url).origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
