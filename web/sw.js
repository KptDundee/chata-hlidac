// Jednoduchý service worker: vždy síť, při výpadku poslední uložená verze.
const C = "chata-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const key = e.request.url.split("?")[0];
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(C).then(c => c.put(key, copy)); }
    return r;
  }).catch(() => caches.match(key)));
});
