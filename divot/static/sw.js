// Divot Service Worker — offline tile caching
const CACHE_NAME = 'divot-v1';
const TILE_CACHE = 'divot-tiles-v1';

// App shell files to cache
const APP_FILES = [
  './',
  './index.html'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME && k !== TILE_CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Cache map tiles
  if (url.hostname.includes('tile.openstreetmap.org') ||
      url.hostname.includes('basemaps.cartocdn.com')) {
    event.respondWith(
      caches.open(TILE_CACHE).then(cache =>
        cache.match(event.request).then(cached => {
          if (cached) return cached;
          return fetch(event.request).then(response => {
            if (response.ok) cache.put(event.request, response.clone());
            return response;
          }).catch(() => new Response('', { status: 408 }));
        })
      )
    );
    return;
  }

  // Cache Socrata API responses (short TTL)
  if (url.hostname.includes('data.lacity.org') ||
      url.hostname.includes('data.cityofchicago.org') ||
      url.hostname.includes('data.cityofnewyork.us')) {
    event.respondWith(
      fetch(event.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => caches.match(event.request))
    );
    return;
  }

  // App shell — cache first
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
