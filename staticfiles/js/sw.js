/**
 * WargaIn Service Worker
 * Developed by Zyntaxera
 * PWA Service Worker supporting Android & iOS Safari standalone mode
 */

const CACHE_NAME = 'wargain-pwa-v1';
const OFFLINE_URL = '/offline/';

const PRECACHE_ASSETS = [
  OFFLINE_URL,
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-maskable-512.png',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/icon.svg',
  '/static/icons/favicon.png'
];

// Install Event: Pre-cache essential offline shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Clean up outdated caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Intelligent routing
self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only handle GET requests
  if (req.method !== 'GET') {
    return;
  }

  // Handle HTML navigation (Pages) -> Network first, fallback to offline page
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => {
        return caches.match(OFFLINE_URL).then((response) => {
          return response || new Response('Anda sedang offline. Silakan periksa koneksi internet Anda.', {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
          });
        });
      })
    );
    return;
  }

  // Handle Static Assets (Images, Icons, CSS, JS) -> Cache First with Network Fallback
  const url = new URL(req.url);
  if (url.pathname.startsWith('/static/') || url.hostname.includes('fonts.googleapis.com') || url.hostname.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.match(req).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(req).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(req, responseToCache);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // Default: Network fetch
  event.respondWith(fetch(req));
});
