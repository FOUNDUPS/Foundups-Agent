// p.fMALL Member Service Worker
// Caches shell assets for installability and fast reload.
// Auth flows (Clerk, Firebase) are NEVER cached.
// Catalog is network-first with cache fallback.

const CACHE_NAME = 'pfmall-member-v1';

// Shell assets pre-cached on install
const SHELL_ASSETS = [
  '/member/',
  '/member/manifest.json',
  '/member/css/member.css',
  '/member/css/account-concierge.css',
  '/member/css/mall-planes.css',
  '/member/css/mall-tile-field.css',
  '/member/css/mall-video-player.css',
  '/member/js/gesture-engine.js',
  '/member/js/shell-bridge-interceptor.js',
  '/member/js/mall-planes.js',
  '/member/js/mall-video-player.js',
  '/member/js/account-concierge.js',
  '/member/js/red-dog-concierge.js',
  '/member/js/mall-state-restore.js',
  '/logo-dog.png',
  '/favicon-32x32.png',
];

// Catalog: network-first with cache fallback
const CATALOG_URL = '/member/mall-video-catalog.json';

// URLs that must NEVER be cached — auth, SDK, dynamic API
const NEVER_CACHE = [
  'clerk.accounts.dev',
  'clerk.',
  'firebaseapp.com',
  'googleapis.com/identitytoolkit',
  'googleapis.com/securetoken',
  'cloudfunctions.net',
  'gstatic.com/firebasejs',
  '/sso-callback/',
];

function shouldNeverCache(url) {
  return NEVER_CACHE.some(function(pattern) { return url.indexOf(pattern) !== -1; });
}

// Install: pre-cache shell assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(SHELL_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) { return key !== CACHE_NAME; })
          .map(function(key) { return caches.delete(key); })
      );
    })
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener('fetch', function(event) {
  var url = event.request.url;

  // Never intercept non-GET
  if (event.request.method !== 'GET') return;

  // Never cache auth/SDK/dynamic
  if (shouldNeverCache(url)) return;

  // Catalog: network-first, cache fallback
  if (url.indexOf(CATALOG_URL) !== -1) {
    event.respondWith(
      fetch(event.request).then(function(response) {
        if (response.ok) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
        }
        return response;
      }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Poster images under /media/posters/: cache-first (large, stable)
  if (url.indexOf('/media/posters/') !== -1) {
    event.respondWith(
      caches.match(event.request).then(function(cached) {
        if (cached) return cached;
        return fetch(event.request).then(function(response) {
          if (response.ok && new URL(url).origin === self.location.origin) {
            var clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
          }
          return response;
        });
      })
    );
    return;
  }

  // Member shell assets: cache-first with network fallback
  if (url.indexOf('/member/') !== -1 && new URL(url).origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then(function(cached) {
        if (cached) return cached;
        return fetch(event.request).then(function(response) {
          if (response.ok) {
            var clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, clone); });
          }
          return response;
        });
      })
    );
    return;
  }

  // Everything else: network only (fonts, external CDN, etc.)
});
