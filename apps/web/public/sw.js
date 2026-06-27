// PAIOS Service Worker — Phase 9.5
// Strategy:
//   - Static assets (_next/static/): cache-first, permanent
//   - App pages (HTML): network-first with cache fallback
//   - API calls (/api/, backend routes): network-only (never stale)

const CACHE_VERSION = "paios-v1";
const SHELL_PAGES = ["/dashboard", "/chat", "/missions", "/memory"];

// Install: pre-cache app shell pages
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(SHELL_PAGES))
      .then(() => self.skipWaiting()),
  );
});

// Activate: delete old cache versions
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE_VERSION)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never cache API calls — always fresh data
  if (
    url.pathname.startsWith("/api/") ||
    url.hostname !== self.location.hostname
  ) {
    return;
  }

  // Static Next.js assets: cache-first (immutable hashed filenames)
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
            }
            return response;
          }),
      ),
    );
    return;
  }

  // HTML pages: network-first, fallback to cache, fallback to /dashboard
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
          return response;
        })
        .catch(
          () =>
            caches.match(request) ||
            caches.match("/dashboard") ||
            new Response("Offline — abra o PAIOS quando estiver online.", {
              status: 503,
              headers: { "Content-Type": "text/plain; charset=utf-8" },
            }),
        ),
    );
    return;
  }
});
