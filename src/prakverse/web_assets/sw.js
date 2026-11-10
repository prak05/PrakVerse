const CACHE = "prakverse-shell-v1";
const ASSETS = ["/", "/manifest.webmanifest", "/icon.svg"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener("fetch", event => event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request))));
