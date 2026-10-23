// p.fMALL Member Service Worker
//
// p.fMALL is an AI interaction space for engaging with everything — video,
// documents, community, FoundUps. Video is the default catalog layer; the same
// interaction paradigm (pinch, zoom, navigate) extends to any content type,
// with AI mediating all engagement.
//
// Caches shell assets for installability and fast reload.
// Auth flows (Clerk, Firebase) are NEVER cached.
// Catalog is network-first with cache fallback.

const CACHE_NAME = 'pfmall-member-v4';
const POSTER_CACHE_NAME = 'pfmall-posters-v1';
const PROPERTY_CACHE_NAME = 'pfmall-properties-v1';
const MAX_POSTER_ENTRIES = 60;
const SHELL_DOCUMENT = '/member/';
const PROPERTY_CATALOG_URL = '/move2japan/properties.json';

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
  '/member/js/mall-tile-field.js',
  '/member/js/mall-video-player.js',
  '/member/js/account-concierge.js',
  '/member/js/red-dog-concierge.js',
  '/member/js/mall-state-restore.js',
  '/move2japan/property-search.js',
  '/move2japan/move2japan.css',
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

// Activate: clean old caches (preserve current shell + poster caches)
var KEEP_CACHES = [CACHE_NAME, POSTER_CACHE_NAME, PROPERTY_CACHE_NAME];
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) {
          // Other FoundUps own their caches on this origin. Retire only ours.
          return /^pfmall-(member|posters|properties)-v\d+$/.test(key) && KEEP_CACHES.indexOf(key) === -1;
        })
          .map(function(key) { return caches.delete(key); })
      );
    })
  );
  self.clients.claim();
});

// Trim poster cache to MAX_POSTER_ENTRIES (oldest entries evicted first)
function trimPosterCache() {
  caches.open(POSTER_CACHE_NAME).then(function(cache) {
    cache.keys().then(function(keys) {
      if (keys.length > MAX_POSTER_ENTRIES) {
        var excess = keys.length - MAX_POSTER_ENTRIES;
        for (var i = 0; i < excess; i++) {
          cache.delete(keys[i]);
        }
      }
    });
  });
}

function storeResponse(cacheName, key, response) {
  return caches.open(cacheName).then(function(cache) {
    return cache.put(key, response.clone());
  }).catch(function() { /* Quota/private-mode failure must not hide a network result. */ });
}

function usableResponse(response, kind) {
  if (!response || !response.ok || response.redirected) return false;
  var type = response.headers.get('Content-Type') || '';
  return kind === 'html' ? /^text\/html\b/i.test(type) : /^(application\/json|[^;]+\+json)\b/i.test(type);
}

function networkFirst(request, cacheName, key, kind, fallback) {
  // These are fixed public source paths, never an authenticated API response.
  return fetch(request, { cache: 'no-cache', credentials: 'omit' }).then(function(response) {
    if (!usableResponse(response, kind)) throw new Error('Public source response unavailable');
    return storeResponse(cacheName, key, response).then(function() { return response; });
  }).catch(function() {
    return caches.open(cacheName).then(function(cache) { return cache.match(key); })
      .catch(function() { return null; })
      .then(function(cached) { return cached || fallback(); });
  });
}

function emptyVideoCatalog() {
  return new Response('[]', {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'X-Offline-Fallback': '1' }
  });
}

// Fetch strategy: exact same-origin public paths only. Member APIs, arbitrary
// routes, query-bearing assets and third-party URLs remain network-only.
self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') return;
  var url = new URL(event.request.url);
  if (url.origin !== self.location.origin || shouldNeverCache(url.origin + url.pathname)) return;

  // The product query selects a view inside the existing shell. Cache one
  // static document, never account/filter query strings or return URLs.
  if (event.request.mode === 'navigate' &&
      (url.pathname === '/member/' || url.pathname === '/member/index.html')) {
    event.respondWith(networkFirst(SHELL_DOCUMENT, CACHE_NAME, SHELL_DOCUMENT, 'html', function() {
      return new Response('The Foundups Mall is unavailable offline. Reconnect and retry.', {
        status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }));
    return;
  }

  if (url.search) return;

  if (url.pathname === PROPERTY_CATALOG_URL) {
    event.respondWith(networkFirst(event.request, PROPERTY_CACHE_NAME, PROPERTY_CATALOG_URL, 'json', function() {
      // No fabricated empty catalog or fresh timestamp. Cached source bytes,
      // including observed_on, are returned unchanged when available.
      return new Response('{"error":"public_property_catalog_unavailable"}', {
        status: 503, headers: { 'Content-Type': 'application/json', 'X-Offline-Fallback': '1' }
      });
    }));
    return;
  }

  // Catalog: network-first, cache fallback, empty-array last resort
  if (url.pathname === CATALOG_URL) {
    event.respondWith(networkFirst(event.request, CACHE_NAME, CATALOG_URL, 'json', emptyVideoCatalog));
    return;
  }

  // Poster images under /media/posters/: cache-first, bounded poster cache
  if (/^\/media\/posters\/[^/]+\.(jpg|jpeg|png|webp|avif)$/i.test(url.pathname)) {
    event.respondWith(
      caches.open(POSTER_CACHE_NAME).then(function(posterCache) {
        return posterCache.match(event.request).then(function(cached) {
          if (cached) return cached;
          return fetch(event.request, { credentials: 'omit' }).then(function(response) {
            if (response.ok && !response.redirected) {
              posterCache.put(event.request, response.clone());
              trimPosterCache();
            }
            return response;
          });
        });
      })
    );
    return;
  }

  // Only declared static shell assets are eligible, not everything /member/*.
  if (SHELL_ASSETS.indexOf(url.pathname) !== -1) {
    event.respondWith(
      caches.open(CACHE_NAME).then(function(cache) { return cache.match(url.pathname); }).then(function(cached) {
        if (cached) return cached;
        return fetch(event.request, { credentials: 'omit' }).then(function(response) {
          if (response.ok && !response.redirected) {
            return storeResponse(CACHE_NAME, url.pathname, response).then(function() { return response; });
          }
          return response;
        });
      })
    );
    return;
  }

  // Everything else: network only (fonts, external CDN, etc.)
});
