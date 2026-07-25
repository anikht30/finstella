// This script runs in the background to handle caching and offline modes.
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Installed');
});

self.addEventListener('fetch', (e) => {
    // A fetch listener is strictly required for the PWA install prompt to trigger
    e.respondWith(fetch(e.request));
});