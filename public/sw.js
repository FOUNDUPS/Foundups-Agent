// FoundUPS Root Service Worker - Phase 1
// Safe static-asset caching only. No aggressive offline behavior.
// Does NOT cache auth flows, Clerk SDK, Firebase SDK, or dynamic API calls.

const CACHE_NAME = 'foundups-root-v1';

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/logo-dog.png',
  '/logo-foundups.svg',
  '/favicon-32x32.png',
  '/js/foundup-cube.js'
];

// URLs that must NEVER be cached - auth, legal, dynamic
const NEVER_CACHE = [
  'clerk.accounts.dev',
  'clerk.',
  'firebaseapp.com',
  'googleapis.com/identitytoolkit',
  'googleapis.com/securetoken',
  'cloudfunctions.net',
  '/member/',
  '/sso-callback/',
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
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for HTML/auth, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Never intercept non-GET requests
  if (event.request.method !== 'GET') return;

  // Never cache auth/API/dynamic URLs
  if (shouldNeverCache(url)) return;

  // HTML pages: network-first with cache fallback
  if (event.request.mode === 'navigate' || event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache a fresh copy of the page
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
        // Only cache same-origin successful responses
        if (response.ok && new URL(url).origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
