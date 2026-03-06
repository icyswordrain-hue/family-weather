// Service Worker — Canopy / 厝邊天氣
const CACHE_NAME = 'weather-v8';
const SHELL_ASSETS = [
    '/',
    '/static/style.css',
    '/static/app.js',
    '/static/manifest.json',
    '/static/icon-192.svg',
    '/static/icon-512.svg',
];

// Install: cache app shell
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
    );
    self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Normalise a URL to strip query strings — so versioned ?v=N URLs hit the same cache entry
function normalisedRequest(request) {
    const url = new URL(request.url);
    if (!url.search) return request;
    return new Request(url.origin + url.pathname, { mode: 'no-cors' });
}

// Fetch: network-first for API, cache-first for everything else
self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);

    // API calls — always network-first (no cache on success)
    if (url.pathname.startsWith('/api/')) {
        e.respondWith(
            fetch(e.request).catch(() => caches.match(normalisedRequest(e.request)))
        );
        return;
    }

    // Audio files — cache-first, cache on first load for offline playback
    if (url.pathname.startsWith('/local_assets/')) {
        e.respondWith(
            caches.match(e.request).then((cached) => {
                if (cached) return cached;
                return fetch(e.request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
                    return response;
                });
            })
        );
        return;
    }

    // Static assets — stale-while-revalidate with query-string-stripped cache key
    const cacheReq = normalisedRequest(e.request);
    e.respondWith(
        caches.match(cacheReq).then((cached) => {
            const fetching = fetch(e.request).then((response) => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(cacheReq, clone));
                return response;
            });
            return cached || fetching;
        })
    );
});
