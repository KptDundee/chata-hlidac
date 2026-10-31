// Jednoduchý service worker: vždy síť, při výpadku poslední uložená verze.
const C = "chata-v1";  // 4.26: síť bez mezipaměti prohlížeče
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const key = e.request.url.split("?")[0];
  // vždy ověřit u serveru (ne starou kopii z mezipaměti prohlížeče)
  const net = e.request.mode === "navigate" ? fetch(e.request.url, {cache:"no-cache", credentials:"same-origin"}) : fetch(e.request, {cache:"no-cache"});
  e.respondWith(net.then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(C).then(c => c.put(key, copy)); }
    return r;
  }).catch(() => caches.match(key)));
});
