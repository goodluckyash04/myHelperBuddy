/**
 * service-worker.js — myHelperBuddy PWA Service Worker
 *
 * Served from root path (/service-worker.js) so scope covers the entire origin.
 * Cache version bumped — old SW with wrong /static/ scope will be replaced.
 */

const CACHE_NAME = "mhb-pwa-v3";

// Static assets to pre-cache on install
const STATIC_URLS = [
  "/",
  "/static/css/style.css",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png",
];

// ── Install: pre-cache known-good static assets ──────────────────────────────
self.addEventListener("install", (event) => {
  self.skipWaiting(); // Activate immediately — don't wait for old SW to die
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // allSettled so one missing file doesn't kill the whole install
      Promise.allSettled(STATIC_URLS.map((url) => cache.add(url)))
    )
  );
});

// ── Activate: remove stale caches ────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim()) // Take control of all existing pages
  );
});

// ── Fetch: cache-first for static, network-first for pages ───────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin requests
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Skip Django auth / admin / API endpoints — always go to network
  if (
    url.pathname.startsWith("/admin/") ||
    url.pathname.startsWith("/login") ||
    url.pathname.startsWith("/logout") ||
    url.pathname.startsWith("/signup") ||
    url.pathname.startsWith("/accounts/") ||
    url.pathname.startsWith("/api/")
  ) return;

  // Cache-first for static files (CSS, JS, images)
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  // Network-first for app pages — content stays fresh, falls back to cache offline
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
